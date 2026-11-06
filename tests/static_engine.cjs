'use strict';
// Run: node tests/static_engine.cjs
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../docs/pages');
const native=async url=>{const name=String(url).replace('./','');return new Response(fs.readFileSync(path.join(root,name)),{status:200});};
const context={window:{fetch:native},Response,TextDecoder,crypto:require('node:crypto').webcrypto,FormData,File,Blob,Uint8Array,structuredClone,console};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'browser-api.js'),'utf8'),context);
const request=async (url,method='GET',data)=>{
 const body=data===undefined?undefined:(data instanceof FormData?data:JSON.stringify(data));
 const response=await context.window.fetch(url,{method,body});
 const value=(response.headers.get('content-type')||'').includes('json')?await response.json():await response.text();
 return {status:response.status,body:value};
};
(async()=>{
 let st=(await request('/api/status')).body;assert.equal(st.loaded,false);
 let response=await request('/api/demo','POST');assert.equal(response.status,200);
 st=(await request('/api/status')).body;assert.equal(st.report.valid,434);assert.equal(st.report.removed_invalid,5);assert.equal(st.report.removed_duplicates,1);
 const a=(await request('/api/analyze','POST',{x:'age',y:'intention_achat'})).body;
 assert.equal(a.blocked,false);assert.equal(a.n,434);assert.ok(a.test.p_value>=0&&a.test.p_value<=1);console.log('chi2:',a.test.chi2,'p:',a.test.p_value);
 const exp=await request('/api/export/csv','POST',{x:'age',y:'intention_achat'});assert.equal(exp.status,200);assert.ok(exp.body.includes('Modalité'));
 const grp=(await request('/api/groups','PUT',{groups:{age:{Jeunes:['18-24','25-34']}}}));assert.equal(grp.status,200);
 const tar=(await request('/api/targets','PUT',{targets:[{name:'Acheteurs',combine:'AND',conditions:[{variable:'intention_achat',values:['Oui']}]}]}));assert.equal(tar.status,200);
 const a2=(await request('/api/analyze','POST',{x:'age',y:'produit_prefere',target:'Acheteurs'})).body;assert.equal(typeof a2.blocked,'boolean');
 const conf=(await request('/api/session/export')).body;const cfg=JSON.parse(conf);assert.equal(cfg.groups.age.Jeunes[0],'18-24');
 const form=new FormData();form.append('config',new File([JSON.stringify(cfg)],'config.json',{type:'application/json'}));
 const restored=await request('/api/session/import','POST',form);assert.equal(restored.status,200);
 const bad=new FormData();bad.append('config',new File([JSON.stringify({...cfg,fingerprint:'bad'})],'config.json',{type:'application/json'}));assert.equal((await request('/api/session/import','POST',bad)).status,422);
 const upload=new FormData();upload.append('responses',new File([fs.readFileSync(path.join(root,'reponses_demo.csv'))],'reponses.csv',{type:'text/csv'}));
 upload.append('structure',new File([fs.readFileSync(path.join(root,'questions_demo.json'))],'questions.json',{type:'application/json'}));
 assert.equal((await request('/api/upload','POST',upload)).status,200);
 assert.equal((await request('/api/status')).body.report.valid,434);
 console.log('STATIC ENGINE PASS: demo, quality, cross, tests, export, groups, targets, config, import, negative tests');
})().catch(e=>{console.error(e);process.exit(1)});