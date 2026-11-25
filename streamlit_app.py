"""Application Python Streamlit - SAE Sodebo (demo publique avec donnees fictives)."""
from __future__ import annotations
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app.analysis import (
    AnalysisError, ingest, valid_variables, transformed, validate_groups,
    validate_targets, analyze, aggregate_csv,
)
from app.secure_sessions import encrypt_project, decrypt_project

BASE = Path(__file__).resolve().parent
UPLOADS_ENABLED = os.getenv("SAE_ALLOW_UPLOAD", "0") == "1"

st.set_page_config(page_title="SAE - Analyse des enquetes", page_icon="📊", layout="wide")
st.title("📊 SAÉ 5.01 / 6.01 — Analyse des enquêtes")
st.caption("Version Python (Streamlit) — prototype pédagogique, non validé par Sodebo")
st.warning(
    "N'importez pas de donnees personnelles dans une demonstration publique. "
    "Le masquage des petites cellules ne garantit pas l'anonymat complet."
)

for key, default in (("survey", None), ("groups", {}), ("targets", []), ("result", None)):
    if key not in st.session_state:
        st.session_state[key] = default


def load_survey(survey):
    st.session_state.survey = survey
    st.session_state.groups = {}
    st.session_state.targets = []
    st.session_state.result = None


