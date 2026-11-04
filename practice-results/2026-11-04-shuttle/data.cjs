const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {load,schemas,keys}=require('./tools/audit_inputs.cjs');
const ROOT=__dirname;
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const fileNames=[...Object.keys(schemas).map(x=>x+'.csv'),'constraints.json'].sort();
function csvText(table,rows){const q=v=>'"'+String(v??'').replaceAll('"','""')+'"';return schemas[table].map(q).join(',')+'\n'+rows.map(r=>schemas[table].map(k=>q(r[k])).join(',')).join('\n')+'\n';}
function contentsOf(tables,cfg){return Object.fromEntries(fileNames.map(f=>[f,f==='constraints.json'?JSON.stringify(cfg):csvText(f.slice(0,-4),tables[f.slice(0,-4)])]));}
function fingerprint(hashes){return sha(fileNames.map(f=>f+'\0'+hashes[f]).join('\n'));}
function snapshotNames(){return fs.readdirSync(path.join(ROOT,'datasets'),{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>x.name).sort((a,b)=>a==='base'?-1:b==='base'?1:a.localeCompare(b));}
function readInput({name,files}){
  if(files){if(typeof files!=='object'||Array.isArray(files))throw Error('files must be an object');if(Object.keys(files).sort().join('|')!==fileNames.join('|')||Object.values(files).some(v=>typeof v!=='string'))throw Error('Exactly 10 CSV files and constraints.json required');}
  else{if(!snapshotNames().includes(name))throw Error('Unknown snapshot');files=Object.fromEntries(fileNames.map(f=>[f,fs.readFileSync(path.join(ROOT,'datasets',name,f),'utf8')]));}
  const checked=load(null,files),hashes=Object.fromEntries(fileNames.map(f=>[f,sha(files[f])]));return {...checked,hashes,fingerprint:fingerprint(hashes),name:name||'uploaded'};
}
function sanitized(tables){let result=structuredClone(tables);result.demo_accounts=result.demo_accounts.map(({initial_password,...r})=>({...r,initial_password:'INITIALIZATION_ONLY'}));return result;}
function validateTables(tables,cfg){return load(null,contentsOf(tables,cfg)).issues;}
module.exports={ROOT,sha,fileNames,schemas,keys,csvText,contentsOf,fingerprint,snapshotNames,readInput,sanitized,validateTables};
