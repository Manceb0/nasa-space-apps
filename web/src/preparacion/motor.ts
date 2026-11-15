/** Motor puro: tiempo, cobertura y procedencia antes de interpretar señales. */
export interface Sample { time: string; mm: number | null }
export interface DeficitMetric { days: number; total_mm: number | null; percentile: number | null; reference_n: number; start: string; end: string; reference_totals_mm: number[] }
export interface EvidenceRecord {
  id: string; source_id: string; kind: "forecast" | "reanalysis" | "observation";
  site_id: string; requested: [number, number]; returned: [number, number];
  valid_start: string; valid_end: string; issued_at: string | null;
  first_seen_at: string; retrieved_at: string; availability_basis: string;
  quality: "provider" | "unverified" | "synthetic"; delivery?: string; provenance: string;
  model?: string; sha256?: string; hourly?: Sample[]; metrics?: DeficitMetric[]; precipitation_mm?: number;
  spatial_scope?: string;
  resolution?: string;
}
export interface Site { id: string; name: string; lat: number; lon: number; province: string; evidence: EvidenceRecord[]; errors: string[]; trends: Record<string, Record<string, unknown> | null> }
export interface Package {
  version: number; generated_at: string; sites: Site[];
  graph: { nodes: string[]; edges: string[][] };
  measurement_priority: Record<string, string>[];
  yuna_backtest: { resumen: { regla: string; h: number; fa: number }[]; eventos: Record<string, unknown>[] };
}
export interface Accumulation { start: string; end: string; mm: number }
export interface InvestigationCase {
  site_id: string; decision_at: string; excluded: { id: string; source: string; reason: string }[];
  rain: { state: "watch" | "below_rule" | "insufficient"; agreement: string;
    window: { start: string; end: string } | null;
    models: { source: string; record: EvidenceRecord; max24: Accumulation | null; max48: Accumulation | null; same_window_mm: number | null }[] };
  drought: { state: "deficit" | "not_below_p20" | "insufficient"; metrics: DeficitMetric[]; record: EvidenceRecord | null };
  local: EvidenceRecord[]; supporting: string[]; contradictions: string[]; missing: string[];
  tasks: { id: string; reason: string }[];
  rules: { id: string; result: string }[];
}
const HOUR = 3600000;
const timestamp = (s: string) => Date.parse(s);
const validMM = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0;

export function accumulations(samples: Sample[], hours: number, decision: number): Accumulation[] {
  const rows = [...samples].sort((a,b) => timestamp(a.time)-timestamp(b.time));
  const out: Accumulation[] = [];
  for (let i=hours-1;i<rows.length;i++) {
    const part = rows.slice(i-hours+1,i+1), end=timestamp(rows[i].time), start=end-hours*HOUR;
    if (start<decision || part.some((r,k) => !validMM(r.mm) || !Number.isFinite(timestamp(r.time)) || (k>0 && timestamp(r.time)-timestamp(part[k-1].time)!==HOUR))) continue;
    out.push({start:new Date(start).toISOString(),end:new Date(end).toISOString(),mm:part.reduce((s,r)=>s+r.mm!,0)});
  }
  return out;
}

export function exclusion(r: EvidenceRecord, decision: number): string | null {
  if (!Number.isFinite(decision)) return "invalid_decision";
  const captured=timestamp(r.first_seen_at), retrieved=timestamp(r.retrieved_at), end=timestamp(r.valid_end), start=timestamp(r.valid_start);
  if (![captured,retrieved,start,end].every(Number.isFinite) || start>end || !r.returned.every(Number.isFinite)) return "invalid_metadata";
  if (captured>decision) return "not_yet_captured";
  if (r.issued_at && !Number.isFinite(timestamp(r.issued_at))) return "invalid_metadata";
  if (r.issued_at && timestamp(r.issued_at)>decision) return "future_issue";
  if (r.kind!=="forecast" && end>decision) return "future_observation";
  if (r.kind==="forecast" && (decision-retrieved>12*HOUR || end<=decision)) return "expired_forecast";
  if (r.kind==="reanalysis" && decision-end>8*24*HOUR) return "old_reanalysis";
  return null;
}

