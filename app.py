"""실행: python -m streamlit run app.py"""
import io
import json
import os
from pathlib import Path
import zipfile

import pandas as pd
import plotly.express as px
import streamlit as st

from economic_reality.analysis import (HORIZONS, RISKS, SCENARIOS, alerts, changes, chart,
                                       coverage, indexed, latest, regime, relationship)
from economic_reality.catalog import CATEGORIES, COUNTRIES, GAPS, catalog
from economic_reality.report import generate
from economic_reality.sources import update
from economic_reality.store import Store

st.set_page_config(page_title='경제의 실체',page_icon='📊',layout='wide')
store=Store(os.environ.get('ECONOMIC_DATA_DIR','data'))
report_root=Path(os.environ.get('ECONOMIC_REPORT_DIR','reports'))
for meta in catalog(): store.register(meta)

st.title('경제의 실체')
st.caption('성장 · 구매력 · 고용 · 금융 · 분배를 공식 통계로 확인합니다.')
with st.sidebar:
    st.header('분석 범위')
    page=st.radio('화면',['경제 현황','지표 탐색','국가 비교','지표 관계','산업과 청년고용','위험과 시나리오','데이터·갱신','보고서'])
    country=st.selectbox('국가·지역',list(COUNTRIES),format_func=COUNTRIES.get)
    years=st.select_slider('최근 기간',options=[1,3,5,10],value=10)
    runs=store.runs()
    options=[None]+(runs.id.tolist() if not runs.empty else [])
    as_of=st.selectbox('수집 이력 시점',options,format_func=lambda x:'현재 저장된 최신 버전' if x is None else f'수집 실행 {x}')
    st.caption('관측 기준기간과 수집시각은 다릅니다. 과거 시점은 이 시스템이 수집한 이후 이력만 제공합니다.')

df=store.frame(as_of=as_of)
if not df.empty:
    cutoff=pd.Timestamp.now(tz='Asia/Seoul').tz_localize(None)-pd.DateOffset(years=years)
    period_ends=pd.Series(index=df.index,dtype='datetime64[ns]')
    for frequency,g in df.groupby('frequency'):
        period_ends.loc[g.index]=pd.PeriodIndex(g.period,freq={'A':'Y'}.get(frequency,frequency)).end_time
    df=df[period_ends>=cutoff]
valid=df.dropna(subset=['value']) if not df.empty else df
if valid.empty:
    st.warning('선택 범위에 확인된 실제 통계가 없습니다. 경제 수치·차트·경기 판단을 생성하지 않습니다. 데이터·갱신 화면에서 수집 상태를 확인하세요.')
else:
    st.caption(f'선택 범위: {len(valid):,}개 관측 · {valid.series_id.nunique()}개 지표. 각 지표의 최신 기준기간을 확인하세요.')


def display_series(group):
    if group.empty or group.value.notna().sum()==0:
        st.info('이 조건의 관측값이 없습니다.')
        return
    m=group.iloc[0]
    st.plotly_chart(chart(group),width='stretch')
    st.caption(f'단위: {m.unit} · 기준기간: {group.period.min()}~{group.period.max()} · 최종 수집: {group.retrieved_at.max()} · {m.adjustment} · {m.price_basis}')
    st.markdown(f'출처: [{m.source}]({m.source_url})')
    st.caption(m.note)
    with st.expander('수치·발표일·개정 상태 확인'):
        st.dataframe(group[['country','period','value','unit','release_date','status','provider_updated','retrieved_at']].rename(columns={'country':'국가 코드','period':'기준기간','value':'값','unit':'단위','release_date':'발표일','status':'공표 상태','provider_updated':'공급자 갱신일','retrieved_at':'수집시각'}),hide_index=True)
        st.download_button('표시된 원자료 CSV',group.to_csv(index=False).encode('utf-8-sig'),file_name='경제지표.csv',mime='text/csv',key='csv-'+m.series_id)


if page=='경제 현황':
    st.header(f'{COUNTRIES[country]} 경제 현황')
    if country=='KOR':
        state,note=regime(df)
        st.info(f'경기국면: {state}. {note}')
    metrics=['wb:NY.GDP.MKTP.KD.ZG','wb:FP.CPI.TOTL.ZG','wb:SL.UEM.TOTL.ZS','wb:SL.UEM.1524.ZS']
    for col,sid in zip(st.columns(4),metrics):
        m=next(m for m in catalog() if m['id']==sid)
        sub=df[(df.series_id==sid)&(df.country==country)] if not df.empty else df
        with col:
            row=latest(sub)
            st.metric(m['name'],'미확보' if row.empty or pd.isna(row.iloc[0].value) else f'{row.iloc[0].value:.2f}%')
            if not row.empty: st.caption('기준기간 '+row.iloc[0].period)
    category=st.selectbox('분석 영역',CATEGORIES)
    if not df.empty:
        sub=df[(df.category==category)&(df.country==country)]
        for sid,g in sub.groupby('series_id'): display_series(g)
    with st.expander('이 영역의 미확보 자료',expanded=valid.empty):
        st.write(GAPS[category][0])
        st.caption(GAPS[category][1])

