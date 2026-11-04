const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {DatabaseSync}=require('node:sqlite');
const {readInput,sanitized,sha}=require('./data.cjs');
function passwordHash(value,salt=crypto.randomBytes(16).toString('hex')){return salt+':'+crypto.scryptSync(value,salt,64).toString('hex');}
function passwordOK(value,hash){const [salt,h]=hash.split(':');const actual=Buffer.from(passwordHash(value,salt).split(':')[1],'hex'),expected=Buffer.from(h,'hex');return actual.length===expected.length&&crypto.timingSafeEqual(actual,expected);}
function openStore(filename){fs.mkdirSync(path.dirname(filename),{recursive:true});const db=new DatabaseSync(filename);db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), json TEXT NOT NULL); CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, role TEXT NOT NULL, employee_id TEXT, active INTEGER NOT NULL, password_hash TEXT NOT NULL); CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, csrf TEXT NOT NULL, expires INTEGER NOT NULL);');
 let state;const row=db.prepare('SELECT json FROM state WHERE id=1').get();
 if(row){state=JSON.parse(row.json);if(['UPDATING','CALCULATING'].includes(state.status)){state.status='ERROR';state.error='서버가 계산 도중 재시작되었습니다. 자동 복구 계산을 시작합니다.';}}
 else{const source=readInput({name:'base'});if(source.issues.length)throw Error('Invalid base');state={dataset_version:1,policy_version:1,name:'base',tables:sanitized(source.tables),cfg:source.cfg,hashes:source.hashes,dataset_fingerprint:source.fingerprint,policy:null,status:'AWAITING_POLICY',plan:null,previous_plan:null,last_success:null,last_validation:{ok:true,issues:[],at:new Date().toISOString()},history:[],decision_log:[]};
 db.exec('BEGIN IMMEDIATE');try{for(const u of source.tables.demo_accounts)db.prepare('INSERT INTO users VALUES(?,?,?,?,?)').run(u.username,u.role,u.employee_id,Number(u.active),passwordHash(u.initial_password));db.prepare('INSERT INTO state VALUES(1,?)').run(JSON.stringify(state));db.exec('COMMIT');}catch(e){db.exec('ROLLBACK');throw e;}}
 function save(next){db.exec('BEGIN IMMEDIATE');try{db.prepare('UPDATE state SET json=? WHERE id=1').run(JSON.stringify(next));db.exec('COMMIT');state=next;}catch(e){db.exec('ROLLBACK');throw e;}}
 const get=()=>structuredClone(state);
 function login(username,password){const u=db.prepare('SELECT * FROM users WHERE username=? AND active=1').get(username);if(!u||!passwordOK(password,u.password_hash))return null;const token=crypto.randomBytes(32).toString('hex'),csrf=crypto.randomBytes(24).toString('hex');db.prepare('DELETE FROM sessions WHERE expires<?').run(Date.now());db.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run(sha(token),u.username,csrf,Date.now()+8*60*60*1000);return {token,csrf,user:{username:u.username,role:u.role,employee_id:u.employee_id}};}
 function session(token){if(!token)return null;return db.prepare('SELECT u.username,u.role,u.employee_id,s.csrf FROM sessions s JOIN users u ON u.username=s.username WHERE s.token_hash=? AND s.expires>? AND u.active=1').get(sha(token),Date.now())||null;}
 return {db,get,save,login,session,logout:token=>db.prepare('DELETE FROM sessions WHERE token_hash=?').run(sha(token||'')),close:()=>db.close()};
}
module.exports={openStore,passwordHash,passwordOK};