def safe(fn, message=None):
    try:
        fn()
        if message:
            st.success(message)
    except (AnalysisError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        st.error(str(exc))


def choices(survey):
    df = transformed(survey, st.session_state.groups)
    return {
        item["id"]: {
            "label": item["label"],
            "options": sorted(df[item["id"]].unique().tolist()),
        }
        for item in valid_variables(survey)
    }


data_tab, group_tab, target_tab, analysis_tab, save_tab = st.tabs(
    ["Données", "Regroupements", "Cibles", "Analyses", "Sauvegarde"]
)

with data_tab:
    st.subheader("Importer une enquête")
    if st.button("Charger les données de démonstration", type="primary"):
        def demo():
            csv = (BASE / "examples" / "reponses_demo.csv").read_bytes()
            schema = (BASE / "examples" / "questions_demo.json").read_bytes()
            load_survey(ingest(csv, "reponses_demo.csv", schema))
        safe(demo, "Données fictives chargées.")
    if UPLOADS_ENABLED:
        st.info("Import réservé à un déploiement local ou privé avec contrôle d'accès.")
        responses = st.file_uploader("Réponses CSV/XLSX", type=["csv", "xlsx"])
        schema = st.file_uploader("Structure JSON (facultatif)", type=["json"])
        if st.button("Importer et nettoyer", disabled=responses is None):
            safe(
                lambda: load_survey(
                    ingest(
                        responses.getvalue(), responses.name,
                        schema.getvalue() if schema else None,
                    )
                ),
                "Import réussi.",
            )
    else:
        st.info("Mode public : import désactivé. Utilisez les données fictives de démonstration.")
    if st.session_state.survey is not None:
        report = st.session_state.survey.report
        for col, label, field in zip(
            st.columns(4),
            ["Reçues", "Valides", "Invalides", "Doublons"],
            ["initial", "valid", "removed_invalid", "removed_duplicates"],
        ):
            col.metric(label, report[field])
        with st.expander("Rapport de nettoyage et exclusions"):
            st.json(report)

survey = st.session_state.survey

with group_tab:
    st.subheader("Regroupements personnalisés")
    if survey is None:
        st.info("Chargez d'abord des données.")
    else:
        opts = choices(survey)
        var = st.selectbox("Variable à regrouper", list(opts),
                           format_func=lambda v: opts[v]["label"])
        label = st.text_input("Nom du groupe, ex. Jeunes")
        modalities = st.multiselect(
            "Modalités originales à fusionner",
            sorted(survey.frame[var].unique().tolist()),
        )
        if st.button("Créer le regroupement"):
            def add_group():
                if not label.strip() or not modalities:
                    raise AnalysisError("Un nom et au moins une modalité sont nécessaires.")
                groups = json.loads(json.dumps(st.session_state.groups))
                if label.strip() in groups.get(var, {}):
                    raise AnalysisError("Ce nom de groupe existe déjà.")
                groups.setdefault(var, {})[label.strip()] = modalities
                st.session_state.groups = validate_groups(survey, groups)
                st.session_state.targets = []
                st.session_state.result = None
            safe(add_group, "Groupe enregistré. Les cibles ont été réinitialisées.")
        st.json(st.session_state.groups)
        if st.button("Réinitialiser les groupes"):
            st.session_state.groups = {}
            st.session_state.targets = []
            st.session_state.result = None
            st.success("Groupes supprimés.")

with target_tab:
    st.subheader("Constitution des cibles")
    if survey is None:
        st.info("Chargez d'abord des données.")
    else:
        opts = choices(survey)
        name = st.text_input("Nom de la cible")
        relation = st.radio("Relation", ["AND", "OR"], horizontal=True,
                            format_func=lambda v: "ET" if v == "AND" else "OU")
        count = st.slider("Nombre de conditions", 1, 8, 1)
        conditions = []
        for i in range(count):
            c1, c2 = st.columns(2)
            variable = c1.selectbox(
                f"Question {i+1}", list(opts),
                format_func=lambda v: opts[v]["label"], key=f"variable_{i}"
            )
            values = c2.multiselect(
                f"Modalités {i+1}", opts[variable]["options"], key=f"modalities_{i}"
            )
            conditions.append({"variable": variable, "values": values})
        if st.button("Ajouter la cible"):
            def add_target():
                if not name.strip() or any(not c["values"] for c in conditions):
                    raise AnalysisError("Nommez la cible et choisissez toutes les modalités.")
                proposed = st.session_state.targets + [
                    {"name": name.strip(), "combine": relation, "conditions": conditions}
                ]
                st.session_state.targets = validate_targets(
                    transformed(survey, st.session_state.groups), proposed
                )
                st.session_state.result = None
            safe(add_target, "Cible enregistrée.")
        st.json(st.session_state.targets)
        if st.button("Réinitialiser les cibles"):
            st.session_state.targets = []
            st.session_state.result = None

with analysis_tab:
    st.subheader("Tableaux croisés, graphiques et tests d'hypothèses")
    if survey is None:
        st.info("Chargez d'abord des données.")
    else:
        opts = choices(survey)
        x = st.selectbox("Variable principale", list(opts),
                         format_func=lambda v: opts[v]["label"])
        y = st.selectbox(
            "Croisement", [None] + [v for v in opts if v != x],
            format_func=lambda v: "Aucun (répartition simple)" if v is None else opts[v]["label"],
        )
        targets = [item["name"] for item in st.session_state.targets]
        target = st.selectbox(
            "Filtre/cible", [None] + targets,
            format_func=lambda v: "Tous les répondants" if v is None else v,
        )
        alpha = st.select_slider("Seuil alpha", options=[0.01, 0.05, 0.10], value=0.05)
        if st.button("Générer l'analyse", type="primary"):
            safe(lambda: st.session_state.update(
                result=analyze(
                    survey, st.session_state.groups,
                    st.session_state.targets, x, y, target, alpha
                )
            ))
        result = st.session_state.result
        if result:
            if result.get("blocked"):
                st.error(result.get("message", "Résultat masqué."))
            else:
                st.metric("Effectif analysé", result["n"])
                table = pd.DataFrame(
                    result["counts"], index=result["rows"], columns=result["columns"]
                )
                st.dataframe(table, use_container_width=True)
                st.bar_chart(table, use_container_width=True)
                test = result["test"]
                st.write("**Hypothèse :**", result["hypothesis"])
                st.write(f"**Test :** {test['name']}")
                if "p_value" in test:
                    st.write(f"p-valeur = {test['p_value']:.6g}")
                st.caption(test.get("message", ""))
                if test.get("status") == "caution":
                    st.warning("Hypothèses statistiques à vérifier avant toute conclusion.")
                st.caption(result["privacy"] + " " + result["interpretation_warning"])
                st.download_button(
                    "Télécharger les résultats agrégés (CSV)",
                    data=aggregate_csv(result), file_name="resultats_agreges.csv",
                    mime="text/csv",
                )

with save_tab:
    st.subheader("Enregistrer ou restaurer une session")
    if survey is None:
        st.info("Chargez d'abord des données.")
    else:
        config = {
            "version": 1,
            "fingerprint": survey.fingerprint,
            "groups": st.session_state.groups,
            "targets": st.session_state.targets,
        }
        st.download_button(
            "Exporter les réglages (JSON)",
            json.dumps(config, ensure_ascii=False, indent=2),
            file_name="configuration_sae.json", mime="application/json",
        )
        file = st.file_uploader("Importer des réglages", type=["json"], key="settings")
        if st.button("Restaurer les réglages", disabled=file is None):
            def restore():
                if len(file.getvalue()) > 200_000:
                    raise AnalysisError("Configuration trop volumineuse.")
                obj = json.loads(file.getvalue())
                if obj.get("version") != 1 or obj.get("fingerprint") != survey.fingerprint:
                    raise AnalysisError("La configuration correspond à une autre enquête.")
                groups = validate_groups(survey, obj.get("groups", {}))
                targets = validate_targets(
                    transformed(survey, groups), obj.get("targets", [])
                )
                st.session_state.groups = groups
                st.session_state.targets = targets
                st.session_state.result = None
            safe(restore, "Réglages restaurés.")
        if UPLOADS_ENABLED:
            st.divider()
            st.write("**Archive complète chiffrée (mode privé uniquement)**")
            phrase = st.text_input("Phrase secrète (12 caractères minimum)", type="password")
            if len(phrase) >= 12:
                try:
                    encrypted = encrypt_project(
                        survey, st.session_state.groups,
                        st.session_state.targets, phrase
                    )
                    st.download_button(
                        "Exporter l'archive chiffrée", encrypted,
                        file_name="session_sae.sae",
                        mime="application/octet-stream",
                    )
                except AnalysisError as exc:
                    st.error(str(exc))
            archive = st.file_uploader("Importer une archive chiffrée", type=["sae"])
            if st.button("Restaurer l'archive", disabled=archive is None):
                def open_archive():
                    restored, groups, targets = decrypt_project(
                        archive.getvalue(), phrase
                    )
                    load_survey(restored)
                    st.session_state.groups = groups
                    st.session_state.targets = targets
                safe(open_archive, "Archive restaurée.")

st.caption("Démonstration éducative : les données d'exemple sont entièrement fictives.")
