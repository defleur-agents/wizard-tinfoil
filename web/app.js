"use strict";
const el=id=>document.getElementById(id);
let busy=false;
function render(s){el('connection').textContent=s.status==='connected'?'Connected':s.credentialStored?'Key saved · awaiting first successful request':'Not connected';el('verified').textContent=s.verification.lastVerifiedAt?'Attestation last verified: '+new Date(s.verification.lastVerifiedAt).toLocaleString():'No verified connection yet.';el('models').textContent=s.models.length?s.models.join(' · '):'Connect to load available models.';el('test').disabled=el('disconnect').disabled=busy||!s.credentialStored;}
async function request(path,body){const r=await fetch(path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json','X-Wizard-Request':'1'},body:JSON.stringify(body)});const s=await r.json();if(!r.ok)throw Error(s.error||'Connection unavailable.');return s;}
async function action(path,body){if(busy)return;busy=true;for(const b of document.querySelectorAll('button'))b.disabled=true;el('status').textContent='Verifying securely…';try{await request(path,body);el('status').textContent=path.endsWith('disconnect')?'Disconnected. Local gateway credential rotated.':'Key saved; enclave verified. API-key validity is confirmed only by a successful inference request.';}catch(e){el('status').textContent=e.message;}finally{busy=false;el('connect').disabled=false;request('api/connection').then(render).catch(()=>{el('status').textContent='Connection status unavailable.';});}}
el('connect-form').onsubmit=e=>{e.preventDefault();const key=el('api-key').value;el('api-key').value='';action('api/connect',{apiKey:key});};
el('test').onclick=()=>action('api/test',{});el('disconnect').onclick=()=>action('api/disconnect',{});
window.__wizardCloseOverlay=()=>false;
request('api/connection').then(render).catch(e=>{el('status').textContent=e.message;});
