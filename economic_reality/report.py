"""동일 데이터 스냅샷에서 한국어 보고서와 근거 표를 생성한다."""
import difflib
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .analysis import HORIZONS, RISKS, SCENARIOS, changes, coverage, latest, regime
from .catalog import CATEGORIES, COUNTRIES, GAPS

TITLE = '대한민국과 세계경제의 실체: 데이터로 분석한 현재와 미래'
CHAPTERS = [
('현재 한국 경제의 종합 진단', None),
('경제성장의 구조와 한계', CATEGORIES[0]),
('물가와 국민의 실질구매력', CATEGORIES[1]),
('청년고용과 노동시장', CATEGORIES[2]),
('가계부채와 금융시장', CATEGORIES[3]),
('부동산과 자산시장', CATEGORIES[4]),
('세계경제와 한국의 관계', CATEGORIES[5]),
('산업별 성장과 구조적 변화', CATEGORIES[6]),
('경제적 불평등과 인구구조', CATEGORIES[7]),
]
INTERPRETATIONS = {
CATEGORIES[0]: ('실질 GDP는 생산 규모를 측정하지만 분배와 삶의 질을 직접 측정하지 않습니다. 수출 증가율만으로 순수출의 성장기여도를 계산할 수 없습니다.', '실질소비·투자와 고용이 함께 개선되면 성장의 확산 근거가 됩니다.', '수출·특정 산업에 성장이 집중되면 내수 체감 개선이 제한될 수 있습니다.', '수입 감소로 순수출이 개선될 수 있으므로 수출 주도 성장과 구분해야 합니다.'),
CATEGORIES[1]: ('물가상승률 둔화는 가격 수준 하락과 다릅니다. 실질임금은 동일 기간 명목임금과 적절한 소비자물가 지수로 계산해야 합니다.', '임금 증가가 생활비 증가를 웃돌면 구매력 회복 조건이 됩니다.', '평균 물가가 안정돼도 식품·주거비 비중이 큰 저소득층 부담은 클 수 있습니다.', '평균임금 상승이 구성효과인지 동일 노동자의 소득 개선인지 별도로 확인해야 합니다.'),
CATEGORIES[2]: ('실업률은 구직 포기·쉬었음 인구를 포함하지 않으므로 고용률·참가율과 함께 해석해야 합니다. 15~24세 국제통계와 한국 청년통계의 연령 범위가 다릅니다.', '청년고용률·참가율의 동반 개선은 취업 기회의 확대와 부합합니다.', '청년 신규채용 감소는 경력 축적과 장기 소득에 영향을 줄 수 있습니다.', '실업률 하락은 취업 증가뿐 아니라 노동시장 이탈에서도 발생할 수 있습니다. AI의 고용 영향은 산업 수요·인구 변화와 분리해 검증해야 합니다.'),
CATEGORIES[3]: ('금리는 차입자와 예금자에게 다른 영향을 줍니다. 민간신용·가계부채·기업부채의 범위를 구분해야 합니다.', '소득 증가와 부채 만기 연장은 상환 부담을 완화할 수 있습니다.', '고금리와 소득 충격이 겹치면 연체·부실이 늘 수 있습니다.', '부채 총량만으로 위기를 예측할 수 없습니다. 금리구조·자산·현금흐름·자본완충을 함께 봐야 합니다.'),
CATEGORIES[4]: ('자산가격은 미래 현금흐름과 할인율 기대를 반영하므로 현재 실물생산과 일대일로 대응하지 않습니다.', '기업이익·소득에 뒷받침된 가격 상승은 재무 여력 개선과 양립합니다.', '소득 대비 주거비·부채 확대는 무주택 청년과 차입자 부담을 높일 수 있습니다.', '전국 평균은 수도권·지방 및 소유자·임차인의 격차를 숨길 수 있습니다.'),
CATEGORIES[5]: ('미국 금리, 중국 수요, 유럽·일본 경기 변화는 교역·환율·자금조달 경로로 한국에 영향을 줍니다. EU와 유로지역은 서로 다른 집계입니다.', '해외 수요 회복과 공급망 안정은 수출·수입비용에 유리할 수 있습니다.', '무역장벽·유가·달러 충격은 수출과 실질구매력을 동시에 압박할 수 있습니다.', '원화 약세는 수출기업에 유리할 수 있지만 수입원가·외화부채 부담은 커질 수 있습니다.'),
CATEGORIES[6]: ('생산·수출·투자·고용을 동일 산업분류로 연결해야 성장의 고용 파급을 평가할 수 있습니다. 제조업 합계를 반도체나 AI 성과로 해석하지 않습니다.', '생산성 개선과 신산업 투자 확대는 중장기 성장 여력을 높일 수 있습니다.', '고용 유발이 낮은 산업 집중과 기술 전환의 숙련 불일치는 성과 확산을 제한할 수 있습니다.', 'AI는 일부 과업을 대체하면서 새로운 과업을 만들 수 있습니다. 향후 5~10년 경쟁력을 단일 지표로 확정하지 않습니다.'),
CATEGORIES[7]: ('소득분배와 자산분배는 다릅니다. 지니계수 비교에는 세전·세후, 가구·개인, 균등화 기준의 일치가 필요합니다.', '노동참여·생산성 개선과 이전소득은 인구구조 충격을 완화할 수 있습니다.', '고령화와 생산가능인구 감소는 노동공급·재정부담 경로로 성장에 제약이 될 수 있습니다.', '출산율 변화가 노동공급에 미치는 영향은 장기간에 걸칩니다. 인구 감소가 1인당 소득 감소를 자동 의미하지 않습니다.'),
}