elif page in ('지표 탐색','국가 비교'):
    metas=store.catalog()
    sid=st.selectbox('지표',[m['id'] for m in metas],format_func=lambda s:next(m['name'] for m in metas if m['id']==s))
    selected=st.multiselect('비교 국가·지역',list(COUNTRIES),default=['KOR','USA','JPN'] if page=='국가 비교' else [country],format_func=COUNTRIES.get)
    if not df.empty:
        sub=df[(df.series_id==sid)&df.country.isin(selected)].copy()
        if not sub.empty:
            if st.checkbox('공통 기준기간을 100으로 지수화'):
                sets=[set(sub[(sub.country==c)&sub.value.notna()].period) for c in selected]
                common=sorted(set.intersection(*sets)) if sets else []
                if not common:
                    st.info('공통 관측기간이 없어 지수화할 수 없습니다.')
                    sub=sub.iloc[0:0]
                else:
                    base=st.selectbox('기준기간',common)
                    try:
                        sub=pd.concat([indexed(g,base) for _,g in sub.groupby('country')])
                        sub['unit']=f'{base}=100'
                        st.caption('수준 차이가 아닌 기준기간 이후 상대 변화입니다. 성장률·금리 같은 비율 지표는 원 단위 비교를 권장합니다.')
                    except ValueError as exc:
                        st.warning(str(exc))
                        sub=sub.iloc[0:0]
            display_series(sub)
        else: st.info('선택한 지표·국가의 자료가 없습니다.')
    st.caption('국가별 최신 연도가 다를 수 있습니다. EU와 유로지역은 중복 집계이므로 합산하지 않습니다.')

elif page=='지표 관계':
    st.header('시차를 둔 지표 변화 비교')
    st.write('동일 주기·계절조정 기준의 두 지표를 선택합니다. 추세에 따른 허위 상관을 줄이기 위해 원 단위의 1차 차분을 비교합니다.')
    if not valid.empty:
        subset=df[df.country==country]
        ids=subset.series_id.unique().tolist()
        names={m['id']:m['name'] for m in store.catalog()}
        if len(ids)>=2:
            left=st.selectbox('선행 지표 X',ids,format_func=names.get)
            right=st.selectbox('후행 지표 Y',ids,index=1,format_func=names.get)
            lag=st.slider('X의 선행 기간 수',0,12,0)
            x=subset[subset.series_id==left]; y=subset[subset.series_id==right]
            if x.iloc[0].frequency!=y.iloc[0].frequency or x.iloc[0].adjustment!=y.iloc[0].adjustment:
                st.warning('주기 또는 계절조정 기준이 달라 자동 상관을 계산하지 않습니다.')
            else:
                result=relationship(x,y,x.iloc[0].frequency,lag)
                st.metric('변화의 상관계수','산출 불가' if result['correlation'] is None else f'{result["correlation"]:.3f}')
                st.caption(f'정확히 일치한 기간 {result["n"]}개. 최소 12쌍·변동성 필요. X(t−시차)와 Y(t)를 비교합니다.')
                pairs=result['pairs'].copy(); pairs['period']=pairs.period.astype(str)
                if not pairs.empty:
                    st.plotly_chart(px.scatter(pairs,x='x',y='y',hover_data=['period'],labels={'x':names[left]+' 변화 ('+x.iloc[0].unit+')','y':names[right]+' 변화 ('+y.iloc[0].unit+')'},template='plotly_white'),width='stretch')
    st.info('상관은 인과효과가 아닙니다. 공통 경기충격·정책 대응·기저효과·시차 선택에 따른 결과 변화를 함께 검토해야 합니다.')
    st.subheader('실질임금과 물가')
    st.write('실질임금·가계 실질소득 자료는 아직 확보되지 않았습니다. 명목임금과 물가의 동일 주기·모집단 자료 확보 후 계산해야 하며, GDP를 임금의 대리값으로 사용하지 않습니다.')

elif page=='산업과 청년고용':
    st.header('성장이 고용으로 이어지는가')
    section=st.radio('분석 대상',['청년고용','산업구조'],horizontal=True)
    category=CATEGORIES[2] if section=='청년고용' else CATEGORIES[6]
    if not df.empty:
        subset=df[(df.category==category)&(df.country==country)]
        for _,g in subset.groupby('series_id'): display_series(g)
    if section=='청년고용':
        st.info('국제 비교의 청년은 15~24세입니다. 실업률만으로 쉬었음·구직 포기를 판단할 수 없으며 고용률·참가율을 함께 확인해야 합니다.')
    else:
        st.info('제조업·서비스업 합계는 개별 산업의 성과를 설명하지 않습니다. 세부 산업의 생산·수출·투자·고용 연결은 아래 자료 확보 후 가능합니다.')
    st.write(GAPS[category][0]); st.caption(GAPS[category][1])