export function investigate(site: Site, at: string, disabled: Set<string> = new Set(), local: EvidenceRecord[] = []): InvestigationCase {
  const decision=timestamp(at), excluded: InvestigationCase["excluded"]=[], usable: EvidenceRecord[]=[];
  for (const r of [...site.evidence,...local.filter(x=>x.site_id===site.id)]) {
    const reason=disabled.has(r.source_id)?"removed_by_user":exclusion(r,decision);
    if (reason) excluded.push({id:r.id,source:r.source_id,reason}); else usable.push(r);
  }
  const latest=new Map<string,EvidenceRecord>();
  for(const r of usable.filter(x=>x.kind!=="observation")) {
    const previous=latest.get(r.source_id);
    if(!previous||timestamp(r.first_seen_at)>timestamp(previous.first_seen_at)) latest.set(r.source_id,r);
  }
  const modelRows=[...latest.values()].filter(r=>r.kind==="forecast").map(r=>({r,w24:accumulations(r.hourly??[],24,decision),w48:accumulations(r.hourly??[],48,decision)}));
  // Comparar ambos modelos EN LA MISMA ventana, conservando su celda representativa.
  const ends=[...new Set(modelRows.flatMap(m=>m.w48.map(w=>w.end)))];
  const ranked=ends.map(end=>{
    const values=modelRows.map(m=>m.w48.find(w=>w.end===end)?.mm??null);
    return {end,values,support:values.filter(v=>v!==null&&v>100).length,peak:Math.max(...values.filter((v):v is number=>v!==null))};
  }).sort((a,b)=>b.support-a.support||b.peak-a.peak||timestamp(a.end)-timestamp(b.end));
  const chosen=ranked[0];
  const max=(a:Accumulation[])=>a.length?[...a].sort((x,y)=>y.mm-x.mm)[0]:null;
  const models=modelRows.map((m,i)=>({source:m.r.source_id,record:m.r,max24:max(m.w24),max48:max(m.w48),same_window_mm:chosen?.values[i]??null}));
  const covered=models.filter(m=>m.max48!==null).length;
  const watch=models.some(m=>(m.max48?.mm??0)>100);
  const era=latest.get("ERA5")??null;
  const metrics=(era?.metrics??[]).filter(m=>m.reference_n>=20&&m.reference_totals_mm.length===m.reference_n&&m.reference_totals_mm.every(validMM)&&validMM(m.total_mm)&&m.percentile!==null&&Number.isFinite(m.percentile)&&m.percentile>=0&&m.percentile<=100);
  const localRows=usable.filter(r=>r.source_id==="LOCAL");
  const supporting:string[]=[],contradictions:string[]=[],missing:string[]=[];
  const agreement=chosen?.support===2?"two_partially_dependent":watch?"one_or_disagree":covered?"below_exploratory_rule":"no_complete_window";
  if (chosen?.support===2) supporting.push("same_48h_two_models_partial_dependence");
  if (watch&&chosen?.support!==2) contradictions.push("watch_not_jointly_confirmed");
  for(const source of ["ECMWF","GFS"]) if(!models.some(m=>m.source===source&&m.max48)) missing.push(source);
  if (!metrics.length) missing.push("ERA5_reference");
  const actualLocal=localRows.filter(r=>r.quality!=="synthetic");
  if (!actualLocal.length) missing.push("local_measurement");
  else supporting.push("local_report_available_unverified");
  for(const source of ["IMERG","CHIRPS"]) if(usable.some(r=>r.source_id===source)) supporting.push(`historical_context_${source}`);
  const tasks:InvestigationCase["tasks"]=[{id:"official_bulletin",reason:"decision_needs_official_context"}];
  if(watch) tasks.push({id:"rain_interval",reason:"forecast_crosses_exploratory_rule"});
  if (contradictions.length) tasks.push({id:"resolve_models",reason:"model_disagreement"});
  if (metrics.some(m=>m.percentile!<=20)) tasks.push({id:"water_availability",reason:"precipitation_deficit_not_impact"});
  tasks.push({id:actualLocal.length?"verify_local_provenance":"obtain_local_measurement",reason:actualLocal.length?"unverified_report":"missing_independent_measurement"});
  if (missing.length) tasks.push({id:"coverage",reason:missing.join(", ")});
  return {site_id:site.id,decision_at:at,excluded,
    rain:{state:!covered?"insufficient":watch?"watch":"below_rule",agreement,models,
      window:chosen?{start:new Date(timestamp(chosen.end)-48*HOUR).toISOString(),end:chosen.end}:null},
    drought:{state:!metrics.length?"insufficient":metrics.some(m=>m.percentile!<=20)?"deficit":"not_below_p20",metrics,record:era},
    local:localRows,supporting,contradictions,missing,tasks,
    rules:[{id:"F1",result:"forecast_48h_gt_100_mm_exploratory"},{id:"D1",result:"same_product_same_cell_calendar_reference_2001_2024_min20_p20"},
      {id:"T1",result:"first_capture_le_decision_and_nonforecast_valid_end_le_decision"},{id:"P1",result:"shared_inputs_never_independent_votes"}]};
}

