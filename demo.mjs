import fs from 'node:fs';
import {execute,state,snapshot,safeError,ROOT} from './scripts/runtime.mjs';
try {
 if(!state.contract)throw Error('Deploy first.');
 if(state.transactions.some(x=>x.action==='create_review'))throw Error('Demo started already: reconcile original transactions, never resend.');
 const source={reference:'Synthetic schedule A (test fixture)',excerpt:'Workshop Orion opens at 09:00 on 20 November 2026.'};
 const counter={reference:'Synthetic correction B (test fixture)',excerpt:'Workshop Orion opens at 11:00 on 20 November 2026; the earlier 09:00 opening is cancelled.'};
 await execute('create_review',['Synthetic workshop schedule review','Workshop Orion opens at 09:00 on 20 November 2026.',JSON.stringify([source])]);
 await execute('resolve',['1',1]);
 const first=await snapshot();
 if(first.items[0]?.rounds[0]?.result?.verdict!=='support_only')throw Error('First result differs from expected fixture; inspect, do not resend.');
 fs.writeFileSync(ROOT+'/first-round.json',JSON.stringify(first,null,2));
 await execute('propose_round',['1',1,JSON.stringify([counter])]);
 await execute('resolve',['1',2]);
 const result=await snapshot();
 const r=result.items.find(x=>x.id==='1');
 if(r?.rounds[0]?.result?.verdict!=='support_only'||r?.rounds[1]?.result?.verdict!=='conflicted')throw Error('Expected preserved support round and conflicted counterevidence round not observed.');
 fs.writeFileSync(ROOT+'/demo-result.json',JSON.stringify(result,null,2));
 fs.writeFileSync(ROOT+'/deployment.json',JSON.stringify({network:'Bradbury Phase 2',chainId:4221,contract:state.contract,wallet:state.wallet,transactions:result.transactions.map(x=>({action:x.action,txId:x.txId,status:x.status,consensusResult:x.consensusResult,outcome:x.outcome,executionResult:x.executionResult,netCostGEN:x.netCostGEN})),netCostGEN:result.netCostGEN},null,2));
 console.log(JSON.stringify(result,null,2));
}catch(e){console.error(safeError(e));process.exitCode=1;}
