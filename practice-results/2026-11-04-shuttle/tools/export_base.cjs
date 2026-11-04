const fs=require('node:fs'),path=require('node:path');
const {readInput,ROOT}=require('../data.cjs'),{solve}=require('../planner.cjs'),{inspect}=require('../verify.cjs');
const decision=JSON.parse(fs.readFileSync(path.join(ROOT,'decision.json'),'utf8'));
const input=readInput({name:'base'});if(input.issues.length)throw Error('Invalid base input');
const plan=solve({...input,dataset_version:1,policy_version:1,dataset_fingerprint:input.fingerprint,policy:decision.policy});const checks=inspect(plan,input.tables,input.cfg);if(checks.problems.length)throw Error(JSON.stringify(checks.problems));
fs.mkdirSync(path.join(ROOT,'artifacts'),{recursive:true});fs.writeFileSync(path.join(ROOT,'artifacts/route_plan.json'),JSON.stringify(plan,null,2));console.log(JSON.stringify({status:plan.status,metrics:plan.metrics,generated_at:plan.generated_at,dataset_fingerprint:plan.dataset_fingerprint},null,2));