def table(df):
    if df.empty:
        return '확인된 관측값 없음.'
    def clean(v):
        if pd.isna(v): return '미확인'
        if isinstance(v,float): return f'{v:,.3f}'
        return str(v).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(map(str,df.columns))+' |','| '+' | '.join(['---']*len(df.columns))+' |']+['| '+' | '.join(clean(v) for v in row)+' |' for row in df.itertuples(index=False,name=None)])


def save_chart(group,path):
    os.environ.setdefault('MPLCONFIGDIR','/tmp/economic-reality-mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    fontpath='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font=FontProperties(fname=fontpath) if Path(fontpath).exists() else FontProperties()
    m=group.iloc[0]
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    for country,g in group.groupby('country'):
        x=changes(g,m.frequency)
        dates=pd.PeriodIndex(x.period,freq={'A':'Y'}.get(m.frequency,m.frequency)).to_timestamp()
        ax.plot(dates,x.value,label=COUNTRIES.get(country,country),linewidth=1.8)
    ax.set_title(m['name'],fontproperties=font,fontsize=15)
    ax.set_ylabel(m.unit,fontproperties=font)
    ax.grid(alpha=.2)
    ax.legend(prop=font)
    fig.savefig(path,dpi=140)
    plt.close(fig)


def generate(store, output='reports'):
    root=Path(output)
    root.mkdir(parents=True,exist_ok=True)
    previous=sorted(root.glob('*/report.md'))
    stamp=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S-%f')
    target=root/stamp
    target.mkdir()
    (target/'charts').mkdir()
    runs=store.runs()
    completed=runs[runs.finished_at.notna()]
    cutoff=int(completed.id.max()) if not completed.empty else 0
    df=store.frame(as_of=cutoff)
    evidence=df.to_csv(index=False).encode('utf-8-sig')
    (target/'evidence.csv').write_bytes(evidence)
    cov=coverage(store)
    cov.to_csv(target/'coverage.csv',index=False,encoding='utf-8-sig')
    store.attempts().to_csv(target/'collection-log.csv',index=False,encoding='utf-8-sig')
    valid=df.dropna(subset=['value']) if not df.empty else df
    complete=not valid.empty
    report=[f'# {TITLE}',f'작성일: {datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")}',
            '**부분 분석 보고서 — 미확보 지표와 공표시점 확인 필요**' if complete else '**수집 상태 보고서 — 실제 데이터 미확보로 경제 진단 작성 보류**',
            '## 목차','\n'.join(f'{i+1}. {title}' for i,title in enumerate(['Executive Summary']+[c[0] for c in CHAPTERS]+['향후 경제 전망','주요 위험요인','종합 결론','참고문헌 및 데이터 출처'])),
            '## Executive Summary']
    if not complete:
        report += ['공식 통계의 실제 관측값이 확보되지 않아 한국과 세계경제의 현재 상태를 판단할 수 없습니다. 아래 경제적 설명은 조건부 해석의 틀이며, 현재 발생한 사실이나 전망을 뜻하지 않습니다. 숫자를 생성하거나 과거 자료를 최신 자료로 대체하지 않았습니다.']
    else:
        for sid in ['wb:NY.GDP.MKTP.KD.ZG','wb:FP.CPI.TOTL.ZG','wb:SL.UEM.1524.ZS']:
            subset=df[(df.series_id==sid)&(df.country=='KOR')]
            if not subset.empty:
                row=latest(subset).iloc[0]
                v='결측' if pd.isna(row.value) else f'{row.value:,.2f} {row.unit}'
                report.append(f'- **확인된 사실:** 한국 {row["name"]}의 저장된 최신 기준기간은 {row.period}, 값은 {v}입니다. [{row.source}]({row.source_url}).')
        report += ['연간 통계의 구조적 추세와 최근 월·분기 경기 신호는 다릅니다. 아래 관측기간을 기준으로 읽어야 하며 최신 공식 발표를 모두 반영했다고 보장하지 않습니다.']
    for title,category in CHAPTERS:
        report.append('## '+title)
        if category is None:
            state,note=regime(df)
            report.extend([f'**경기국면: {state}.** {note}', '성장률이 양수라는 사실만으로 모든 계층의 삶이 개선되었다고 결론 내리지 않습니다. 임금근로자·자영업자·청년·고령층·차입자·자산보유자의 결과는 서로 다를 수 있습니다.'])
            continue
        sub=df[df.category==category] if not df.empty else df
        rows=latest(sub)
        report += ['### ① 핵심 요약', f'이 영역에서 확보한 비결측 관측값은 {len(sub.dropna(subset=["value"])) if not sub.empty else 0}개입니다. 아래 수치와 추가 검증 항목을 함께 확인하세요.', '### ② 주요 경제지표']
        if not rows.empty:
            display=rows[['name','country','period','value','unit','source','release_date','retrieved_at']].copy()
            display.country=display.country.map(COUNTRIES).fillna(display.country)
            display.columns=['지표','국가','기준기간','값','단위','출처','발표일','수집시각(UTC)']
            report.append(table(display))
        else:
            report.append('자료 미확보 — 추가 검증 필요.')
        report.append('### ③ 시계열 그래프 및 기간별 추세')
        for sid,g in sub.groupby('series_id') if not sub.empty else []:
            if g.value.notna().sum()<2:
                continue
            image=hashlib.sha256(sid.encode()).hexdigest()[:12]+'.png'
            save_chart(g,target/'charts'/image)
            report.append(f'![{g.iloc[0]["name"]}](charts/{image})')
            report.append(f'출처: [{g.iloc[0].source}]({g.iloc[0].source_url}); 단위: {g.iloc[0].unit}; 기준기간: {g.period.min()}~{g.period.max()}; 수집시각: {g.retrieved_at.max()}; {g.iloc[0].note}')
            kr=g[g.country=='KOR'].sort_values('period')
            if not kr.empty:
                for years in (1,3,5,10):
                    last=kr.iloc[-1]
                    freq={'A':'Y'}.get(last.frequency,last.frequency)
                    p=pd.Period(last.period,freq=freq)
                    if last.frequency not in ('A','M','Q'):
                        continue
                    before=str(p-years*{'A':1,'M':12,'Q':4}[last.frequency])
                    old=kr[kr.period==before]
                    if not old.empty and pd.notna(last.value) and pd.notna(old.iloc[0].value):
                        delta=last.value-old.iloc[0].value
                        unit='%p' if last.unit=='%' else last.unit
                        report.append(f'- 한국 {years}년 비교 ({before}→{last.period}): {delta:+,.3f} {unit}. 원 단위 차이이며 원인·인과 판정이 아닙니다.')
                    else:
                        report.append(f'- 한국 {years}년 비교: 동일 기준기간 자료 부족.')
        interpretation,positive,negative,alternative=INTERPRETATIONS[category]
        report += ['### ④ 경제학적 해석 (조건부)',interpretation,'### ⑤ 긍정적 요인 (확인할 조건)',positive,'### ⑥ 부정적 요인 (확인할 조건)',negative,'### ⑦ 반론 및 대안적 해석',alternative,'### ⑧ 향후 관찰해야 할 변수',GAPS[category][0]+'. '+GAPS[category][1]+'. **추가 검증 필요.**','### ⑨ 자료 출처']
        for m in store.catalog():
            if m['category']==category:
                report.append(f'- [{m["name"]} — {m["source"]}]({m["source_url"]}) · {m["adjustment"]} · {m["price_basis"]}. 연결 주소는 출처 안내이며, 수집 성공 여부는 부록 참조.')
    report += ['## 향후 경제 전망','다음은 관측자료로 검증해야 하는 조건부 시나리오입니다. 수치·확률을 부여하지 않으며 가장 개연성 높은 경로도 자료 검증 전에는 확정하지 않습니다.',table(pd.DataFrame(SCENARIOS)),table(pd.DataFrame([{'기간':k,'판별할 변화':v} for k,v in HORIZONS.items()])),
               '## 주요 위험요인','현재 위험 수준은 자료 미확보 항목에 대해 판정하지 않습니다. 아래 신호가 실제로 관측되었는지는 원자료로 확인해야 합니다.',table(pd.DataFrame(RISKS,columns=['위험','발생 원인','완화 요인','관찰 지표','경제 영향'])),
               '## 종합 결론','확인된 관측값, 경제학적 해석, 조건부 미래 전망을 구분했습니다. 성장·분배·금융안정을 종합한 현재 진단은 미확보 국내 세부 통계와 최신 발표자료 검증 후 갱신해야 합니다.',
               '## 참고문헌 및 데이터 출처',table(cov),
               '### 계산·자료 관리 방법','변화율은 같은 달력 기준기간을 비교하며 결측을 보간하지 않습니다. 비율의 차이는 %p로 표시합니다. 국가 합계를 합산하거나 서로 다른 기준연도 지수를 같은 수준으로 비교하지 않습니다. 발표일이 제공되지 않으면 미확인으로 유지하고 수집시각과 공급자 갱신일을 별도 저장합니다. 원문·개정 이력과 이번 보고서의 정확한 수치는 evidence.csv 및 SQLite에 있습니다.',
               f'스냅샷 실행 ID: {cutoff}. 근거 CSV SHA-256: {hashlib.sha256(evidence).hexdigest()}.',
               '### 수집 이력',table(store.attempts()[['series_id','status','message','rows']] if not store.attempts().empty else pd.DataFrame())]
    text='\n\n'.join(report)+'\n'
    (target/'report.md').write_text(text,encoding='utf-8')
    if previous:
        diff=''.join(difflib.unified_diff(previous[-1].read_text().splitlines(True),text.splitlines(True),fromfile=str(previous[-1]),tofile=str(target/'report.md')))
        (target/'changes.diff').write_text(diff,encoding='utf-8')
    (target/'manifest.json').write_text(json.dumps({'run_id':cutoff,'generated_at':stamp,'evidence_sha256':hashlib.sha256(evidence).hexdigest(),'has_observations':complete,'report':'report.md'},ensure_ascii=False,indent=2))
    return target/'report.md'
