'use strict';
/* Moteur de démonstration 100 % navigateur : aucune requête API pour les microdonnées.
 * Le traitement statistique est indépendant de l'implémentation SciPy du backend.
 * À valider par un statisticien avant tout usage décisionnel réel.
 */
(function () {
  const K_MIN=10, MAX_BYTES=12*1024*1024;
  const SENSITIVE=['nom','prenom','prénom','email','e_mail','mail','telephone','téléphone','phone','adresse','address','ip_address','date_naissance','birth_date','identite','identité','respondent_id','id_repondant','répondant_id'];
  const BAD_MISSING=['','nan','null','n/a','nr','non renseigné'];
  const nativeFetch=window.fetch.bind(window);
  let survey=null,groups={},targets=[];
  const fail=(text)=>{throw new Error(text)};
  const keys=obj=>Object.keys(obj);
  const uniq=vals=>[...new Set(vals)];
  const sort=arr=>arr.slice().sort((a,b)=>String(a).localeCompare(String(b),'fr'));
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const isSensitive=(key)=>SENSITIVE.some(v=>key.toLowerCase().replace(/[^\da-z_éèêàâîôûùç]/g,'_').includes(v));

  // Parseur CSV avec guillemets, retours ligne et détection du séparateur.
  function csvParse(text){
    if(text.charCodeAt(0)===0xfeff)text=text.slice(1);
    const firstLine=text.split(/\r?\n/,1)[0];
    const d=[';',',','\t'].map(sep=>({sep,count:firstLine.split(sep).length})).sort((a,b)=>b.count-a.count)[0].sep;
    const rows=[];let row=[],field='',quoted=false;
    for(let i=0;i<text.length;i++){
      const c=text[i];
      if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}
      else if(!quoted&&c===d){row.push(field.trim());field='';}
      else if(!quoted&&(c==='\n'||c==='\r')){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field.trim());if(row.some(x=>x!==''))rows.push(row);row=[];field='';if(rows.length>100001)fail('Limite de 100 000 réponses dépassée.');}
      else field+=c;
    }
    if(quoted)fail('CSV invalide : guillemet non fermé.');
    row.push(field.trim());if(row.some(x=>x!==''))rows.push(row);
    if(rows.length<2)fail('CSV vide : une ligne d’en-tête et des réponses sont attendues.');
    const header=rows.shift();
    if(header.length>100||!header.length||header.some(v=>!v)||uniq(header).length!==header.length)fail('Noms de colonnes vides, doublés ou plus de 100 colonnes.');
    if(rows.some(row=>row.length!==header.length))fail('CSV mal formé : nombre de colonnes incohérent.');
    return {header,rows:rows.map(items=>Object.fromEntries(header.map((h,i)=>[h,items[i]])))};
  }
  function parseSchema(blob,columns){
    if(!blob)return Object.fromEntries(columns.map(c=>[c,{label:c.replaceAll('_',' '),type:'categorical',required:true,allowed_values:[],identifier:false}]));
    if(!Array.isArray(blob)||!blob.length)fail('Le questionnaire doit être une liste JSON non vide.');
    const meta={};
    for(const q of blob){
      if(!q||typeof q.id!=='string'||!columns.includes(q.id)||q.id in meta)fail('Question absente, en doublon ou sans identifiant.');
      if(!['categorical','ordinal','identifier','text'].includes(q.type??'categorical'))fail('Type de question non pris en charge.');
      if(q.allowed_values!==undefined&&(!Array.isArray(q.allowed_values)||q.allowed_values.some(x=>!['string','number'].includes(typeof x))))fail('Modalités invalides.');
      meta[q.id]={label:String(q.label??q.id).slice(0,160),type:q.type??'categorical',required:q.required!==false,
        allowed_values:uniq((q.allowed_values??[]).map(String).map(x=>x.trim())),identifier:!!q.identifier||q.type==='identifier'};
    }
    return meta;
  }
  async function digest(raw){const data=await crypto.subtle.digest('SHA-256',raw);return [...new Uint8Array(data)].map(x=>x.toString(16).padStart(2,'0')).join('');}
  async function ingest(raw,filename,schemaText){
    if(raw.byteLength>MAX_BYTES)fail('Fichier trop volumineux (limite 12 Mo).');
    if(!filename.toLowerCase().endsWith('.csv'))fail('Sur GitHub Pages, seul le format CSV est accepté.');
    const parsed=csvParse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
    const meta=parseSchema(schemaText?JSON.parse(schemaText):null,parsed.header);
    const reasons={};let invalid=0,duplicate=0;const ids=keys(meta).filter(c=>meta[c].identifier||(isSensitive(c)&&c.toLowerCase().includes('id')));
    const usedIds=new Set(),valid=[];
    for(const row of parsed.rows){
      let bad=false;
      for(const c of keys(meta)){
        const v=row[c],m=meta[c];
        const missing=BAD_MISSING.includes(v.toLowerCase());
        const thisBad=(missing&&m.required)||(!missing&&m.allowed_values.length&&!m.allowed_values.includes(v));
        if(thisBad){reasons[c]=(reasons[c]??0)+1;bad=true;}
      }
      if(bad){invalid++;continue;}
      if(ids.length){const id=row[ids[0]];if(usedIds.has(id)){duplicate++;continue;}usedIds.add(id);}
      valid.push(row);
    }
    const excluded=parsed.header.filter(c=>!meta[c]||meta[c].identifier||['text','identifier'].includes(meta[c].type)||isSensitive(c));
    const allowed=keys(meta).filter(c=>!excluded.includes(c));
    if(!allowed.length)fail('Aucune variable catégorielle exploitable.');
    survey={rows:valid.map(row=>Object.fromEntries(allowed.map(c=>[c,row[c]]))),meta:Object.fromEntries(allowed.map(c=>[c,meta[c]])),
      fingerprint:await digest(raw),report:{initial:parsed.rows.length,valid:valid.length,removed_invalid:invalid,removed_duplicates:duplicate,
      errors_by_variable:reasons,excluded_columns:sort(excluded),privacy_note:'Identifiants et textes exclus du moteur. Aucun transfert réseau des réponses ; anonymat complet non garanti face aux analyses successives.'}};
    groups={};targets=[];
  }
  function variableList(){
    const rows=transformed();
    return keys(survey.meta).map(id=>({id,label:survey.meta[id].label,type:survey.meta[id].type,modalities:sort(uniq(rows.map(r=>r[id])))}));
  }
  function validatedGroups(g){
    if(!g||typeof g!=='object'||Array.isArray(g))fail('Format de regroupements invalide.');
    for(const [variable,named] of Object.entries(g)){
      if(!(variable in survey.meta)||!named||typeof named!=='object'||Array.isArray(named))fail('Variable de groupe inconnue.');
      const used=new Set(),existing=new Set(survey.rows.map(r=>r[variable]));
      for(const [label,vals] of Object.entries(named)){
        if(!label.trim()||label.length>80||!Array.isArray(vals)||!vals.length||vals.some(v=>typeof v!=='string'))fail('Nom ou valeurs de groupe invalides.');
        if(vals.some(v=>used.has(v)||!existing.has(v)))fail('Une modalité a déjà été regroupée ou est inconnue.');
        vals.forEach(v=>used.add(v));
      }
    }
    return g;
  }
  function transformed(g=groups){
    if(!survey)fail('Chargez d’abord les réponses.');
    validatedGroups(g);
    const reverse={};
    for(const [variable,named] of Object.entries(g)){reverse[variable]={};for(const [name,vals] of Object.entries(named))vals.forEach(v=>reverse[variable][v]=name);}
    return survey.rows.map(row=>Object.fromEntries(keys(row).map(c=>[c,reverse[c]?.[row[c]]??row[c]])));
  }
  function validatedTargets(ts,rows){
    if(!Array.isArray(ts)||ts.length>20)fail('Maximum 20 cibles.');
    const seen=new Set(),cols=keys(survey.meta);
    for(const t of ts){
      if(!t||typeof t.name!=='string'||!t.name.trim()||t.name.length>80||seen.has(t.name))fail('Nom de cible invalide ou déjà présent.');
      if(!['AND','OR'].includes(t.combine)||!Array.isArray(t.conditions)||!t.conditions.length||t.conditions.length>8)fail('Conditions de cible invalides.');
      for(const c of t.conditions){if(!cols.includes(c.variable)||!Array.isArray(c.values)||!c.values.length||c.values.some(v=>!new Set(rows.map(r=>r[c.variable])).has(v)))fail('Condition de cible invalide.');}
      seen.add(t.name);
    }
    return ts;
  }
  function targetMatch(row,t){const parts=t.conditions.map(c=>c.values.includes(row[c.variable]));return t.combine==='OR'?parts.some(Boolean):parts.every(Boolean);}
  // logΓ et fonction gamma incomplète régularisée Q(a,x), pour les p-valeurs du χ².
  function logGamma(z){const p=[0.99999999999980993,676.5203681218851,-1259.1392167224028,771.32342877765313,-176.61502916214059,12.507343278686905,-0.13857109526572012,9.984369578019572e-6,1.5056327351493116e-7];if(z<.5)return Math.log(Math.PI)-Math.log(Math.sin(Math.PI*z))-logGamma(1-z);z-=1;let x=p[0];for(let i=1;i<p.length;i++)x+=p[i]/(z+i);const t=z+7.5;return .5*Math.log(2*Math.PI)+(z+.5)*Math.log(t)-t+Math.log(x);}
  function gammaQ(a,x){if(x<=0)return 1;if(x<a+1){let sum=1/a,del=sum,ap=a;for(let n=1;n<2000;n++){ap++;del*=x/ap;sum+=del;if(Math.abs(del)<Math.abs(sum)*1e-13)break;}return Math.max(0,1-sum*Math.exp(-x+a*Math.log(x)-logGamma(a)));}let b=x+1-a,c=1e30,d=1/(Math.abs(b)<1e-30?1e-30:b),h=d;for(let n=1;n<2000;n++){const an=-n*(n-a);b+=2;d=an*d+b;if(Math.abs(d)<1e-30)d=1e-30;c=b+an/c;if(Math.abs(c)<1e-30)c=1e-30;d=1/d;const delta=d*c;h*=delta;if(Math.abs(delta-1)<1e-13)break;}return Math.min(1,Math.max(0,Math.exp(-x+a*Math.log(x)-logGamma(a))*h));}
  function fisher2x2(t){const a=t[0][0],r1=t[0][0]+t[0][1],r2=t[1][0]+t[1][1],c1=t[0][0]+t[1][0],n=r1+r2,lo=Math.max(0,c1-r2),hi=Math.min(r1,c1);const lchoose=(n,k)=>logGamma(n+1)-logGamma(k+1)-logGamma(n-k+1);const logp=k=>lchoose(r1,k)+lchoose(r2,c1-k)-lchoose(n,c1);const lp=logp(a);let total=0;for(let k=lo;k<=hi;k++){const pk=logp(k);if(pk<=lp+1e-9)total+=Math.exp(pk);}return Math.min(1,total);}
  function testIndependence(t,alpha){
    const nonZeroRows=t.filter(row=>row.some(v=>v>0));if(nonZeroRows.length<2||t[0].length<2)return {name:'Indépendance',status:'not_applicable',message:'Deux modalités par variable au moins sont nécessaires.'};
    const mat=nonZeroRows;const rs=mat.map(r=>r.reduce((a,b)=>a+b,0)),cs=mat[0].map((_,j)=>mat.reduce((s,row)=>s+row[j],0)),n=rs.reduce((a,b)=>a+b,0);
    if(cs.some(c=>c===0))return {name:'Indépendance',status:'not_applicable',message:'Colonne nulle.'};
    let chi=0,min=Infinity;mat.forEach((row,i)=>row.forEach((v,j)=>{const expected=rs[i]*cs[j]/n;chi+=(v-expected)**2/expected;min=Math.min(min,expected);}));
    const df=(mat.length-1)*(cs.length-1),v=Math.sqrt(chi/(n*Math.min(mat.length-1,cs.length-1))),weak=min<5;
    if(weak&&mat.length===2&&cs.length===2){const p=fisher2x2(mat);return {name:'Test exact de Fisher (2×2)',status:'ok',p_value:p,chi2:chi,df,cramers_v:v,min_expected:min,significant:p<alpha,alpha,message:'Effectifs attendus faibles : test exact de Fisher. χ² et V sont descriptifs.'};}
    const p=gammaQ(df/2,chi/2);
    return {name:'Khi-deux d’indépendance',status:weak?'caution':'ok',p_value:p,chi2:chi,df,cramers_v:v,min_expected:min,significant:weak?null:p<alpha,alpha,message:weak?'Effectifs théoriques inférieurs à 5 : interprétation non fiable.':'H₀ : variables indépendantes ; V de Cramér mesure l’association.'};
  }
  function analyze({x,y=null,target=null,alpha=.05}){
    if(!survey)fail('Chargez d’abord une enquête.');
    if(!(alpha>0&&alpha<1))fail('Alpha invalide.');
    if(!(x in survey.meta)||(y&&(!(y in survey.meta)||x===y)))fail('Variables invalides ou identiques.');
    const rows=transformed(),t=target?targets.find(v=>v.name===target):null;
    if(target&&!t)fail('Cible inconnue.');
    const sample=t?rows.filter(r=>targetMatch(r,t)):rows;
    if(sample.length<K_MIN)return {blocked:true,message:`Analyse masquée : cible de moins de ${K_MIN} répondants.`,n:null,k_min:K_MIN};
    let data,columns,lines,mode,test,hypothesis;
    if(y){data=sample;columns=sort(uniq(sample.map(r=>r[y])));lines=sort(uniq(sample.map(r=>r[x])));mode='cross';hypothesis=`H₀ : ${x} et ${y} sont indépendantes.`;}
    else if(t){data=rows.map(r=>({...r,__target:targetMatch(r,t)?'Cible':'Hors cible'}));columns=['Cible','Hors cible'];lines=sort(uniq(rows.map(r=>r[x])));y='__target';mode='target';hypothesis=`H₀ : la répartition de ${x} est identique dans et hors de la cible.`;}
    else {data=sample;columns=['Effectif'];lines=sort(uniq(sample.map(r=>r[x])));mode='distribution';hypothesis=`H₀ technique : toutes les modalités de ${x} sont équiprobables.`;}
    const tcounts=lines.map(a=>columns.map(b=>data.filter(r=>r[x]===a&&(!y||r[y]===b)).length));
    // Le moteur ne transmet aucune cellule ni statistique si une cellule 1..9 existe.
    if(tcounts.some(row=>row.some(c=>c>0&&c<K_MIN)))return {blocked:true,message:`Tableau et graphique masqués : une cellule contient 1 à ${K_MIN-1} individus.`,n:null,k_min:K_MIN};
    if(!y){if(lines.length<2)test={name:'Adéquation',status:'not_applicable',message:'Au moins deux modalités sont nécessaires.'};else {const expect=sample.length/lines.length,chi=tcounts.reduce((s,r)=>s+(r[0]-expect)**2/expect,0);test={name:'Khi-deux d’adéquation (répartition uniforme)',status:'caution',chi2:chi,p_value:gammaQ((lines.length-1)/2,chi/2),df:lines.length-1,significant:null,alpha,message:'H₀ : répartition uniforme ; hypothèse technique à faire valider, non interprétable comme comparaison de groupes.'};}}
    else test=testIndependence(tcounts,alpha);
    return {blocked:false,n:sample.length,mode,x,y:y==='__target'?null:y,target,rows:lines,columns,counts:tcounts,percentages_by_row:tcounts.map(row=>row.map(c=>row.reduce((a,b)=>a+b,0)?Math.round(c*1000/row.reduce((a,b)=>a+b,0))/10:0)),test,hypothesis,privacy:`Seuil de diffusion : ${K_MIN} répondants par cellule non nulle.`,interpretation_warning:'Les p-valeurs ne prouvent pas la causalité. Valider plan de sondage, pondérations et comparaisons multiples.'};
  }
  function csvResult(q){const res=analyze(q);if(res.blocked)fail('Export interdit pour analyse masquée.');const safe=s=>/^[=+\-@\t\r]/.test(String(s))?'\''+s:s;const lines=[['Modalité',...res.columns.map(safe)],...res.rows.map((v,i)=>[safe(v),...res.counts[i]])];return '\ufeff'+lines.map(r=>r.map(s=>String(s).includes(';')||String(s).includes('"')?'"'+String(s).replaceAll('"','""')+'"':String(s)).join(';')).join('\r\n');}
  function json(obj){return new Response(JSON.stringify(obj),{headers:{'Content-Type':'application/json;charset=utf-8'}});}
  function file(data,type){return new Response(data,{headers:{'Content-Type':type}});}
  async function localFetch(path,opts={}){
    if(!path.startsWith('/api/'))return nativeFetch(path,opts);
    try{
      const body=opts.body instanceof FormData?opts.body:opts.body?JSON.parse(opts.body):{};
      if(path==='/api/status')return json(survey?{loaded:true,report:survey.report,variables:variableList(),groups,targets,k_min:K_MIN,fingerprint:survey.fingerprint.slice(0,12)}:{loaded:false,k_min:K_MIN});
      if(path==='/api/demo'){
        const [r,s]=await Promise.all([nativeFetch('./reponses_demo.csv'),nativeFetch('./questions_demo.json')]);
        if(!r.ok||!s.ok)fail('Fichiers de démonstration inaccessibles.');
        await ingest(await r.arrayBuffer(),'demo.csv',await s.text());return json({message:'Jeu synthétique chargé.',report:survey.report});
      }
      if(path==='/api/upload'){
        const file=body.get('responses'),schema=body.get('structure');if(!file||!file.name)fail('Fichier CSV manquant.');
        const sch=schema&&schema.size?await schema.text():null;
        if(sch&&new Blob([sch]).size>200000)fail('Structure JSON trop volumineuse.');
        await ingest(await file.arrayBuffer(),file.name,sch);return json({message:'Import réussi',report:survey.report});
      }
      if(!survey)fail('Chargez d’abord un jeu de réponses.');
      if(path==='/api/groups'){
        validatedGroups(body.groups);const rows=transformed(body.groups);groups=structuredClone(body.groups);
        try{validatedTargets(targets,rows);}catch{targets=[];}
        return json({message:'Regroupements enregistrés'});
      }
      if(path==='/api/targets'){validatedTargets(body.targets,transformed());targets=structuredClone(body.targets);return json({message:'Cibles enregistrées',count:targets.length});}
      if(path==='/api/analyze')return json(analyze(body));
      if(path==='/api/export/csv')return file(csvResult(body),'text/csv; charset=utf-8');
      if(path==='/api/session/export')return file(JSON.stringify({version:1,fingerprint:survey.fingerprint,groups,targets},null,2),'application/octet-stream');
      if(path==='/api/session/import'){
        const config=body.get('config');if(!config||config.size>200000)fail('Configuration illisible ou volumineuse.');
        const obj=JSON.parse(await config.text());
        if(obj.version!==1||obj.fingerprint!==survey.fingerprint)fail('La configuration ne correspond pas au fichier importé.');
        validatedGroups(obj.groups);validatedTargets(obj.targets,transformed(obj.groups));groups=structuredClone(obj.groups);targets=structuredClone(obj.targets);return json({message:'Configuration restaurée.'});
      }
      fail('Cette fonctionnalité nécessite le serveur Python.');
    }catch(e){return new Response(JSON.stringify({detail:e instanceof SyntaxError?'JSON ou CSV invalide.':e.message}),{status:422,headers:{'Content-Type':'application/json'}});}
  }
  window.SAE_DEMO={analyze:q=>analyze(q),getStatus:()=>survey&&({report:survey.report,variables:variableList(),groups,targets}),gammaQ};
  window.fetch=localFetch;
})();