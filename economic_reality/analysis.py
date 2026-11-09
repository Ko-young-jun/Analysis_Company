from datetime import date

import pandas as pd
import plotly.express as px

from .catalog import COUNTRIES, GAPS


def freq_code(frequency):
    return {'A':'Y'}.get(frequency,frequency)


def changes(df, frequency):
    """달력 기준 이전기 및 전년비. 결측을 건너뛰거나 메우지 않는다."""
    if df.empty:
        return pd.DataFrame(columns=['period','value','change','yoy'])
    x = df[['period','value']].copy()
    x.index = pd.PeriodIndex(x.period, freq=freq_code(frequency))
    if x.index.duplicated().any():
        raise ValueError('단일 시리즈·국가를 선택하세요')
    x = x.reindex(pd.period_range(x.index.min(),x.index.max(),freq=freq_code(frequency)))
    x['period'] = x.index.astype(str)
    x['value'] = pd.to_numeric(x.value,errors='raise')
    x['change'] = x.value.diff()
    periods = {'A':1,'Q':4,'M':12}.get(frequency)
    if periods:
        previous = x.value.shift(periods)
        x['yoy'] = (x.value / previous.where(previous > 0) - 1) * 100
    else:
        x['yoy'] = float('nan')  # 윤년·거래일 처리 없이 일별 전년비를 산출하지 않는다.
    return x.reset_index(drop=True)


def indexed(df, base):
    x = df.copy()
    v = x.loc[x.period == base,'value']
    if len(v) != 1 or pd.isna(v.iloc[0]) or v.iloc[0] <= 0:
        raise ValueError('공통 기준기간에 양의 관측값이 있어야 합니다')
    x['value'] = x.value / v.iloc[0] * 100
    return x


def relationship(left, right, frequency, lag=0):
    """X(t-lag) 변화와 Y(t) 변화의 동행성. 추세 상관을 줄이기 위해 1차 차분."""
    x=changes(left,frequency).set_index('period')['change']
    y=changes(right,frequency).set_index('period')['change']
    x.index=pd.PeriodIndex(x.index,freq=freq_code(frequency)) + lag
    y.index=pd.PeriodIndex(y.index,freq=freq_code(frequency))
    pairs=pd.concat([x.rename('x'),y.rename('y')],axis=1).dropna()
    corr = None
    if len(pairs)>=12 and pairs.x.std()>0 and pairs.y.std()>0:
        corr=float(pairs.x.corr(pairs.y))
    return {'correlation':corr,'n':len(pairs),'pairs':pairs.reset_index(names='period')}


def latest(df):
    if df.empty:
        return df.copy()
    # 최신 공표가 결측이면 과거 값을 최신으로 둔갑시키지 않는다.
    return df.sort_values('period').groupby(['series_id','country'],as_index=False).tail(1)


def coverage(store):
    df = store.frame()
    attempts = store.attempts()
    rows=[]
    for m in store.catalog():
        available = df[df.series_id==m['id']] if not df.empty else df
        nonnull=available.dropna(subset=['value']) if not available.empty else available
        history=attempts[attempts.series_id==m['id']] if not attempts.empty else attempts
        status=history.iloc[0]['status'] if not history.empty else 'unrun'
        rows.append({'지표':m['name'],'영역':m['category'],'출처':m['source'],'상태':{'success':'수집 성공','failed':'수집 실패','skipped':'미시도 (출처 차단)','empty':'응답에 수치 없음','unrun':'미실행'}.get(status,status),'관측 수':len(nonnull),'최신 수치 기간':nonnull.period.max() if not nonnull.empty else '없음','지표 ID':m['id']})
    return pd.DataFrame(rows)


def alerts(df, threshold=2.0):
    rows=[]
    if df.empty:
        return pd.DataFrame()
    for (sid,country),group in df.groupby(['series_id','country']):
        m=group.iloc[-1]
        x=changes(group,m.frequency)
        if len(x)<9:
            continue
        # 최근 변화는 이전 변화들로만 표준화한다. 경제 위험의 확률이 아니다.
        prior=x.change.iloc[:-1].dropna().tail(36)
        v=x.change.iloc[-1]
        if len(prior)<8 or pd.isna(v) or prior.std()==0:
            continue
        z=(v-prior.mean())/prior.std()
        if abs(z)>=threshold:
            rows.append({'지표':m['name'],'국가':COUNTRIES.get(country,country),'기간':x.iloc[-1].period,'변화':v,'단위':m.unit,'표준화 편차':z,'해석':'과거 변화와 차이가 큼; 개정·기저효과·공표주기 확인 필요'})
    return pd.DataFrame(rows)