export interface LocalInput { site_id: string; start: string; end: string; mm: number; source: string; synthetic?: boolean; lat?: number; lon?: number }
export function localEvidence(input:LocalInput,site:Site,at:string):EvidenceRecord {
  const explicitZone=(value:string)=>typeof value==="string"&&/(Z|[+-]\d{2}:\d{2})$/.test(value);
  if(!explicitZone(input.start)||!explicitZone(input.end)||(input.synthetic!==undefined&&typeof input.synthetic!=="boolean"))throw new Error("explicit_timezone_required");
  const a=timestamp(input.start),b=timestamp(input.end),n=timestamp(at);
  if (input.site_id!==site.id||![a,b,n].every(Number.isFinite)||a>=b||b>n||!validMM(input.mm)||input.source.trim().length<3) throw new Error("invalid_local_measurement");
  const hasCoordinates=input.lat!==undefined||input.lon!==undefined;
  if(hasCoordinates&&(!Number.isFinite(input.lat)||!Number.isFinite(input.lon)||Math.abs(input.lat!)>90||Math.abs(input.lon!)>180))throw new Error("invalid_coordinates");
  return {id:`local:${site.id}:${at}`,source_id:"LOCAL",kind:"observation",site_id:site.id,
    requested:[site.lat,site.lon],returned:hasCoordinates?[input.lat!,input.lon!]:[site.lat,site.lon],
    spatial_scope:hasCoordinates?"instrument_coordinates_user_reported":"municipality_report_location_unspecified",
    valid_start:new Date(a).toISOString(),valid_end:new Date(b).toISOString(),
    issued_at:null,first_seen_at:at,retrieved_at:at,availability_basis:"user_entry",quality:input.synthetic?"synthetic":"unverified",
    provenance:input.source.trim(),precipitation_mm:input.mm};
}

export async function liveForecasts(site:Site,fetcher:typeof fetch=fetch):Promise<EvidenceRecord[]> {
  const models={ECMWF:"ecmwf_ifs025",GFS:"gfs_global"};
  const results=await Promise.allSettled(Object.entries(models).map(async([source,model])=>{
    const q=new URLSearchParams({latitude:String(site.lat),longitude:String(site.lon),hourly:"precipitation",models:model,forecast_days:"7",timezone:"GMT"});
    const url=`https://api.open-meteo.com/v1/forecast?${q}`;
    const response=await fetcher(url,{signal:AbortSignal.timeout(20000)});
    if(!response.ok) throw new Error(String(response.status));
    const data=await response.json();
    if(data.hourly_units?.precipitation!=="mm"||!Array.isArray(data.hourly?.time)||!Array.isArray(data.hourly?.precipitation)||data.hourly.time.length!==data.hourly.precipitation.length) throw new Error("invalid_forecast");
    const hourly:Sample[]=data.hourly.time.map((time:string,i:number)=>({time:time.endsWith("Z")?time:`${time}:00Z`,mm:data.hourly.precipitation[i]}));
    if(!hourly.length||hourly.some(x=>!Number.isFinite(timestamp(x.time))||(x.mm!==null&&!validMM(x.mm)))||![data.latitude,data.longitude].every(Number.isFinite)) throw new Error("invalid_forecast_values");
    const stamp=new Date().toISOString();
    return {id:`${site.id}:${source}:${stamp}`,source_id:source,kind:"forecast",site_id:site.id,
      requested:[site.lat,site.lon],returned:[data.latitude,data.longitude],issued_at:null,first_seen_at:stamp,retrieved_at:stamp,
      valid_start:hourly[0].time,valid_end:hourly[hourly.length-1].time,availability_basis:"first_capture_conservative",quality:"provider",delivery:"network",provenance:url,model,
      resolution:source==="ECMWF"?"IFS 0.25°; native 3/6-hourly, provider hourly interpolation":"GFS surface ~0.11°; hourly, native 3-hourly after 120h",hourly} as EvidenceRecord;
  }));
  return results.filter((r):r is PromiseFulfilledResult<EvidenceRecord>=>r.status==="fulfilled").map(r=>r.value);
}
