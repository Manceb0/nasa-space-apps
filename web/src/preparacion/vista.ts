import { getLang } from "../i18n";
import { esc, LL, num, sgn } from "../tendencias/datos";
import { accumulations, investigate, liveForecasts, localEvidence, type EvidenceRecord, type InvestigationCase, type Package, type Site } from "./motor";
import "./vista.css";
import { hurricanes } from "./huracanes";
let hx:{destroy:()=>void}|null=null,hxHost:HTMLElement|null=null;

const SOURCES=["ECMWF","GFS","ERA5","IMERG","CHIRPS","LOCAL"];
const STORE="stellar-preparation-v1";
let data:Package|null=null,siteId="villa-riva",disabled=new Set<string>(),locals:EvidenceRecord[]=[],history:EvidenceRecord[]=[];
let decision="",message="",loading=false,alive=0,deepOpen=false;
const isoNow=()=>new Date().toISOString();
const dateText=(s:string)=>new Date(s).toLocaleString(getLang()==="es"?"es-DO":"en-US",{timeZone:"America/Santo_Domingo",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
const decimal=(n:number|null|undefined,d=1)=>n===null||n===undefined?"—":num(n,d);
const status=(code:string)=>({watch:LL("Lluvia prevista para revisar","Forecast rain to review"),below_rule:LL("Sin superar la regla exploratoria","Below the exploratory rule"),insufficient:LL("Información insuficiente","Insufficient information"),deficit:LL("Déficit de lluvia para seguimiento","Rainfall deficit to monitor"),not_below_p20:LL("Sin déficit bajo P20","Not below P20")}[code]??code);
const why=(reason:string)=>({not_yet_captured:LL("Todavía no se había capturado","Not captured yet"),removed_by_user:LL("Retirada del análisis","Removed from analysis"),expired_forecast:LL("Pronóstico vencido","Expired forecast"),old_reanalysis:LL("Reanálisis desactualizado","Outdated reanalysis"),future_observation:LL("Observación posterior a la decisión","Observation after decision"),future_issue:LL("Emisión futura","Future issue"),invalid_metadata:LL("Metadatos inválidos","Invalid metadata"),invalid_decision:LL("Hora de decisión inválida","Invalid decision time")}[reason]??reason);
const task=(id:string)=>({official_bulletin:LL("Contrastar con el boletín oficial de COE e INDOMET","Check official COE and INDOMET bulletins"),rain_interval:LL("Verificar la ventana de lluvia y los reportes locales","Verify the rainfall window and local reports"),resolve_models:LL("Investigar el desacuerdo entre pronósticos","Investigate forecast disagreement"),water_availability:LL("Consultar registros locales de disponibilidad de agua e impactos","Check local records of water availability and impacts"),obtain_local_measurement:LL("Solicitar una medición local con fecha y procedencia","Request a dated local measurement with provenance"),verify_local_provenance:LL("Verificar la procedencia de la aportación local","Verify the local report's provenance"),coverage:LL("Revisar las fuentes faltantes o excluidas","Review missing or excluded sources")}[id]??id);

function restore(){
  try{const p=JSON.parse(localStorage.getItem(STORE)??"{}");history=Array.isArray(p.history)?p.history:[];locals=Array.isArray(p.locals)?p.locals:[];}catch{history=[];locals=[];}
}
function save(){try{localStorage.setItem(STORE,JSON.stringify({history,locals}));}catch{message=LL("No se pudo guardar en este navegador. Descarga el expediente.","Browser storage unavailable. Download the case.");}}
function withHistory(site:Site):Site{return {...site,evidence:[...site.evidence,...history.filter(r=>r.site_id===site.id)]};}
export function destroyPreparation(){alive++;hx?.destroy();hx=null;hxHost=null;}
export async function viewPreparation(view:HTMLElement,embedded=false){
  const token=++alive;
  if(!embedded)document.body.classList.remove("wx-on");
  view.innerHTML=`<div class="prep"><p>${esc(LL("Conectando las evidencias…","Connecting evidence…"))}</p></div>`;
  restore();decision=isoNow();
  if(!data){
    try{
      const r=await fetch("./data/preparacion.json",{cache:"no-cache"});if(!r.ok)throw Error(String(r.status));
      data=await r.json();
      try{localStorage.setItem(`${STORE}-package`,JSON.stringify(data));}catch{/* memoria sigue disponible */}
    }catch{
      try{data=JSON.parse(localStorage.getItem(`${STORE}-package`)??"null");}catch{data=null;}
      message=LL("No se pudo descargar. Se muestra la última copia local, con su fecha.","Download failed. Showing the dated local copy.");
    }
  }
  if(token!==alive)return;
  if(!data){view.innerHTML=`<div class="prep"><h1>${esc(LL("Preparar mi territorio","Prepare my territory"))}</h1><p>${esc(LL("No hay paquete disponible. Abre el respaldo local o vuelve a intentar con conexión.","No package available. Open the local backup or retry online."))}</p><button id="prep-retry">${esc(LL("Reintentar","Retry"))}</button></div>`;view.querySelector("button")!.addEventListener("click",()=>viewPreparation(view));return;}
  render(view);
}

function priorityMap(site:Site){
  const rows=data!.measurement_priority.filter(r=>Number.isFinite(Number(r.indice_prioridad)));
  const x=(lon:number)=>(lon+72.1)/3.9*600+20,y=(lat:number)=>(20.1-lat)/2.8*290+15;
  return `<svg class="prep-map" viewBox="0 0 640 335" role="img" aria-label="${esc(LL("Prioridad de medición en celdas de República Dominicana","Measurement priority across Dominican Republic cells"))}">
    ${rows.map(r=>`<rect x="${x(Number(r.lon))-4}" y="${y(Number(r.lat))-4}" width="8" height="8" fill="${Number(r.indice_prioridad)>.75?"#f2cf83":Number(r.indice_prioridad)>.5?"#827147":"#36434a"}"><title>${esc(`${r.provincia} · ${LL("prioridad de medición","measurement priority")} ${decimal(Number(r.indice_prioridad),2)} · GHCN ${decimal(Number(r.dist_estacion_ghcn_activa_km))} km`)}</title></rect>`).join("")}
    ${data!.sites.map(s=>`<circle cx="${x(s.lon)}" cy="${y(s.lat)}" r="${s.id===site.id?8:5}" fill="${s.id===site.id?"#fff":"#8fd3ff"}" stroke="#111" stroke-width="2"><title>${esc(s.name)}</title></circle>`).join("")}
    <text x="20" y="326" fill="#bbc4cf" font-size="13">${esc(LL("Ámbar: mayor prioridad de medición · círculos: pilotos","Amber: higher measurement priority · circles: pilot sites"))}</text></svg>`;
}


const HOUR=3600000;
// Pronóstico: lluvia de 48 h acumulada a lo largo de 7 días, los dos modelos en la misma escala y la regla de 100 mm
function forecastChart(c:InvestigationCase,at:number){
  const W=300,H=74,L=4,R=46,T=8,B=16,span=7*24*HOUR;
  const lines=c.rain.models.map(m=>({src:m.source,pts:accumulations(m.record.hourly??[],48,at)}));
  const top=Math.max(120,...lines.flatMap(l=>l.pts.map(p=>p.mm)));
  const x=(t:number)=>L+(t-at)/span*(W-L-R),y=(v:number)=>T+(1-v/top)*(H-T-B);
  const col:Record<string,string>={ECMWF:"#ffffff",GFS:"#64d2ff"};
  const days=[...Array(8)].map((_,i)=>at+i*24*HOUR);
  const paths=lines.filter(l=>l.pts.length).map(l=>{
    const d=l.pts.map((p,i)=>`${i?"L":"M"}${x(Date.parse(p.end)).toFixed(1)},${y(p.mm).toFixed(1)}`).join("");
    const mx=l.pts.reduce((a,p)=>p.mm>a.mm?p:a,l.pts[0]);
    return `<path d="${d}" fill="none" stroke="${col[l.src]??"#aaa"}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${x(Date.parse(mx.end)).toFixed(1)}" cy="${y(mx.mm).toFixed(1)}" r="3.5" fill="${col[l.src]??"#aaa"}"><title>${esc(`${l.src}: ${num(mx.mm,0)} mm`)}</title></circle>`;
  }).join("");
  const key=lines.filter(l=>l.pts.length).map(l=>`<i style="--k:${col[l.src]??"#aaa"}"></i>${l.src} ${num(Math.max(...l.pts.map(p=>p.mm)),0)} mm`).join(" ");
  return `<svg class="pb-fc" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL("Lluvia prevista en 48 h durante los próximos 7 días, ECMWF y GFS, frente a la regla de 100 mm","Forecast 48-h rain over the next 7 days, ECMWF and GFS, against the 100 mm rule"))}">
    ${days.map(t=>`<line x1="${x(t).toFixed(1)}" x2="${x(t).toFixed(1)}" y1="${T}" y2="${H-B}" stroke="#2a2d31" stroke-width="1"/>`).join("")}
    <line x1="${L}" x2="${W-R}" y1="${y(100).toFixed(1)}" y2="${y(100).toFixed(1)}" stroke="#ff9f0a" stroke-width="1.5" stroke-dasharray="4 4" stroke-linecap="round"/>
    <text x="${W-R+6}" y="${(y(100)+4).toFixed(1)}" fill="#ff9f0a" font-size="11" font-weight="600">100 mm</text>
    ${paths||`<text x="${L}" y="${H/2}" fill="#949494" font-size="12">${esc(LL("Sin pronóstico vigente","No current forecast"))}</text>`}
    ${days.slice(0,7).map((t)=>`<text x="${(x(t)+ (x(t+24*HOUR)-x(t))/2).toFixed(1)}" y="${H-4}" fill="#949494" font-size="11" text-anchor="middle">${esc(new Date(t).toLocaleDateString(getLang()==="es"?"es-DO":"en-US",{timeZone:"America/Santo_Domingo",weekday:"narrow"}))}</text>`).join("")}
  </svg>${key?`<small class="pb-key">${LL("Máximo","Peak")}: ${key}</small>`:""}`;
}
// Sequía: los últimos 90 días contra el mismo tramo de cada año 2001–2024, un punto por año
function dryStrip(c:InvestigationCase){
  const m=c.drought.metrics.find(k=>k.days===90)??c.drought.metrics[c.drought.metrics.length-1];
  if(!m||m.total_mm===null||!m.reference_totals_mm?.length)return {svg:`<p class="pb-none">${esc(LL("Sin referencia vigente","No current reference"))}</p>`,drier:null as number|null,n:0,m};
  const W=300,H=74,L=10,R=10,ref=m.reference_totals_mm,lo=Math.min(m.total_mm,...ref),hi=Math.max(m.total_mm,...ref);
  const x=(v:number)=>L+(v-lo)/(hi-lo||1)*(W-L-R),cy=40,dry=m.percentile!==null&&m.percentile<=20,hue=dry?"#ff9f0a":"#ffffff";
  const drier=ref.filter(v=>v<m.total_mm!).length;
  const svg=`<svg class="pb-dry" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL(`Lluvia de los últimos ${m.days} días: ${num(m.total_mm,0)} mm; ${drier} de ${ref.length} años fueron más secos`,`Rain over the last ${m.days} days: ${num(m.total_mm,0)} mm; ${drier} of ${ref.length} years were drier`))}">
    <line x1="${L}" x2="${W-R}" y1="${cy}" y2="${cy}" stroke="#2a2d31" stroke-width="2" stroke-linecap="round"/>
    ${ref.map(v=>`<circle cx="${x(v).toFixed(1)}" cy="${cy}" r="4" fill="#5b6066"><title>${num(v,0)} mm</title></circle>`).join("")}
    <circle cx="${x(m.total_mm).toFixed(1)}" cy="${cy}" r="9" fill="none" stroke="${hue}" stroke-width="2.5"/>
    <circle cx="${x(m.total_mm).toFixed(1)}" cy="${cy}" r="4.5" fill="${hue}"/>
    <text x="${L}" y="${H-6}" fill="#949494" font-size="11">${esc(LL("más seco","drier"))}</text>
    <text x="${W-R}" y="${H-6}" fill="#949494" font-size="11" text-anchor="end">${esc(LL("más lluvioso","wetter"))}</text>
    <text x="${Math.min(Math.max(x(m.total_mm),40),W-40).toFixed(1)}" y="${cy-16}" fill="${hue}" font-size="12" font-weight="600" text-anchor="middle">${esc(`${num(m.total_mm,0)} mm`)}</text>
  </svg>`;
  return {svg,drier,n:ref.length,m};
}
function board(){
  const at=Date.parse(decision);
  const rows=data!.sites.map(s=>{const c=investigate(withHistory(s),decision,disabled,locals.filter(r=>r.site_id===s.id));
    const ds=dryStrip(c),rain=c.rain.state==="watch",dry=c.drought.state==="deficit";
    return {s,c,ds,rain,dry,score:(rain?2:0)+(dry?1:0)+(ds.m?.percentile!=null?(100-ds.m.percentile)/1000:0)};}).sort((a,b)=>b.score-a.score);
  const word=(r:typeof rows[number])=>r.rain&&r.dry?LL("Vigilar lluvia y sequía","Watch rain and drought"):r.rain?LL("Vigilar lluvia fuerte","Watch heavy rain"):r.dry?LL("Vigilar sequía","Watch drought"):LL("Sin señal que vigilar","Nothing to watch");
  const hue=(r:typeof rows[number])=>r.rain?"#64d2ff":r.dry?"#ff9f0a":"#949494";
  const top=rows[0];
  const lead=top.dry&&top.ds.drier!==null?LL(`${top.s.name}: solo ${top.ds.drier} de ${top.ds.n} años ${top.ds.drier===1?"tuvo":"tuvieron"} menos lluvia en estos ${top.ds.m!.days} días`,`${top.s.name}: only ${top.ds.drier} of ${top.ds.n} years had less rain in these ${top.ds.m!.days} days`)
    :top.rain?LL(`${top.s.name}: lluvia prevista por encima de 100 mm en 48 h`,`${top.s.name}: forecast rain above 100 mm in 48 h`):LL("Ningún municipio piloto pasa hoy las reglas de vigilancia","No pilot municipality crosses the watch rules today");
  const first=(c:InvestigationCase)=>c.tasks[0]?task(c.tasks[0].id):"";
  return `<header class="pb-head">
      <h1>${esc(LL("¿Qué municipio vigilar hoy?","Which municipality to watch today?"))}</h1>
      <p class="pb-lead">${esc(lead)}</p>
    </header>
    <div class="pb-cols" aria-hidden="true"><span></span><span>${esc(LL("Lluvia prevista · 48 h, próximos 7 días","Forecast rain · 48 h, next 7 days"))}</span><span>${esc(LL("Lluvia de 90 días frente a 2001–2024","90-day rain against 2001–2024"))}</span></div>
    <ol class="pb-list">${rows.map((r,i)=>`<li><button class="pb-row ${r.s.id===siteId&&deepOpen?"on":""}" data-pick="${r.s.id}" style="--c:${hue(r)};--i:${i}" aria-expanded="${r.s.id===siteId&&deepOpen}">
        <span class="pb-name"><b>${esc(r.s.name)}</b><em><i class="${r.rain||r.dry?"":"no"}"></i>${esc(word(r))}</em>${(r.rain||r.dry)&&first(r.c)?`<small>${esc(first(r.c))}</small>`:""}</span>
        <span class="pb-chart">${forecastChart(r.c,at)}</span>
        <span class="pb-chart">${r.ds.svg}${r.ds.drier!==null?`<small>${esc(LL(`${r.ds.drier} de ${r.ds.n} años ${r.ds.drier===1?"fue más seco":"fueron más secos"}`,`${r.ds.drier} of ${r.ds.n} ${r.ds.drier===1?"year was":"years were"} drier`))}</small>`:""}</span>
      </button></li>`).join("")}</ol>
    <p class="pb-foot">${esc(LL(`Pronóstico capturado ${dateText(data!.generated_at)} · puntos representativos, no todo el municipio · regla de 100 mm exploratoria`,`Forecast captured ${dateText(data!.generated_at)} · representative points, not the whole municipality · 100 mm rule is exploratory`))}</p>
    <section class="pb-flood" aria-labelledby="pb-flood-h">
      <h2 id="pb-flood-h">${esc(LL("Dos tipos de inundación, dos respuestas","Two kinds of flood, two responses"))}</h2>
      <p class="pb-flood-s">${esc(LL("Río Yuna: 14 inundaciones entre 2001 y 2024.","Yuna river: 14 floods between 2001 and 2024."))}</p>
      <div class="pb-hx" id="hx-slot"></div>
      <div class="pb-flood-g">
        <div class="pb-cy">
          <h3><b>${esc(LL("6 de 14","6 of 14"))}</b> ${esc(LL("llegaron con un ciclón","came with a cyclone"))}</h3>
          <p class="pb-step"><strong>${esc(LL("Pre-alerta con el aviso oficial del NHC","Pre-alert from the official NHC advisory"))}</strong> ${esc(LL("para lo barato: albergues, nivel de Hatillo, avisar a Villa Riva.","for cheap actions: shelters, Hatillo level, notify Villa Riva."))}</p>
          ${leadChart()}
          <p class="pb-note">${esc(LL("Coste: en 24 años, 33 tormentas se pronosticaron a menos de 200 km y solo 5 trajeron una inundación catalogada. Sirve para preparar, no para evacuar.","Cost: in 24 years, 33 storms were forecast within 200 km and only 5 brought a catalogued flood. It serves to prepare, not to evacuate."))}</p>
          <p class="pb-step"><strong>${esc(LL("Alerta confirmada cuando dos satélites coinciden","Confirmed alert when two satellites agree"))}</strong> ${esc(LL("para lo caro: movilizar.","for costly actions: mobilise."))}</p>
          <div class="pb-nums">
            <p><b>39</b><span>${esc(LL("falsas alarmas con un satélite","false alarms with one satellite"))}</span></p>
            <svg viewBox="0 0 40 16" aria-hidden="true"><path d="M2 8h32m-6-5 6 5-6 5" fill="none" stroke="#949494" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <p><b class="ok">16</b><span>${esc(LL("si un segundo lo confirma","if a second one confirms"))}</span></p>
          </div>
          <p class="pb-note">${esc(LL("IMERG confirmado por CHIRPS en la misma celda, 2016–2024: detecta 6 de 8 inundaciones en vez de 7 de 8.","IMERG confirmed by CHIRPS in the same cell, 2016–2024: detects 6 of 8 floods instead of 7 of 8."))}</p>
        </div>
        <div class="pb-nocy">
          <h3><b>${esc(LL("8 de 14","8 of 14"))}</b> ${esc(LL("llegaron sin ciclón","came without a cyclone"))}</h3>
          <p>${esc(LL("Vaguadas y frentes. Ninguna señal llegó antes del inicio, y los dos satélites coinciden menos en dónde cae la lluvia fuerte.","Troughs and fronts. No signal arrived before onset, and the two satellites agree less on where heavy rain falls."))}</p>
          <div class="pb-ets"><p><b>0,24</b><span>${esc(LL("acuerdo con ciclón cerca","agreement with a cyclone nearby"))}</span></p><p><b class="lo">0,10</b><span>${esc(LL("acuerdo sin ciclón","agreement without one"))}</span></p></div>
          <p class="pb-answer">${esc(LL("Aquí la respuesta es medir donde falta.","Here the answer is to measure where data is missing."))}</p>
          <div class="pb-pmap">${priorityMap(data!.sites.find(x=>x.id==="villa-riva")??data!.sites[0])}</div><p class="pb-note">${esc(LL("Ámbar: donde más falta medir (los productos discrepan y no hay estación cerca). Círculos: los cuatro pilotos.","Amber: where measuring is most needed (products disagree, no station nearby). Circles: the four pilots."))}</p>
          <button class="pb-go" data-goto-map>${esc(LL("Ver dónde falta un pluviómetro","See where a rain gauge is missing"))}</button>
        </div>
      </div>
      <p class="pb-limit">${esc(LL("n = 14 · catálogo armado con prensa · acuerdo medido con ETS · prototipo de apoyo, no una orden de evacuación ni una validación operativa.","n = 14 · catalogue built from press reports · agreement measured as ETS · a support prototype, not an evacuation order or operational validation."))}</p>
    </section>`;
}
// Antelación en las inundaciones de ciclón: desde el primer aviso del NHC que pone el centro a menos de 200 km del Yuna
// (a-deck OFCL tal como se emitió) hasta el inicio catalogado, y el día en que IMERG superó 100 mm/48 h.
// Fuente: results/tropical/ciclones/inundaciones_y_ciclones.csv y results/tropical/alerta_causal/momento_por_evento.csv
const CY:{n:string;y:number;lead:number|null;sat:number}[]=[
  // horas desde la publicación del boletín (hora base del a-deck menos unas 3 h de publicación)
  {n:"María",y:2017,lead:103,sat:0},{n:"Fiona",y:2022,lead:85,sat:1},{n:"Isaac",y:2012,lead:37,sat:-1},
  {n:"Isaías",y:2020,lead:37,sat:0},{n:"Olga",y:2007,lead:1,sat:0},{n:"Noel",y:2007,lead:null,sat:1}];