def chart(df, title=None):
    m=df.iloc[0]
    pieces=[]
    for country,g in df.groupby('country'):
        x=changes(g,m.frequency)
        x['국가']=COUNTRIES.get(country,country)
        x['기준기간']=x.period
        x['날짜']=pd.PeriodIndex(x.period,freq=freq_code(m.frequency)).to_timestamp()
        pieces.append(x)
    data=pd.concat(pieces,ignore_index=True)
    fig=px.line(data,x='날짜',y='value',color='국가',hover_data=['기준기간'],labels={'value':m.unit,'날짜':'기준기간'},title=title or m['name'],template='plotly_white')
    fig.update_traces(connectgaps=False)
    fig.update_layout(legend_title_text='',font={'family':'sans-serif'},margin=dict(l=20,r=20,t=60,b=30))
    return fig


def regime(df):
    return ('판정 유보', '한국의 최신 분기 GDP·월별 생산·소비·고용을 함께 검증하기 전에는 경기국면을 판정하지 않습니다. 연간 WDI와 미국 지표만으로 한국의 현재 국면을 확정할 수 없습니다.')


SCENARIOS = [
{'시나리오':'낙관','발생 조건':'실질소득·내수·수출이 동반 개선되고 금융 스트레스가 완화될 경우','성장·고용':'성장 확산과 채용 개선 가능. 수출의 고용 전이는 산업별 확인 필요','물가·금리':'공급 개선은 물가를 완화하지만 수요 회복은 반대 압력. 금리 인하를 자동 가정하지 않음','산업':'반도체 회복이 설비투자·서비스 수요로 확산되는지 확인','검증 지표':'실질임금, 소매판매, 수출 물량, 산업별 고용, 연체율'},
{'시나리오':'기준 (조건부)','발생 조건':'확인된 최근 추세가 유지되고 새로운 대외 충격이 없을 경우. 자료 확보 전에는 가장 개연성 높은 경로로 확정하지 않음','성장·고용':'수출·내수 간 차별화와 산업별 채용 격차가 지속될 가능성을 점검','물가·금리':'물가·성장·금융안정 간 제약에 따라 경로가 달라짐','산업':'수출 주도 산업과 내수 서비스업의 분화를 점검','검증 지표':'분기 GDP 기여도, 근원물가, 취업자 증감, 민간소비'},
{'시나리오':'비관','발생 조건':'교역 둔화, 에너지·환율 충격, 부채 부실 중 주요 위험이 현실화될 경우','성장·고용':'투자·소비 위축과 신규 채용 둔화 가능','물가·금리':'공급 충격이면 물가 상승과 성장 둔화가 공존; 수요 충격이면 물가 하락 가능','산업':'PF·건설, 고부채 내수업, 대외 수요 민감 제조업의 손실 확대 여부','검증 지표':'연체율, 신용 스프레드, 수출, 유가, 환율, 청년고용'},
]
HORIZONS = {'3개월':'월별 물가·생산·고용과 금리·환율 변화', '6개월':'수출 주문·재고와 투자·소비로의 파급', '1년':'실질소득·부채상환·기업이익과 채용의 연결', '3년':'설비투자·산업 재편·노동 이동과 생산성', '5년':'인구구조·자본축적·AI 확산과 분배 구조'}
RISKS = [
('경기침체','소비·투자·수출 동반 둔화','실질소득 회복·재정 여력','GDP, 산업생산, 소비, 고용','기업 매출·가계 소득 동반 위축'),
('물가 재상승','에너지·환율·공급 제약','공급 정상화·수요 안정','근원·수입물가, 유가, 환율','실질구매력 감소·금리 인하 제약'),
('금융불안·글로벌 충격','신용경색·해외 자금 유출','은행 자본·유동성 완충','신용 스프레드, 자본비율, 환율','차입비용 상승·투자 감소'),
('가계부채 부실','소득 대비 원리금 상환 확대','고용 유지·채무 조정','가계 연체율, DSR, 처분가능소득','소비 위축·금융기관 손실'),
('부동산·PF 불안','미분양·차환 실패','사업성 개선·건전한 자본','거래량, 미분양, PF 연체율','건설·지역 고용과 금융기관 파급'),
('수출 둔화·경쟁력 약화','해외 수요·통상 규제·비용 증가','시장 다변화·생산성 개선','수출 물량, 점유율, 산업별 생산성','설비투자·제조업 고용 위축'),
('고용 악화','신규 채용 감소·기술 변화와 숙련 불일치','노동 이동·재훈련·서비스 수요','청년고용, 쉬었음, 신규 채용','경력 축적 지연·소득 격차 확대'),
]