elif page=='위험과 시나리오':
    st.header('변화 감지와 위험 점검')
    found=alerts(df)
    if found.empty: st.info('선택 범위에서 산출 가능한 큰 변화 신호가 없습니다. 자료 부족도 포함하며 경제가 안전하다는 뜻은 아닙니다.')
    else: st.dataframe(found,hide_index=True)
    st.caption('감지 기준: 최신 원 단위 변화가 이전 최대 36개 변화 평균에서 표준편차 2배 이상 벗어남. 최소 과거 변화 8개. 위험 확률이나 위기 판정이 아닙니다.')
    st.dataframe(pd.DataFrame(RISKS,columns=['위험','원인','완화 요인','관찰 지표','영향']),hide_index=True)
    st.subheader('조건부 미래 시나리오')
    st.warning('현재 관측으로 확정한 전망이 아닙니다. 근거 없는 수치·확률은 부여하지 않습니다.')
    horizon=st.selectbox('전망 기간',list(HORIZONS))
    st.write(HORIZONS[horizon])
    for scenario in SCENARIOS:
        with st.expander(scenario['시나리오'],expanded=True):
            for key,value in scenario.items():
                if key!='시나리오': st.markdown(f'**{key}:** {value}')

elif page=='데이터·갱신':
    st.header('출처와 수집 상태')
    st.caption('수집 상태는 현재 DB 전체 기준입니다. 왼쪽의 과거 시점·기간 필터는 적용되지 않습니다.')
    source=st.selectbox('수집 출처',['all','worldbank','fred'],format_func=lambda x:{'all':'모든 출처','worldbank':'World Bank WDI','fred':'FRED'}[x])
    if st.button('공식 통계 갱신',type='primary'):
        with st.spinner('공식 자료 확인 중…'):
            run,result=update(store,source)
        ok=sum(s=='success' for _,s,_ in result)
        if ok==len(result): st.success(f'실행 {run}: {ok}개 지표 수집 완료')
        else: st.warning(f'실행 {run}: {ok}/{len(result)}개 성공. 실패·미시도 내역을 확인하세요.')
    st.dataframe(coverage(store),hide_index=True,width='stretch')
    with st.expander('요구사항별 미확보 자료',expanded=True):
        st.dataframe(pd.DataFrame([{'영역':k,'미확보 항목':v[0],'필요 자료':v[1]} for k,v in GAPS.items()]),hide_index=True)
    with st.expander('수집 로그'):
        st.dataframe(store.attempts(),hide_index=True)
    with st.expander('개정 이력'):
        ids=[m['id'] for m in store.catalog()]
        rev_id=st.selectbox('이력 지표',ids)
        st.dataframe(store.history(rev_id,country),hide_index=True)
    if not df.empty:
        st.download_button('선택 범위 데이터 CSV',df.to_csv(index=False).encode('utf-8-sig'),'경제의실체.csv','text/csv')
    st.markdown('공식 CSV 수동 가져오기는 README의 `import-csv` 절차를 사용할 수 있습니다. 인증정보는 화면이나 로그에 입력하지 않습니다.')

elif page=='보고서':
    st.header('한국어 보고서와 이전 버전 비교')
    st.caption('보고서는 현재 DB 전체의 최신 버전으로 생성됩니다. 화면의 국가·기간·과거 시점 필터는 적용되지 않습니다.')
    if st.button('현재 데이터로 보고서 생성',type='primary'):
        with st.spinner('표·그래프·출처·이력 생성 중…'):
            path=generate(store,report_root)
        st.success('보고서를 저장했습니다. 데이터가 없으면 수집 상태 보고서로 표시됩니다.')
    reports=sorted(report_root.glob('*/report.md'),reverse=True)
    if reports:
        chosen=st.selectbox('보고서 버전',reports,format_func=lambda p:p.parent.name)
        text=chosen.read_text(encoding='utf-8')
        st.download_button('보고서 Markdown 다운로드',text,'경제의실체.md','text/markdown')
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as bundle:
            for path in chosen.parent.rglob('*'):
                if path.is_file(): bundle.write(path,path.relative_to(chosen.parent))
        st.download_button('보고서·그래프·근거자료 묶음',buffer.getvalue(),'경제의실체_보고서.zip','application/zip')
        if (chosen.parent/'changes.diff').exists():
            with st.expander('이전 보고서와 차이'): st.code((chosen.parent/'changes.diff').read_text(),language='diff')
        # Markdown의 로컬 이미지가 실제 화면에 표시되도록 분리 렌더링한다.
        import re
        parts=re.split(r'(!\[[^\]]*\]\(charts/[^)]+\))',text)
        for part in parts:
            match=re.fullmatch(r'!\[([^\]]*)\]\((charts/[^)]+)\)',part)
            if match: st.image(str(chosen.parent/match[2]),caption=match[1])
            else: st.markdown(part)
    else: st.info('아직 생성된 보고서가 없습니다.')
