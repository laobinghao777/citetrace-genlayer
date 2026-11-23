// No key imports, signer creation, writes, deployment or transaction broadcasts.
import fs from 'node:fs';
import {createClient} from 'genlayer-js';
import {testnetBradbury} from 'genlayer-js/chains';
const CONTRACT='0x9D34993A82039478b496a2fAe403BA12DD6e14AA';
const CALLER='0xF10aB469555eb723d62A565217EE678A8C200526';
const id=process.argv[2]??'1';
if(!/^[1-9][0-9]{0,18}$/.test(id))throw Error('Invalid review ID');
const client=createClient({chain:testnetBradbury,endpoint:'https://rpc-bradbury.genlayer.com'});
try {
 const raw=await client.readContract({address:CONTRACT,functionName:'get_review',args:[id],account:{address:CALLER},transactionHashVariant:'latest-final'});
 const review=typeof raw==='string'?JSON.parse(raw):raw;
 const output=JSON.stringify(review,null,2)+'\n';
 if(process.argv[3])fs.writeFileSync(process.argv[3],output);else process.stdout.write(output);
}catch(e){console.error('Read failed: '+String(e.shortMessage??e.message).slice(0,250));process.exitCode=1;}
