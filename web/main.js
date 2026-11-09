import Chart from 'chart.js/auto';
import catalog from './catalog.json';
import './style.css';
const esc=s=>String(s??'미확인').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const root=document.querySelector('#app');
root.innerHTML=`<header><span class="brand">ECONOMIC REALITY</span><h1>경제의 실체<span>성장 너머, 삶의 변화까지.</span></h1><p>대한민국과 세계경제를 공식 통계로 비교합니다.</p></header><main><nav aria-label="주요 화면"><button data-tab="explore" class="active">지표 탐색</button><button data-tab="risk">위험과 전망</button><button data-tab="sources">자료와 한계</button></nav><section id="explore"><div class="filters"><label>분석 영역<select id="category">${catalog.categories.map(c=>`<option>${esc(c)}</option>`).join('')}</select></label><label>경제지표<select id="series"></select></label><label>비교 기간<select id="years"><option value="10">최근 10년</option><option value="5">최근 5년</option><option value="3">최근 3년</option><option value="1">최근 1년</option></select></label><button id="refresh" class="primary">공식 자료 조회</button></div><fieldset id="countries"><legend>비교 국가·지역</legend>${Object.entries(catalog.countries).map(([id,name])=>`<label><input type="checkbox" value="${id}" ${['KOR','USA','JPN'].includes(id)?'checked':''}>${name}</label>`).join('')}</fieldset><div id="status" role="status" aria-live="polite">공식 자료를 불러오는 중입니다.</div><div id="metrics" class="metrics"></div><article class="chart-card"><h2 id="chart-title">시계열 비교</h2><p id="meta"></p><div class="chart-box"><canvas id="chart" role="img" aria-label="국가별 경제지표 시계열"></canvas></div><p id="note"></p></article><div class="actions"><button id="csv" disabled>표시 데이터 CSV</button><button id="report" disabled>분석 자료 HTML 저장</button></div><details><summary>정확한 수치와 공표 정보</summary><div id="table" class="table-wrap"></div></details><aside id="gap"></aside></section><section id="risk" hidden><h2>위험은 여러 지표로 확인해야 합니다.</h2><p>아래는 검증할 조건의 목록입니다. 현재 위험 수준이나 전망 확률을 판정한 결과가 아닙니다.</p><div class="table-wrap"><table><thead><tr><th>위험</th><th>발생 조건</th><th>완화 요인</th><th>관찰 지표</th><th>영향</th></tr></thead><tbody>${catalog.risks.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><h2>조건부 시나리오</h2><div class="scenario-grid">${catalog.scenarios.map(s=>`<article><h3>${esc(s['시나리오'])}</h3>${Object.entries(s).filter(([k])=>k!=='시나리오').map(([k,v])=>`<p><strong>${esc(k)}</strong><br>${esc(v)}</p>`).join('')}</article>`).join('')}</div><h2>기간별 관찰 변수</h2>${Object.entries(catalog.horizons).map(([k,v])=>`<p><strong>${esc(k)}</strong> · ${esc(v)}</p>`).join('')}</section><section id="sources" hidden><h2>자료가 말할 수 있는 범위</h2><p>World Bank WDI 연간 통계와 FRED 공식 CSV를 조회합니다. 발표일·속보/잠정/확정 여부가 제공되지 않으면 미확인으로 표시합니다. 미국 금리나 연간 통계만으로 한국의 현재 경기국면을 판정하지 않습니다.</p><p>국제 청년통계는 15~24세 ILO 추정입니다. 한국의 청년 정의와 다릅니다. 민간신용은 가계부채와, 중앙정부 부채는 일반정부 부채와 다릅니다.</p><h3>추가 검증이 필요한 자료</h3>${Object.entries(catalog.gaps).map(([k,v])=>`<article class="gap"><h3>${esc(k)}</h3><p>${esc(v[0])}</p><p>${esc(v[1])}</p></article>`).join('')}<h3>보관과 재현</h3><p>웹 버전은 공식 출처를 조회하며 서버에 영구 저장하지 않습니다. 표시 데이터와 분석 자료를 다운로드할 수 있습니다. 개정 이력의 영구 보관·전체 보고서 생성은 GitHub 저장소의 Python·SQLite 프로그램에서 지원합니다.</p><a href="https://github.com/Ko-young-jun/Analysis_Company" target="_blank" rel="noopener noreferrer">소스 코드와 실행 방법 ↗</a></section><footer>공식 통계 · 기준기간 표시 · 결측 보존<br>확인된 사실과 경제학적 해석, 미래 전망을 구분합니다.</footer></main>`;
let data=null, chart=null, generation=0, visible=[];
const colors=['#176B72','#DC7438','#6458A6','#467149','#B34F6B','#2C659B','#7E7158'];
const el=id=>document.getElementById(id);
function fillSeries(){
 const category=el('category').value;
 el('series').innerHTML=catalog.series.filter(s=>s.category===category).map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('');
 el('gap').innerHTML=`<h3>함께 확인해야 할 자료</h3><p>${esc(catalog.gaps[category][0])}</p><small>${esc(catalog.gaps[category][1])}</small>`;
}
function filtered(){
 const countries=[...document.querySelectorAll('#countries input:checked')].map(c=>c.value);
 const cutoff=new Date(); cutoff.setUTCFullYear(cutoff.getUTCFullYear()-Number(el('years').value));
 return data.rows.filter(r=>{
  let end;if(data.series.frequency==='A')end=new Date(`${r.period}-12-31T23:59:59Z`);else if(data.series.frequency==='M'){const [y,m]=r.period.split('-').map(Number);end=new Date(Date.UTC(y,m,0,23,59,59));}else end=new Date(r.period+'T23:59:59Z');
  return countries.includes(r.country)&&end>=cutoff;
 });
}
function render(){
 if(!data)return;visible=filtered();
 const series=data.series,countries=[...new Set(visible.map(r=>r.country))];
 const labels=[...new Set(visible.map(r=>r.period))].sort();
 // 누락 연·월도 축에 남겨 선이 결측을 가로질러 이어지지 않게 한다.
 if(labels.length&&series.frequency==='A'){const a=Number(labels[0]),b=Number(labels.at(-1));labels.splice(0,labels.length,...Array.from({length:b-a+1},(_,i)=>String(a+i)));}
 if(labels.length&&series.frequency==='M'){let [y,m]=labels[0].split('-').map(Number);const end=labels.at(-1),all=[];while(`${y}-${String(m).padStart(2,'0')}`<=end){all.push(`${y}-${String(m).padStart(2,'0')}`);if(++m===13){m=1;y++;}}labels.splice(0,labels.length,...all);}
 if(chart)chart.destroy();
 chart=new Chart(el('chart'),{type:'line',data:{labels,datasets:countries.map((country,i)=>{const values=new Map(visible.filter(r=>r.country===country).map(r=>[r.period,r.value]));return {label:catalog.countries[country],data:labels.map(p=>values.get(p)??null),borderColor:colors[i],backgroundColor:colors[i],pointRadius:labels.length>100?0:2,borderWidth:2,spanGaps:false};})},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom'}},scales:{x:{ticks:{maxTicksLimit:12}},y:{title:{display:true,text:series.unit}}}}});
 el('chart-title').textContent=series.name;
 el('meta').innerHTML=`${esc(series.unit)} · ${esc(labels[0]||'없음')} ~ ${esc(labels.at(-1)||'없음')} · <a href="${esc(series.source_url)}" target="_blank" rel="noopener noreferrer">${esc(series.source)} ↗</a>`;
 el('note').textContent=`${series.adjustment} · ${series.price_basis}. ${series.note} 조회: ${new Date(data.retrieved_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} KST`;
 el('metrics').innerHTML=countries.map(c=>{const last=visible.filter(r=>r.country===c).at(-1);return `<div><span>${esc(catalog.countries[c])}</span><strong>${last.value===null?'결측':last.value.toLocaleString('ko-KR',{maximumFractionDigits:2})}</strong><small>${esc(series.unit)} · ${esc(last.period)}</small></div>`;}).join('');
 el('status').className=visible.some(r=>r.value!==null)?'success':'warning';
 el('status').textContent=visible.some(r=>r.value!==null)?'공식 자료를 조회했습니다. 국가별 기준기간과 정의 차이를 확인하세요.':'선택 범위에 수치가 없습니다. 결측을 0으로 대체하지 않습니다.';
 el('table').innerHTML=`<table><thead><tr><th>국가</th><th>기준기간</th><th>값</th><th>발표일</th><th>공표 상태</th></tr></thead><tbody>${visible.slice().reverse().map(r=>`<tr><td>${esc(catalog.countries[r.country])}</td><td>${esc(r.period)}</td><td>${esc(r.value)}</td><td>미확인</td><td>${esc(r.status)}</td></tr>`).join('')}</tbody></table>`;
 el('csv').disabled=el('report').disabled=!visible.some(r=>r.value!==null);
}
async function load(){
 const version=++generation;data=null;visible=[];
 if(chart){chart.destroy();chart=null;}
 el('metrics').innerHTML='';el('table').innerHTML='';el('meta').textContent='';el('note').textContent='';
 el('chart-title').textContent=el('series').selectedOptions[0].text;
 el('csv').disabled=el('report').disabled=true;
 el('status').className='';el('status').textContent='공식 자료를 불러오는 중입니다…';
 try{const response=await fetch('/api/indicators?id='+encodeURIComponent(el('series').value));const payload=await response.json();if(!response.ok)throw new Error(payload.error||'자료 조회 실패');if(version!==generation)return;data=payload;render();}
 catch{if(version!==generation)return;el('status').className='warning';el('status').textContent='공식 통계에 연결하지 못했습니다. 잠시 후 다시 조회하세요. 데이터 없이 경제 수치나 진단을 생성하지 않습니다.';}
}
function download(content,type,name){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
el('csv').onclick=()=>{const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';const rows=[['지표','국가','기준기간','값','단위','출처','조회시각','발표일','공표상태'],...visible.map(r=>[data.series.name,catalog.countries[r.country],r.period,r.value,data.series.unit,data.series.source_url,data.retrieved_at,r.release_date,r.status])];download('\uFEFF'+rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8','경제의실체.csv');};
el('report').onclick=()=>{download(`<!doctype html><html lang="ko"><meta charset="utf-8"><title>경제의 실체 — 지표 분석 자료</title><style>body{max-width:1000px;margin:40px auto;padding:20px;font:16px/1.7 sans-serif;color:#172d35}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ddd}img{width:100%}</style><h1>경제의 실체 — ${esc(data.series.name)}</h1><p>선택한 지표의 관측자료이며 전체 경제 진단 보고서는 아닙니다.</p><p>${el('meta').innerHTML}</p><img alt="시계열 그래프" src="${chart.toBase64Image()}"><p>${esc(el('note').textContent)}</p><h2>확인된 관측값</h2>${el('table').innerHTML}<h2>해석상 한계</h2><p>단일 지표로 경기국면이나 인과관계를 확정하지 않습니다. 발표일과 공표 확정 여부는 미확인입니다.</p><h2>추가 자료</h2>${el('gap').innerHTML}</html>`,'text/html;charset=utf-8','경제의실체_분석자료.html');};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));['explore','risk','sources'].forEach(id=>el(id).hidden=id!==b.dataset.tab);});
el('category').onchange=()=>{fillSeries();load();};el('series').onchange=load;el('refresh').onclick=load;el('years').onchange=render;el('countries').onchange=render;fillSeries();load();
