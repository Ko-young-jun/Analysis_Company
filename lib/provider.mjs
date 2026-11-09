import catalog from '../web/catalog.json' with {type:'json'};
export function selectSeries(id) {
 const series=catalog.series.find(s=>s.id===id);
 if(!series) throw new Error('등록되지 않은 지표입니다.');
 return series;
}
export function parseWorldBank(data,code,countries) {
 if(!Array.isArray(data)||data.length!==2||Number(data[0].pages)>1) throw new Error('공식 API 응답 구조를 확인할 수 없습니다.');
 return (data[1]||[]).map(r=>{
  if(r.indicator?.id!==code||!countries.includes(r.countryiso3code)) throw new Error('요청과 다른 통계가 반환되었습니다.');
  if(r.value!==null&&(typeof r.value!=='number'||!Number.isFinite(r.value))) throw new Error('올바르지 않은 통계 수치입니다.');
  return {country:r.countryiso3code,period:r.date,value:r.value,release_date:null,status:'미확인',provider_updated:data[0].lastupdated||null};
 });
}
export function parseFred(text,code,country,frequency) {
 const lines=text.trim().split(/\r?\n/); const headers=lines.shift().split(',');
 const col=headers.indexOf(code); const date=headers.findIndex(h=>h==='observation_date'||h==='DATE');
 if(col<0||date<0) throw new Error('FRED 응답 열을 확인할 수 없습니다.');
 return lines.filter(Boolean).map(line=>{
  const cells=line.split(','); const raw=cells[col];
  const value=raw==='.'||raw===''?null:Number(raw);
  if(value!==null&&!Number.isFinite(value)) throw new Error('올바르지 않은 수치입니다.');
  return {country,period:frequency==='M'?cells[date].slice(0,7):cells[date],value,release_date:null,status:'미확인',provider_updated:null};
 });
}
export async function collect(id,fetcher=fetch) {
 const series=selectSeries(id), end=new Date().getUTCFullYear(), start=end-11;
 const countries=Object.keys(catalog.countries);
 const url=series.adapter==='worldbank'
  ?`https://api.worldbank.org/v2/country/${countries.join(';')}/indicator/${series.code}?format=json&date=${start}:${end}&per_page=20000&source=2`
  :`https://fred.stlouisfed.org/graph/fredgraph.csv?id=${series.code}&cosd=${start}-01-01&coed=${end}-12-31`;
 const response=await fetcher(url,{signal:AbortSignal.timeout(22000),headers:{Accept:series.adapter==='worldbank'?'application/json':'text/csv'}});
 if(!response.ok) throw new Error(`공식 출처 응답 오류 (HTTP ${response.status}).`);
 const rows=series.adapter==='worldbank'?parseWorldBank(await response.json(),series.code,countries):parseFred(await response.text(),series.code,series.country,series.frequency);
 return {series,rows:rows.sort((a,b)=>a.period.localeCompare(b.period)),retrieved_at:new Date().toISOString(),source_url:url,note:'발표일·확정 여부 미확인. 조회 시각과 통계 기준기간은 다릅니다.'};
}