function leadChart(){
  const W=560,L=96,R=12,T=30,rh=30,H=T+CY.length*rh+26,x0=-120,x1=48;
  const x=(h:number)=>L+(h-x0)/(x1-x0)*(W-L-R);
  const ticks=[-120,-96,-72,-48,-24,0,24,48];
  const rows=CY.map((c,i)=>{const y=T+i*rh+rh/2;
    const nhc=c.lead===null?`<text x="${x(-114)}" y="${y+4}" fill="#949494" font-size="12">${esc(LL("el NHC nunca lo pronosticó a menos de 200 km","NHC never forecast it within 200 km"))}</text>`
      :`<rect x="${x(-c.lead).toFixed(1)}" y="${y-7}" width="${Math.max(4,x(0)-x(-c.lead)).toFixed(1)}" height="14" rx="7" fill="#64d2ff"/><text x="${(x(-c.lead)-8).toFixed(1)}" y="${y+4}" fill="#64d2ff" font-size="12" font-weight="600" text-anchor="end">${c.lead} h</text>`;
    const sat=`<rect x="${(x(c.sat*24)+1).toFixed(1)}" y="${y-7}" width="${(x(24)-x(0)-2).toFixed(1)}" height="14" rx="4" fill="#ffffff" fill-opacity=".85"/>`;
    return `<text x="${L-12}" y="${y+4}" fill="#fff" font-size="13" font-weight="600" text-anchor="end">${esc(c.n)} <tspan fill="#949494" font-weight="400">${c.y}</tspan></text>${c.lead!==null&&c.lead>=20?"":""}${nhc}${sat}`;}).join("");
  return `<svg class="pb-lead-c" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL("Horas de antelación del aviso del NHC y día de la señal del satélite en las seis inundaciones de ciclón del Yuna","Lead time of the NHC advisory and day of the satellite signal in the six cyclone floods of the Yuna"))}">
    <text x="${L}" y="14" fill="#64d2ff" font-size="12" font-weight="600">${esc(LL("Boletín del NHC publicado","NHC advisory published"))}</text>
    <text x="${L+110}" y="14" fill="#fff" font-size="12" font-weight="600">${esc(LL("Día de la señal del satélite (IMERG)","Satellite signal day (IMERG)"))}</text>
    ${ticks.map(t=>`<line x1="${x(t)}" x2="${x(t)}" y1="${T-4}" y2="${H-22}" stroke="${t===0?"#ff9f0a":"#23262a"}" stroke-width="${t===0?2:1}" ${t===0?'stroke-dasharray="4 4" stroke-linecap="round"':""}/>
      <text x="${x(t)}" y="${H-6}" fill="${t===0?"#ff9f0a":"#949494"}" font-size="11" text-anchor="middle" font-weight="${t===0?600:400}">${t===0?esc(LL("inicio","onset")):`${t>0?"+":"−"}${Math.abs(t/24)} d`}</text>`).join("")}
    ${rows}
  </svg>`;
}

function render(view:HTMLElement){
  const site=data!.sites.find(s=>s.id===siteId)??data!.sites[0];siteId=site.id;
  const expanded=withHistory(site),c=investigate(expanded,decision,disabled,locals);
  const packageVisible=Date.parse(data!.generated_at)<=Date.parse(decision);
  const newest=site.evidence.reduce((v,r)=>r.retrieved_at>v?r.retrieved_at:v,"");
  const sources=SOURCES.map(source=>`<label class="source-toggle"><input type="checkbox" data-source="${source}" ${disabled.has(source)?"":"checked"}><span>${source}</span></label>`).join("");
  const rainRows=c.rain.models.map(m=>`<tr><th scope="row">${esc(m.source)}</th><td>${decimal(m.max24?.mm)}</td><td>${decimal(m.max48?.mm)}</td><td>${decimal(m.same_window_mm)}</td></tr>`).join("");
  const drought=c.drought.metrics.map(m=>`<div><strong>${decimal(m.total_mm)}<small> mm</small></strong><span>${m.days} ${esc(LL("días","days"))}</span><b>P${decimal(m.percentile)}</b><small>${m.reference_n} ${esc(LL("ventanas de referencia","reference windows"))}</small><small>${esc(m.start)} → ${esc(m.end)}</small></div>`).join("");
  const contextSources=["IMERG","CHIRPS"].filter(source=>c.supporting.includes(`historical_context_${source}`));
  const tr=(site.trends.SDII??{}) as Record<string,{pendiente_decada?:number;p?:number;q?:number|null}>;
  const trRows=contextSources.map(source=>tr[source]?`<tr><th>${source}</th><td>${sgn(tr[source].pendiente_decada??0)} mm/${esc(LL("día húmedo/década","wet day/decade"))}</td><td>${decimal(tr[source].q??null,3)}</td></tr>`:"").join("");
  const evidenceRows=[...expanded.evidence,...locals.filter(r=>r.site_id===site.id)].map(r=>{
    const ex=c.excluded.find(x=>x.id===r.id);
    const scope=r.spatial_scope==="province_not_point"?LL("Contexto provincial; no medición puntual","Provincial context; not a point measurement"):r.spatial_scope==="municipality_report_location_unspecified"?LL("Aportación municipal sin coordenadas del instrumento","Municipal report without instrument coordinates"):r.spatial_scope==="instrument_coordinates_user_reported"?LL("Coordenadas declaradas por el usuario","User-reported coordinates"):"";
    return `<tr><th>${esc(r.source_id)}</th><td>${esc(r.kind)}<br>${esc(r.quality)}<br>${esc(r.resolution??"")}</td><td>${r.spatial_scope==="municipality_report_location_unspecified"?"—":esc(r.returned.map(v=>decimal(v,3)).join(", "))}<br>${esc(scope)}</td><td>${esc(dateText(r.valid_end))}</td><td>${esc(dateText(r.first_seen_at))}</td><td>${esc(ex?why(ex.reason):LL("Admitida","Eligible"))}</td></tr>`;
  }).join("");
  view.innerHTML=`<div class="prep">
    ${board()}
    <p class="prep-message" role="status">${esc(message)}</p>
    <details class="prep-deep" id="prep-deep" ${deepOpen?"open":""}>
    <summary><span>${esc(LL(`Investigar ${site.name}`,`Investigate ${site.name}`))}</span><small>${esc(LL("fuentes, hora de decisión, mediciones locales y expediente","sources, decision time, local readings and case file"))}</small></summary>
    <section class="prep-toolbar" aria-label="${esc(LL("Tiempo","Time"))}">
      <label>${esc(LL("Hora de decisión (UTC)","Decision time (UTC)"))}<input id="prep-at" type="datetime-local" value="${decision.slice(0,16)}"></label>
      <button id="prep-before">${esc(LL("Antes de la captura","Before capture"))}</button><button id="prep-now">${esc(LL("Ahora","Now"))}</button>
      <button id="prep-refresh" ${loading?"disabled":""}>${esc(loading?LL("Consultando…","Fetching…"):LL("Actualizar pronósticos","Refresh forecasts"))}</button>
    </section>
    <p class="prep-stamp">${esc(LL("Última captura de este piloto","Latest capture for this pilot"))}: ${esc(dateText(newest))}. ${esc(LL("Horas en RD (UTC−4), salvo el control UTC.","Times in Dominican Republic (UTC−4), except the UTC control."))}</p>
    <div class="prep-cards">
      <section class="prep-card ${c.rain.state==="watch"?"attention":""}" aria-labelledby="prep-rain-title"><p class="prep-eyebrow">${esc(LL("Próximos 7 días · pronóstico","Next 7 days · forecast"))}</p><h2 id="prep-rain-title">${esc(status(c.rain.state))}</h2>
        <div class="prep-table"><table><thead><tr><th>${esc(LL("Modelo","Model"))}</th><th>${esc(LL("Máx. 24 h","Max 24 h"))}</th><th>${esc(LL("Máx. 48 h","Max 48 h"))}</th><th>${esc(LL("Mismas 48 h","Same 48 h"))}</th></tr></thead><tbody>${rainRows||`<tr><td colspan="4">${esc(LL("Sin ventana completa admisible","No eligible complete window"))}</td></tr>`}</tbody></table></div>
        <p>${esc(LL("Todos los acumulados en mm. Cada modelo conserva su celda; las columnas de máximos pueden corresponder a momentos distintos.","All totals in mm. Each model retains its own cell; peak columns may refer to different times."))}</p>
        ${c.rain.window?`<p>${esc(LL("Ventana común seleccionada","Selected common window"))}: ${esc(dateText(c.rain.window.start))} → ${esc(dateText(c.rain.window.end))}</p>`:""}
        <p class="prep-rule">${esc(c.rain.agreement==="two_partially_dependent"?LL("Dos modelos superan 100 mm en las mismas 48 h. Comparten parte de las observaciones: no son votos independientes.","Two models exceed 100 mm in the same 48 h. They share some observations: these are not independent votes."):c.rain.agreement==="one_or_disagree"?LL("La señal no tiene confirmación conjunta de los dos modelos. Revisar el desacuerdo o la cobertura.","The signal lacks joint confirmation from both models. Review disagreement or coverage."):LL("100 mm/48 h es una regla exploratoria. Estar por debajo no descarta inundaciones.","100 mm/48 h is an exploratory rule. Being below it does not rule out flooding."))}</p>
      </section>
      <section class="prep-card ${c.drought.state==="deficit"?"attention":""}" aria-labelledby="prep-drought-title"><p class="prep-eyebrow">ERA5 · ${esc(LL("lluvia acumulada","accumulated rainfall"))}</p><h2 id="prep-drought-title">${esc(status(c.drought.state))}</h2><div class="prep-deficit">${drought||`<p>${esc(LL("Sin referencia completa y vigente: se necesitan al menos 20 ventanas.","No complete, current reference: at least 20 windows are required."))}</p>`}</div>
        <p>${esc(LL("Referencia 2001–2024: mismo producto, celda y fecha del año. P≤20 indica déficit de precipitación para seguimiento; no demuestra sequía agrícola ni impactos. ERA5 es reanálisis, no pluviómetro, y tiene retraso.","Reference 2001–2024: same product, cell and calendar date. P≤20 flags rainfall deficit for monitoring; it does not establish agricultural drought or impacts. ERA5 is reanalysis, not a rain gauge, and arrives with a delay."))}</p>
      </section>
    </div>
    <section class="prep-sources"><h2>${esc(LL("Interrogar las fuentes","Question the sources"))}</h2><p>${esc(LL("Retira una evidencia y observa qué afirmaciones sobreviven. No cambia el clima ni los insumos internos de los productos.","Remove evidence and see which claims survive. This does not change the weather or the products' internal inputs."))}</p><div class="prep-toggles">${sources}</div></section>
    <div class="prep-lower">
      <section class="prep-card"><h2>${esc(LL("Qué comprobar después","What to check next"))}</h2><ol class="prep-tasks">${c.tasks.map(t=>`<li><strong>${esc(task(t.id))}</strong></li>`).join("")}</ol><p>${esc(LL("Apoyo a verificación y preparación, no órdenes de evacuación. Los avisos oficiales y la evaluación local tienen su propio procedimiento.","Support for verification and preparedness, not evacuation orders. Official warnings and local assessment follow their own procedures."))}</p><a href="https://www.coe.gob.do/" target="_blank" rel="noopener">COE ↗</a> · <a href="https://indomet.gob.do/" target="_blank" rel="noopener">INDOMET ↗</a></section>
      <section class="prep-card"><h2>${esc(LL("Quién respalda a quién","Who supports whom"))}</h2><div class="prep-graph" role="group" aria-label="${esc(LL("Grafo de procedencia","Provenance graph"))}">${data!.graph.nodes.map(n=>`<button data-node="${n}" aria-pressed="${!disabled.has(n)}">${n}</button>`).join("")}</div><p id="prep-node-detail">${esc(LL("Toca un nodo para ver sus conexiones. Las fuentes con control se pueden retirar del expediente.","Select a node to inspect its links. Sources with controls can be removed from the case."))}</p><ul class="prep-edges">${data!.graph.edges.map(([a,b,label])=>`<li><button data-node="${esc(a)}">${esc(a)}</button> → <button data-node="${esc(b)}">${esc(b)}</button><small>${esc(label)}</small></li>`).join("")}</ul><p>${esc(LL("Grafo resumido de insumos, no modelo causal ni garantía de independencia. Compartir datos limita la corroboración.","Summarised input graph, not a causal model or independence guarantee. Shared data limits corroboration."))}</p></section>
    </div>
    <section class="prep-card prep-local"><h2>${esc(LL("Incorporar una medición local","Add a local measurement"))}</h2><p>${esc(LL("Se guarda solo en este navegador y queda sin verificar. No confirma automáticamente un pronóstico futuro.","Stored only in this browser and marked unverified. It does not automatically confirm a future forecast."))}</p>
      <form id="prep-local"><label>${esc(LL("Inicio UTC","Start UTC"))}<input name="start" type="datetime-local" required></label><label>${esc(LL("Fin UTC","End UTC"))}<input name="end" type="datetime-local" required></label><label>${esc(LL("Lluvia (mm)","Rainfall (mm)"))}<input name="mm" type="number" min="0" step="any" required></label><label>${esc(LL("Procedencia","Provenance"))}<input name="source" minlength="3" required placeholder="${esc(LL("Instrumento, lugar y responsable","Instrument, location and reporter"))}"></label><label class="source-toggle"><input name="synthetic" type="checkbox">${esc(LL("Ejemplo sintético","Synthetic example"))}</label><button type="submit">${esc(LL("Añadir y recalcular","Add and recalculate"))}</button></form>
      <label>${esc(LL("Importar JSON: site_id, start/end ISO UTC, mm, source; lat/lon opcionales","Import JSON: site_id, start/end ISO UTC, mm, source; optional lat/lon"))}<input type="file" id="prep-import" accept="application/json,.json"></label>
      <ul>${c.local.map(r=>`<li><strong>${decimal(r.precipitation_mm)} mm</strong> · ${esc(dateText(r.valid_start))} → ${esc(dateText(r.valid_end))} · ${esc(r.provenance)} · <b>${esc(r.quality==="synthetic"?LL("SINTÉTICA","SYNTHETIC"):LL("SIN VERIFICAR","UNVERIFIED"))}</b><button data-remove-local="${esc(r.id)}">${esc(LL("Eliminar","Remove"))}</button></li>`).join("")}</ul>
    </section>
    <section class="prep-card"><h2>${esc(LL("Planificar con el contexto NASA","Plan with NASA context"))}</h2><p>${esc(LL("SDII provincial · 2001–2024. No es el estado meteorológico actual del punto. q: FDR entre provincias.","Provincial SDII · 2001–2024. This is not the point's current weather. q: FDR across provinces."))}</p><div class="prep-table"><table><thead><tr><th>${esc(LL("Producto","Product"))}</th><th>${esc(LL("Tendencia","Trend"))}</th><th>q</th></tr></thead><tbody>${trRows||`<tr><td colspan="3">${esc(LL("Contexto retirado o no disponible a la hora elegida","Context removed or unavailable at the selected time"))}</td></tr>`}</tbody></table></div><a href="#tendencias">${esc(LL("Explorar las 32 provincias y sus series →","Explore all 32 provinces and their time series →"))}</a></section>
    <section class="prep-card"><h2>${esc(LL("Dónde falta medir","Where measurement is needed"))}</h2>${packageVisible?priorityMap(site):`<p>${esc(LL("Mapa excluido: el paquete aún no se había capturado a la hora elegida.","Map excluded: the package was not captured at the chosen time."))}</p>`}<p>${esc(LL("Prioridad de medición: promedio de rangos de desacuerdo, persistencia, cambio de clasificación y distancia a estaciones GHCN activas en 2024. No es peligro, exposición ni inventario completo de pluviómetros. Datos históricos 2001–2024.","Measurement priority: mean ranks of disagreement, persistence, classification changes and distance to GHCN stations active in 2024. This is not hazard, exposure or a complete rain-gauge inventory. Historical data, 2001–2024."))}</p></section>
    <details class="prep-card" hidden><summary>${esc(LL("Prueba histórica del Yuna y límites","Yuna historical test and limitations"))}</summary><p>${esc(packageVisible?LL("2016–2024: al pedir confirmación de CHIRPS, 39→16 episodios sin evento catalogado; detecciones 7/8→6/8. Ninguna primera señal precede estrictamente al inicio catalogado. No es validación de estos pronósticos ni de acciones municipales.","2016–2024: requiring CHIRPS confirmation, 39→16 episodes without a catalogued event; detections 7/8→6/8. No first signal strictly precedes the catalogued start. This does not validate these forecasts or municipal actions."):LL("Resultado excluido de la reproducción: el paquete aún no se había capturado.","Result excluded from replay: package not captured yet."))}</p><p>${esc(LL("GOES: sin resolver. No se ha demostrado reducción de daños.","GOES: unresolved. Damage reduction has not been demonstrated."))}</p></details>
    <details class="prep-card"><summary>${esc(LL("Auditar tiempo, coordenadas y exclusiones","Audit time, coordinates and exclusions"))}</summary><p>${esc(LL("Emisión desconocida se conserva como desconocida. La primera captura es un límite conservador de disponibilidad; no equivale a la emisión ni a publicación oficial.","Unknown issue time remains unknown. First capture is a conservative availability boundary, not model initialisation or official publication."))}</p><div class="prep-table"><table><thead><tr><th>${esc(LL("Fuente","Source"))}</th><th>${esc(LL("Tipo/calidad","Type/quality"))}</th><th>${esc(LL("Coordenadas devueltas","Returned coordinates"))}</th><th>${esc(LL("Fin válido","Valid end"))}</th><th>${esc(LL("Primera captura","First capture"))}</th><th>${esc(LL("Estado","State"))}</th></tr></thead><tbody>${evidenceRows}</tbody></table></div></details>
    <footer class="prep-export"><button id="prep-json">${esc(LL("Descargar expediente JSON","Download case JSON"))}</button><button id="prep-html">${esc(LL("Informe para compartir / imprimir","Share / print report"))}</button><small>${esc(LL("Incluye reglas, fuentes, exclusiones y hora de decisión.","Includes rules, sources, exclusions and decision time."))}</small></footer>
    </details>
  </div>`;
  const slot=view.querySelector("#hx-slot");
  if(slot){if(!hxHost){hxHost=document.createElement("div");hxHost.className="pb-hx";hx=hurricanes(hxHost);}slot.replaceWith(hxHost);}
  view.querySelectorAll<HTMLButtonElement>("[data-pick]").forEach(b=>b.addEventListener("click",()=>{
    const id=b.dataset.pick!;deepOpen=!(deepOpen&&siteId===id);siteId=id;message="";render(view);
    if(deepOpen)requestAnimationFrame(()=>view.querySelector("#prep-deep")?.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"}));
  }));
  view.querySelector("[data-goto-map]")?.addEventListener("click",()=>{deepOpen=true;render(view);requestAnimationFrame(()=>view.querySelector(".prep-map")?.closest("section")?.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"}));});
  view.querySelector<HTMLDetailsElement>("#prep-deep")!.addEventListener("toggle",ev=>{deepOpen=(ev.target as HTMLDetailsElement).open;view.querySelectorAll(".pb-row").forEach(r=>r.classList.toggle("on",deepOpen&&(r as HTMLElement).dataset.pick===siteId));});
  view.querySelector<HTMLInputElement>("#prep-at")!.addEventListener("change",ev=>{const value=(ev.target as HTMLInputElement).value;if(value)decision=new Date(`${value}:00Z`).toISOString();render(view);});
  view.querySelector("#prep-before")!.addEventListener("click",()=>{decision=new Date(Math.min(...expanded.evidence.map(r=>Date.parse(r.first_seen_at)))-1000).toISOString();message=LL("La reproducción temporal excluye lo que todavía no se había capturado.","Temporal replay excludes evidence not captured yet.");render(view);});
  view.querySelector("#prep-now")!.addEventListener("click",()=>{decision=isoNow();message="";render(view);});
  view.querySelectorAll<HTMLInputElement>("[data-source]").forEach(input=>input.addEventListener("change",()=>{const source=input.dataset.source!;input.checked?disabled.delete(source):disabled.add(source);render(view);}));
  view.querySelectorAll<HTMLButtonElement>("[data-node]").forEach(b=>b.addEventListener("click",()=>{
    const node=b.dataset.node!;const edges=data!.graph.edges.filter(([a,b])=>a===node||b===node);
    const target=view.querySelector("#prep-node-detail")!;target.textContent=`${node}: ${edges.map(e=>e.join(" → ")).join(" · ")||LL("Sin dependencia documentada en este grafo resumido; no demuestra independencia.","No dependency documented in this summarised graph; this does not prove independence.")}`;
  }));
  view.querySelector("#prep-refresh")!.addEventListener("click",async()=>{
    const token=alive;loading=true;message="";render(view);
    const records=await liveForecasts(site);
    for(const r of records)history.push(r);
    // Conservar hasta 12 instantáneas por modelo y piloto, sin contar duplicados como votos.
    history=history.filter((r,i,a)=>a.filter(x=>x.site_id===r.site_id&&x.source_id===r.source_id).slice(-12).includes(a[i]));save();
    loading=false;decision=isoNow();message=records.length===2?LL("Dos modelos actualizados; coordenadas y primera captura conservadas.","Two models refreshed; coordinates and first capture retained."):LL(`Se actualizaron ${records.length}/2 modelos. Los demás conservan su copia fechada; no se convierten en cero.`,`Refreshed ${records.length}/2 models. Others retain dated copies; missing data is not zero.`);
    if(token===alive)render(view);
  });
  view.querySelector<HTMLFormElement>("#prep-local")!.addEventListener("submit",ev=>{
    ev.preventDefault();const f=new FormData(ev.currentTarget as HTMLFormElement);
    try{const raw=String(f.get("mm")??"");if(!raw.trim())throw Error();locals.push(localEvidence({site_id:site.id,start:`${f.get("start")}:00Z`,end:`${f.get("end")}:00Z`,mm:Number(raw),source:String(f.get("source")),synthetic:f.get("synthetic")==="on"},site,isoNow()));decision=isoNow();save();message=LL("Aportación incorporada sin verificar. Las tareas y el expediente se recalcularon.","Unverified report added. Tasks and case recalculated.");render(view);}catch{message=LL("Medición inválida: revisa fechas UTC, intervalo terminado, mm≥0 y procedencia.","Invalid measurement: check UTC dates, completed interval, mm≥0 and provenance.");view.querySelector(".prep-message")!.textContent=message;}
  });
  view.querySelectorAll<HTMLButtonElement>("[data-remove-local]").forEach(b=>b.addEventListener("click",()=>{locals=locals.filter(r=>r.id!==b.dataset.removeLocal);save();render(view);}));
  view.querySelector<HTMLInputElement>("#prep-import")!.addEventListener("change",async ev=>{
    const file=(ev.target as HTMLInputElement).files?.[0];if(!file)return;
    try{if(file.size>1000000)throw Error("file_too_large");const raw=JSON.parse(await file.text()),items=Array.isArray(raw)?raw:[raw];if(!items.length||items.length>100)throw Error("invalid_count");
      const stamp=isoNow(),records=items.map((item,i)=>({...localEvidence(item,site,stamp),id:`local:${site.id}:${stamp}:${i}`}));
      locals.push(...records);decision=stamp;save();message=LL(`Se importaron ${records.length} aportaciones sin verificar.`,`Imported ${records.length} unverified reports.`);render(view);
    }catch{message=LL("JSON inválido: comprueba municipio, fechas UTC, mm y procedencia. No se importó ninguna fila.","Invalid JSON: check site, UTC dates, mm and provenance. No rows imported.");view.querySelector(".prep-message")!.textContent=message;}
  });
  view.querySelector("#prep-json")!.addEventListener("click",()=>download(site,c,expanded,"json"));
  view.querySelector("#prep-html")!.addEventListener("click",()=>download(site,c,expanded,"html"));
}

function download(site:Site,c:InvestigationCase,expanded:Site,format:"json"|"html"){
  const report={version:1,generated_at:isoNow(),case:c,site:expanded,local_reports:locals.filter(r=>r.site_id===site.id),source_graph:data!.graph,
    methods:{rain:"max rolling48h>100mm exploratory; joint comparisons in same interval; no independent votes",deficit:"P<=20, min20 complete calendar-matched ERA5 windows 2001-2024"},
    limits:["Prototype; no operational alert or damage reduction validation","Representative points and different grids","Forecast capture is not issue time","Local reports remain unverified","ERA5 delayed; catalogue incomplete"]};
  const body=format==="json"?JSON.stringify(report,null,2):`<!doctype html><html lang="${getLang()}"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Stellar Horizons · ${esc(site.name)}</title><style>body{max-width:1000px;margin:auto;padding:24px;font:16px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{line-height:1.2}</style><h1>${esc(site.name)} · Stellar Horizons</h1><p>${esc(LL("Expediente para preparación municipal · prototipo","Municipal preparedness case · prototype"))}</p><p>${esc(dateText(c.decision_at))}</p><h2>${esc(status(c.rain.state))}</h2><h2>${esc(status(c.drought.state))}</h2><ol>${c.tasks.map(t=>`<li>${esc(task(t.id))}</li>`).join("")}</ol><p>${esc(LL("No se ha demostrado anticipación ni reducción de daños. Consultar avisos oficiales.","Lead time and damage reduction have not been demonstrated. Check official warnings."))}</p><details open><summary>${esc(LL("Evidencia completa y reproducible","Complete reproducible evidence"))}</summary><pre>${esc(JSON.stringify(report,null,2))}</pre></details></html>`;
  const url=URL.createObjectURL(new Blob([body],{type:format==="json"?"application/json":"text/html"}));const a=document.createElement("a");a.href=url;a.download=`stellar-${site.id}-${format==="json"?"expediente.json":"informe.html"}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
