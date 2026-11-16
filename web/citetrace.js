import {createClient} from 'genlayer-js';
import {testnetBradbury} from 'genlayer-js/chains';
import {parseEther,formatEther} from 'viem';
const CONTRACT='0x9D34993A82039478b496a2fAe403BA12DD6e14AA',DEMO='0xF10aB469555eb723d62A565217EE678A8C200526';
const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const storageKey='citetrace-pending-v1',rpc=location.origin+'/rpc';
let account=null,client,items=[],selected=new URLSearchParams(location.search).get('review')||'1',roundNumber=Number(new URLSearchParams(location.search).get('round'))||1,busy=false,pending=null;
const originalFetch=globalThis.fetch;
globalThis.fetch=async(url,options={})=>{
 if(String(url).startsWith('https://rpc-bradbury.genlayer.com')||String(url).startsWith('https://rpc.testnet-chain.genlayer.com'))url=rpc;
 if(String(url)===rpc&&options.body){const body=JSON.parse(options.body);if(body.method==='eth_call'&&body.params?.[0])body.params[0].from??=account||DEMO;options={...options,body:JSON.stringify(body)};}
 const r=await originalFetch(url,options);
 if(String(url)===rpc&&options.body&&JSON.parse(options.body).method==='eth_estimateGas'){const result=await r.clone().json();if(result.error)throw Error('Gas estimation failed. No transaction was requested.');}
 return r;
};
const makeClient=provider=>createClient({chain:testnetBradbury,endpoint:rpc,account:account||DEMO,...(provider?{provider}:{})});
client=makeClient();
function message(text,error=false){$('#notice').textContent=text;$('#notice').className=error?'danger':'';}
function short(a){return a.slice(0,8)+'…'+a.slice(-6);}
function lock(value){busy=value;document.querySelectorAll('button').forEach(b=>b.disabled=value);if(!value)renderDetail();}
function savePending(value){pending=value;if(value)localStorage.setItem(storageKey,JSON.stringify(value));else localStorage.removeItem(storageKey);renderPending();}
function renderPending(){const box=$('#pending-panel');box.hidden=!pending;if(!pending)return;$('#recover-form').hidden=!!pending.hash;$('#resume').hidden=!pending.hash;$('#tx').hidden=!pending.hash;if(pending.hash)$('#tx').href='https://scan.bradbury.genlayer.com/tx/'+pending.hash;}
function current(){return items.find(r=>r.id===selected);}
function round(){return current()?.rounds.find(r=>r.number===roundNumber);}
async function connect(){
 if(!window.ethereum)throw Error('Open this page in a wallet browser or enable an EIP-1193 wallet extension, such as MetaMask or OKX Wallet. Public reviews remain readable without one.');
 const addresses=await window.ethereum.request({method:'eth_requestAccounts'});if(!addresses[0])throw Error('No wallet selected.');
 account=addresses[0];client=makeClient(window.ethereum);$('#connect').textContent=short(account);await load();
}
async function network(){
 if(Number(await window.ethereum.request({method:'eth_chainId'}))!==4221){try{await window.ethereum.request({method:'wallet_switchEthereumChain',params:[{chainId:'0x107d'}]});}catch(e){if(e.code!==4902)throw e;await window.ethereum.request({method:'wallet_addEthereumChain',params:[{chainId:'0x107d',chainName:'GenLayer Bradbury',nativeCurrency:{name:'GEN',symbol:'GEN',decimals:18},rpcUrls:['https://rpc.testnet-chain.genlayer.com'],blockExplorerUrls:['https://scan.bradbury.genlayer.com']}]});}}
 if(Number(await window.ethereum.request({method:'eth_chainId'}))!==4221)throw Error('Bradbury chain 4221 is required.');
}
async function fees(){const q=await client.estimateTransactionFees({leaderTimeunitsAllocation:300n,validatorTimeunitsAllocation:300n,executionBudgetPerRound:parseEther('0.025'),totalMessageFees:0n,appealRounds:0n,rotations:[0n]});if(q.feeValue>parseEther('0.2'))throw Error('Quoted protocol deposit exceeds 0.2 test GEN. No transaction requested.');return {distribution:q.distribution,feeValue:q.feeValue};}
async function waitFinal(){
 if(!pending?.hash)return;
 lock(true);try{
  message('Tracking the original transaction. Waiting for validator consensus, finality and refunds; no additional transaction is sent.');
  const r=await client.waitForFinalization({hash:pending.hash,interval:5000,retries:120,fullTransaction:true});
  const operation=pending;savePending(null);
  const accepted=r.statusName==='FINALIZED'&&r.resultName==='MAJORITY_AGREE'&&r.lifecycle?.outcome==='accepted'&&r.txExecutionResultName==='FINISHED_WITH_RETURN';
  if(!accepted){await load();throw Error('Transaction settled without a successful state update: '+r.resultName+' / '+r.txExecutionResultName+'. Inspect its explorer receipt before deciding whether a new attempt is appropriate.');}
  if(operation.action==='create_review')selected=null;
  await load();
  if(operation.action==='propose_round'){const record=current();const mine=record?.rounds.filter(x=>x.author.toLowerCase()===operation.account.toLowerCase()&&x.parent===operation.parent);if(mine?.length)roundNumber=mine.at(-1).number;render();}
  $('#create-dialog').close();message('Finalized with majority agreement. The public contract state has been read back below.');
 }catch(e){message(e.shortMessage||e.message,true);}finally{lock(false);renderPending();}
}
async function write(action,args){
 if(busy)return;
 let walletRequested=false;
 try{
  if(pending)throw Error('An earlier wallet request is unresolved. Track the original transaction above before another write.');
  if(!account)await connect();await network();lock(true);message('Estimating the protocol deposit. Only testnet GEN is used.');
  const fee=await fees();
  savePending({action,account,contract:CONTRACT,parent:action==='propose_round'?args[1]:null,startedAt:new Date().toISOString(),hash:null});walletRequested=true;
  message('Review the wallet request. Protocol deposit: '+formatEther(fee.feeValue)+' test GEN; unused budget is refunded after finalization. Never approve a different network or unexpected recipient.');
  const hash=await client.writeContract({address:CONTRACT,functionName:action,args,consensusMaxRotations:0,fees:fee});
  savePending({...pending,hash});await waitFinal();
 }catch(e){
  if(walletRequested&&Number(e.code??e.cause?.code)===4001)savePending(null);
  message((e.shortMessage||e.message)+(pending&&!pending.hash?' The wallet request may have been sent. Check your wallet/explorer and enter its transaction ID above; this page will not resend automatically.':''),true);
 }finally{lock(false);}
}
async function load(){
 try{
  $('#load-status').textContent='Reading the public contract…';
  const raw=await client.readContract({address:CONTRACT,functionName:'list_reviews',args:[0,20]});const d=typeof raw==='string'?JSON.parse(raw):raw;items=d.items||[];
  if(!items.some(x=>x.id===selected)){selected=items[0]?.id;roundNumber=1;}
  if(!current()?.rounds.some(x=>x.number===roundNumber))roundNumber=current()?.rounds[0]?.number||1;
  $('#load-status').textContent=d.total+' public review'+(d.total===1?'':'s')+' · live on Bradbury';$('#record-count').textContent=d.total;render();
 }catch(e){$('#load-status').textContent='Public RPC unavailable';message('Could not read the contract: '+(e.shortMessage||e.message)+'. Refresh retries a read and never resends a write.',true);}
}
const labels={support_only:'Support only',contradiction_only:'Contradiction only',conflicted:'Conflicting evidence',insufficient:'Insufficient evidence'};
const descriptions={support_only:'The committed excerpts include support and no explicit contradiction. This is not proof of truth.',contradiction_only:'The committed excerpts include contradiction and no explicit support. This is not a verdict on source reliability.',conflicted:'Support and contradiction coexist in this snapshot. Source count does not settle the disagreement.',insufficient:'The committed excerpts do not establish support or contradiction for this exact claim.'};
function render(){
 $('#records').innerHTML=items.map(r=>`<button class="record ${selected===r.id?'selected':''}" data-id="${esc(r.id)}"><span class="record-number">REVIEW ${esc(r.id.padStart(3,'0'))}</span><strong>${esc(r.title)}</strong><span class="meta">${r.rounds.length} round${r.rounds.length===1?'':'s'} · ${r.rounds.filter(x=>x.status==='resolved').length} resolved</span></button>`).join('');
 $('#records').querySelectorAll('button').forEach(b=>b.onclick=()=>{selected=b.dataset.id;roundNumber=1;render();});renderDetail();
}
function renderDetail(){
 const c=current(),r=round();if(!c||!r){$('#detail').innerHTML='<div class="empty"><span>＋</span><h3>Your first evidence trail starts here</h3><p>Create a public review with a specific claim and an exact source excerpt.</p></div>';return;}
 const owned=account?.toLowerCase()===r.author.toLowerCase(),disabled=busy||pending?'disabled':'';
 const verdict=r.result?.verdict;
 $('#detail').innerHTML=`<div class="detail-top"><div><div class="eyebrow">REVIEW ${esc(c.id.padStart(3,'0'))} / PUBLIC EVIDENCE TRAIL</div><h3>${esc(c.title)}</h3></div><div class="detail-actions"><button id="share">Copy link ↗</button><button id="export">Export JSON ↓</button></div></div><div class="claim">${esc(c.claim)}</div><div class="rounds">${c.rounds.map(x=>`<button class="round-button ${x.number===r.number?'active':''}" data-round="${x.number}">Round ${x.number}<small>${x.parent?'FROM ROUND '+x.parent:'ORIGINAL SNAPSHOT'} · ${esc(x.status.toUpperCase())}</small></button>`).join('')}</div><div class="result-banner ${esc(verdict||'committed')}"><div><strong>${esc(verdict?labels[verdict]:'Snapshot committed')}</strong><p>${esc(verdict?descriptions[verdict]:'The evidence is frozen. Its author can now request independent GenLayer classification.')}</p></div>${r.status==='committed'?`<button class="button" id="resolve" ${disabled||(!owned?'disabled':'')}>Resolve this round →</button>`:`<span class="badge ${esc(verdict)}">FINAL ROUND</span>`}</div><div class="round-meta">Round author ${esc(r.author)}${r.status==='committed'&&!owned?'<br>Connect this round’s author wallet to resolve it.':''}</div><div class="hash">SNAPSHOT SHA-256 ${esc(r.snapshot_sha256)}</div><div class="evidence-heading"><h4>Committed evidence</h4><span>${r.sources.length} SOURCE${r.sources.length===1?'':'S'} · CONTRIBUTOR-SUPPLIED</span></div>${r.sources.map((s,i)=>{const item=r.result?.classifications.find(x=>x.id===i+1);return `<section class="evidence-card"><div class="evidence-header"><strong>${i+1}. ${esc(s.reference)}</strong><span class="badge ${esc(item?.relation||'')}">${esc(item?.relation||'pending')}</span></div><blockquote>${esc(s.excerpt)}</blockquote></section>`;}).join('')}${r.status==='resolved'?`<section class="challenge"><h4>Add evidence. Open a new branch.</h4><p>Round ${r.number} stays unchanged. Your new round includes this snapshot’s sources plus your additional excerpt. Anyone may propose a branch; only its author can resolve it.</p>${c.rounds.length>=12||r.sources.length>=8?'<p>This record reached its round or source limit. Start a separate review if further evidence is needed.</p>':`<form id="challenge-form"><label>New source reference<input name="reference" minlength="3" maxlength="200" required placeholder="Document name, citation or public URL"></label><label>Additional exact excerpt<textarea name="excerpt" minlength="10" maxlength="1200" required placeholder="Include specific evidence for the same claim and scope. It will be public."></textarea></label><button class="button secondary" ${disabled}>Commit new round from round ${r.number} →</button></form>`}</section>`:''}`;
 $('#detail').querySelectorAll('[data-round]').forEach(b=>b.onclick=()=>{roundNumber=Number(b.dataset.round);renderDetail();});
 $('#resolve')?.addEventListener('click',()=>write('resolve',[c.id,r.number]));
 $('#challenge-form')?.addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.target);const ref=String(f.get('reference')).trim(),text=String(f.get('excerpt')).trim();if(r.sources.some(s=>s.reference===ref||s.excerpt===text)){message('This reference or excerpt is already in the selected snapshot. Add genuinely different evidence.',true);return;}write('propose_round',[c.id,r.number,JSON.stringify([{reference:ref,excerpt:text}])]);});
 $('#share').onclick=async()=>{const url=new URL(location.href);url.searchParams.set('review',c.id);url.searchParams.set('round',r.number);try{await navigator.clipboard.writeText(url.href);message('Public link copied. It opens this review and round without a wallet.');}catch{message('Share this public link: '+url.href);}};
 $('#export').onclick=()=>{const data={application:'CiteTrace',chainId:4221,contract:CONTRACT,readAt:new Date().toISOString(),review:c};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='citetrace-review-'+c.id+'.json';a.click();URL.revokeObjectURL(url);};
}
$('#source').href='https://github.com/laobinghao777/citetrace-genlayer';$('#explorer').href='https://scan.bradbury.genlayer.com/address/'+CONTRACT;
$('#new').onclick=()=>$('#create-dialog').showModal();$('#close-dialog').onclick=()=>$('#create-dialog').close();
$('#create').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);write('create_review',[String(f.get('title')).trim(),String(f.get('claim')).trim(),JSON.stringify([{reference:String(f.get('reference')).trim(),excerpt:String(f.get('excerpt')).trim()}])]);};
$('#connect').onclick=()=>connect().catch(e=>message(e.message,true));$('#refresh').onclick=load;$('#resume').onclick=waitFinal;
$('#recover-form').onsubmit=e=>{e.preventDefault();const hash=$('#recover-hash').value.trim();if(!/^0x[0-9a-fA-F]{64}$/.test(hash))return;savePending({...pending,hash});waitFinal();};
window.ethereum?.on?.('accountsChanged',()=>{account=null;client=makeClient();$('#connect').textContent='Reconnect wallet';renderDetail();});
try{pending=JSON.parse(localStorage.getItem(storageKey)||'null');}catch{message('Stored transaction record is unreadable. Check the explorer before requesting another write.',true);pending={hash:null};}
renderPending();await load();

