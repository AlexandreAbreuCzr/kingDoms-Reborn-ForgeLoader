// Local persistent REA MCP session. Does not execute or modify the target.
import { Client } from '../.local/node_modules/@modelcontextprotocol/client/dist/index.mjs';
import { StdioClientTransport } from '../.local/node_modules/@modelcontextprotocol/client/dist/stdio.mjs';
import { mkdir, readFile, writeFile, appendFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const output=resolve('artifacts/native-rea',`run-${new Date().toISOString().replace(/[:.]/g,'-')}-${process.pid}`);
await mkdir(output,{recursive:true});
await writeFile(resolve('artifacts/native-rea/latest-run.json'),JSON.stringify({path:output,startedAt:new Date().toISOString()},null,2));
const transport=new StdioClientTransport({command:process.execPath,
 args:[resolve('.local/node_modules/rea-agents/scripts/rea.mjs'),'mcp'],
 env:{...process.env,GHIDRA_INSTALL_DIR:resolve('.local/ghidra/ghidra_12.1.4_PUBLIC'),
 JAVA_HOME:'C:\\Program Files\\Eclipse Adoptium\\jdk-21.0.11.10-hotspot',
 GHIDRA_HEADLESS_MAXMEM:'3G',REA_GHIDRA_STARTUP_TIMEOUT_MS:process.env.REA_GHIDRA_STARTUP_TIMEOUT_MS??'900000',
 REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS:'60',REA_GHIDRA_DISABLED_ANALYZERS:process.env.REA_GHIDRA_DISABLED_ANALYZERS??'WindowsResourceReference',
 REA_GHIDRA_SEED_FILE:resolve('artifacts/native-seeds.tsv'),REA_LOG_LEVEL:'info'},stderr:'pipe'});
const client=new Client({name:'kingdoms-native-investigation',version:'1'});
const log=async(value)=>{const line=JSON.stringify(value);console.log(line);await appendFile(resolve(output,'progress.jsonl'),line+'\n');};
const call=async(name,args,file)=>{
 await log({at:new Date().toISOString(),operation:name,args});
 const result=await client.callTool({name,arguments:args},{timeout:1020000});
 await writeFile(resolve(output,file),JSON.stringify(result,null,2));
 await log({at:new Date().toISOString(),saved:file,isError:result.isError??false});
 return result;
};
try{
 await client.connect(transport);
 transport.stderr?.on('data',data=>process.stderr.write(data));
 const catalog=await client.listTools();
 const selected=catalog.tools.filter(t=>['open_binary','analyze_function','close_binary','binary_session','export_evidence_bundle'].includes(t.name));
 await writeFile(resolve(output,'tool-schemas.json'),JSON.stringify(selected,null,2));
 if(process.argv.includes('--catalog')){console.log(JSON.stringify(selected,null,2));}
 else{
  const plan=JSON.parse(await readFile(resolve('artifacts/native-plan.json'),'utf8'));
  for(const item of plan){
   const result=await call(item.name,item.arguments,item.file);
   if(result.isError)break;
  }
 }
}finally{
 try{await call('close_binary',{},'close.json');}catch(e){console.error(String(e));}
 await client.close();await transport.close();
}
