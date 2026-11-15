import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const text=fs.readFileSync(new URL('../src/preparacion/motor.ts',import.meta.url),'utf8');
const js=ts.transpileModule(text,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {investigate,accumulations,localEvidence,liveForecasts}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const at='2026-11-15T12:00:00Z';
const sample=(value=3)=>Array.from({length:72},(_,i)=>({time:new Date(Date.parse(at)+(i+1)*3600000).toISOString(),mm:value}));
const record=(source,value=3)=>({id:source,source_id:source,kind:'forecast',site_id:'test',requested:[19,-70],returned:[19,-70],
  valid_start:at,valid_end:'2026-11-18T12:00:00Z',issued_at:null,first_seen_at:at,retrieved_at:at,availability_basis:'first_capture',quality:'provider',provenance:'test fixture',hourly:sample(value)});
const site=(evidence)=>({id:'test',name:'Test',lat:19,lon:-70,province:'DO-06',evidence,errors:[],trends:{}});

test('suma en la misma serie; cero no equivale a ausente y huecos no rellenan',()=>{
  assert.equal(accumulations(sample(0),48,Date.parse(at))[0].mm,0);
  const missing=sample(0).slice(0,48);missing[10].mm=null;
  assert.equal(accumulations(missing,48,Date.parse(at)).length,0);
  const gap=sample(3).slice(0,49);gap.splice(24,1);
  assert.equal(accumulations(gap,48,Date.parse(at)).length,0);
  assert.equal(accumulations(sample(3),48,Date.parse(at))[0].mm,144);
});
test('retirar fuente cambia el respaldo; no crea votos independientes',()=>{
  const s=site([record('ECMWF'),record('GFS')]);
  assert.equal(investigate(s,at).rain.agreement,'two_partially_dependent');
  const c=investigate(s,at,new Set(['GFS']));
  assert.equal(c.rain.agreement,'one_or_disagree');assert.ok(c.missing.includes('GFS'));
});
test('dos modelos con picos en ventanas diferentes no confirman',()=>{
  const a=record('ECMWF',0),b=record('GFS',0);
  a.hourly=Array.from({length:168},(_,i)=>({time:new Date(Date.parse(at)+(i+1)*3600000).toISOString(),mm:i<24?6:0}));
  b.hourly=a.hourly.map((x,i)=>({...x,mm:i>=144?6:0}));
  a.valid_end=b.valid_end=a.hourly.at(-1).time;
  assert.equal(investigate(site([a,b]),at).rain.agreement,'one_or_disagree');
});
test('fuentes capturadas o emitidas después no entran; observaciones futuras tampoco',()=>{
  const a=record('ECMWF');a.first_seen_at='2026-11-15T12:01:00Z';
  assert.equal(investigate(site([a]),at).rain.state,'insufficient');
  a.first_seen_at=at;a.issued_at='2026-11-15T13:00:00Z';
  assert.equal(investigate(site([a]),at).excluded[0].reason,'future_issue');
  a.issued_at=null;a.kind='observation';a.source_id='LOCAL';
  assert.equal(investigate(site([a]),at).local.length,0);
});
test('pronóstico vencido deja información insuficiente; duplicados no cuentan votos',()=>{
  const a=record('ECMWF');a.retrieved_at='2026-11-14T00:00:00Z';
  assert.equal(investigate(site([a]),at).rain.state,'insufficient');
  const b=record('ECMWF');assert.equal(investigate(site([b,{...b,id:'duplicate'}]),at).rain.models.length,1);
});
test('déficit exige 20 ventanas completas; cero y percentil 0 son válidos',()=>{
  const r={...record('ERA5'),kind:'reanalysis',valid_start:'2026-08-12T00:00:00Z',valid_end:'2026-11-10T00:00:00Z',hourly:undefined,
    metrics:[{days:90,total_mm:0,percentile:0,reference_n:19,reference_totals_mm:Array(19).fill(5),start:'2026-08-12',end:'2026-11-09'}]};
  assert.equal(investigate(site([r]),at).drought.state,'insufficient');
  r.metrics[0].reference_n=20;r.metrics[0].reference_totals_mm.push(5);
  assert.equal(investigate(site([r]),at).drought.state,'deficit');
});
test('mediciones inválidas rechazadas y aporte sin verificar no confirma pronóstico',()=>{
  const s=site([record('ECMWF')]);
  const input={site_id:'test',start:'2026-11-14T00:00:00Z',end:'2026-11-15T00:00:00Z',mm:0,source:'Pluviómetro de prueba'};
  assert.throws(()=>localEvidence({...input,mm:-1},s,at));
  assert.throws(()=>localEvidence({...input,end:'2026-11-16T00:00:00Z'},s,at));
  assert.throws(()=>localEvidence({...input,start:input.end},s,at));
  assert.throws(()=>localEvidence({...input,start:'2026-11-14T00:00'},s,at));
  assert.throws(()=>localEvidence({...input,lat:91,lon:0},s,at));
  const r=localEvidence(input,s,at);assert.equal(r.quality,'unverified');
  const c=investigate(s,at,new Set(),[r]);assert.equal(c.rain.agreement,'one_or_disagree');
  assert.equal(c.local[0].precipitation_mm,0);assert.ok(c.tasks.some(t=>t.id==='verify_local_provenance'));
  assert.equal(localEvidence({...input,synthetic:true},s,at).quality,'synthetic');
  const synthetic=localEvidence({...input,synthetic:true},s,at);
  assert.ok(investigate(s,at,new Set(),[synthetic]).missing.includes('local_measurement'));
});
test('caída de proveedor y unidades inválidas no fabrican datos',async()=>{
  assert.deepEqual(await liveForecasts(site([]),async()=>{throw Error('offline')}),[]);
  const invalid=async()=>({ok:true,json:async()=>({hourly_units:{precipitation:'inch'},hourly:{time:[],precipitation:[]}})});
  assert.deepEqual(await liveForecasts(site([]),invalid),[]);
});
