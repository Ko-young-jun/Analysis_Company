"""공식 공급자 시리즈와 요구사항의 추적 가능한 카탈로그."""
COUNTRIES = {'KOR':'대한민국','USA':'미국','CHN':'중국','JPN':'일본','EUU':'유럽연합','EMU':'유로지역','WLD':'세계'}
CATEGORIES = ['한국 거시경제','물가와 실질구매력','고용과 노동시장','금융시장과 부채','부동산과 자산시장','국제경제','산업구조와 미래경제','불평등과 구조적 위험']
# ID, 한국어 이름, 단위, 영역, 가격 기준
WB = [
('NY.GDP.MKTP.KD.ZG','실질 GDP 성장률','%',0,'실질'),
('NY.GDP.MKTP.CD','명목 GDP','미 달러',0,'명목'),
('NY.GDP.MKTP.KD','실질 GDP','2015년 불변 미 달러',0,'실질'),
('NE.CON.PRVT.KD.ZG','가계·비영리기관 소비 증가율','%',0,'실질'),
('NE.CON.GOVT.KD.ZG','정부 최종소비 증가율','%',0,'실질'),
('NE.GDI.FTOT.KD.ZG','총고정자본형성 증가율','%',0,'실질'),
('FP.CPI.TOTL.ZG','소비자물가 상승률','%',1,'해당 없음'),
('FP.CPI.TOTL','소비자물가지수','2010=100',1,'해당 없음'),
('SL.EMP.TOTL.SP.ZS','고용률 (15세 이상, ILO 추정)','%',2,'해당 없음'),
('SL.UEM.TOTL.ZS','실업률 (ILO 추정)','%',2,'해당 없음'),
('SL.UEM.1524.ZS','청년실업률 (15~24세, ILO 추정)','%',2,'해당 없음'),
('SL.EMP.1524.SP.ZS','청년고용률 (15~24세, ILO 추정)','%',2,'해당 없음'),
('SL.TLF.CACT.ZS','경제활동참가율 (15세 이상, ILO 추정)','%',2,'해당 없음'),
('SL.EMP.SELF.ZS','자영업자 비중 (ILO 추정)','%',2,'해당 없음'),
('FS.AST.PRVT.GD.ZS','민간부문 국내신용 / GDP','%',3,'해당 없음'),
('FB.AST.NPER.ZS','은행 부실채권 비율','%',3,'해당 없음'),
('FM.LBL.BMNY.GD.ZS','광의통화 / GDP','%',3,'해당 없음'),
('CM.MKT.LCAP.GD.ZS','상장주식 시가총액 / GDP','%',4,'해당 없음'),
('NE.EXP.GNFS.KD.ZG','재화·서비스 수출 증가율','%',5,'실질'),
('NE.IMP.GNFS.KD.ZG','재화·서비스 수입 증가율','%',5,'실질'),
('PA.NUS.FCRF','공식 환율 (연평균)','현지통화/미 달러',5,'해당 없음'),
('GC.DOD.TOTL.GD.ZS','중앙정부 부채 / GDP','%',5,'해당 없음'),
('NV.IND.MANF.KD.ZG','제조업 부가가치 증가율','%',6,'실질'),
('NV.SRV.TOTL.KD.ZG','서비스업 부가가치 증가율','%',6,'실질'),
('SL.IND.EMPL.ZS','산업부문 고용 비중 (ILO 추정)','%',6,'해당 없음'),
('SL.SRV.EMPL.ZS','서비스업 고용 비중 (ILO 추정)','%',6,'해당 없음'),
('SL.GDP.PCAP.EM.KD','취업자당 GDP (PPP)','2021년 PPP 불변 국제 달러',6,'실질'),
('SI.POV.GINI','지니계수','0~100',7,'해당 없음'),
('SI.DST.05TH.20','상위 20% 소득 점유율','%',7,'해당 없음'),
('SI.DST.FRST.20','하위 20% 소득 점유율','%',7,'해당 없음'),
('SP.POP.65UP.TO.ZS','65세 이상 인구 비중','%',7,'해당 없음'),
('SP.POP.1564.TO.ZS','15~64세 인구 비중','%',7,'해당 없음'),
('SP.DYN.TFRT.IN','합계출산율','여성 1명당 출생아 수',7,'해당 없음'),
]
FRED = [
('FEDFUNDS','미국 실효 연방기금금리','%',3,'M','USA','비계절조정'),
('UNRATE','미국 실업률','%',2,'M','USA','계절조정'),
('CPIAUCSL','미국 소비자물가지수','1982~1984=100',1,'M','USA','계절조정'),
('CPILFESL','미국 근원 소비자물가지수','1982~1984=100',1,'M','USA','계절조정'),
('DGS10','미국 국채 10년 금리','%',3,'D','USA','비계절조정'),
('DGS2','미국 국채 2년 금리','%',3,'D','USA','비계절조정'),
('T10Y2Y','미국 국채 10년–2년 금리차','%p',3,'D','USA','비계절조정'),
('DCOILWTICO','WTI 현물유가','미 달러/배럴',5,'D','USA','비계절조정'),
('DEXKOUS','원/미 달러 환율','원/미 달러',5,'D','KOR','비계절조정'),
]


def catalog():
    out = []
    for code,name,unit,cat,price in WB:
        out.append(dict(id='wb:'+code, code=code, name=name, unit=unit, category=CATEGORIES[cat], frequency='A', source='World Bank WDI', source_url=f'https://data.worldbank.org/indicator/{code}', adjustment='연간 자료 · 계절조정 해당 없음', price_basis=price, note='연간 통계는 단기 경기 판정에 불충분합니다. 국가별 정의·자료연도 차이와 개정에 유의하세요. ILO 추정 청년은 15~24세로 한국 공식 청년통계와 다릅니다. 중앙정부 부채는 일반정부 부채가 아닙니다. 민간신용은 가계부채와 다릅니다.', adapter='worldbank'))
    for code,name,unit,cat,freq,country,adjustment in FRED:
        out.append(dict(id='fred:'+code, code=code, name=name, unit=unit, category=CATEGORIES[cat], frequency=freq, country=country, source='FRED (원 생산기관은 시리즈 원문 참조)', source_url=f'https://fred.stlouisfed.org/series/{code}', adjustment=adjustment, price_basis='해당 없음', note='공개 CSV의 발표일·잠정/확정 구분은 미제공입니다. 일별 결측은 주말·휴일과 공표 누락을 포함합니다. 실효 연방기금금리는 정책금리 목표범위와 다릅니다.', adapter='fred'))
    return out

# 공개 연간 통계로 대체했다고 주장하지 않는 미확보 요구사항.
GAPS = {
CATEGORIES[0]: ('잠재성장률, 설비투자, 건설투자, 산업생산, 경기선행·동행지수, 분기 GDP 성장기여도', 'ECOS·KOSIS의 공식 세부 시계열 필요'),
CATEGORIES[1]: ('한국 근원·생산자·생활물가, 식품·에너지, 명목·실질임금, 가계 실질소득·소비지출, 소득계층별 구매력', '동일 모집단·주기의 임금·가계조사 및 물가 자료 필요'),
CATEGORIES[2]: ('비경제활동·쉬었음, 정규·비정규직, 산업별 취업자 증감, 기업규모별 고용, 신규·경력 채용, AI 고용 영향', 'KOSIS·고용노동부 자료 필요. AI 영향의 인과 추론은 별도 설계 필요'),
CATEGORIES[3]: ('한국 기준·대출·국고채 금리, 가계·기업부채, 원리금상환 부담, 연체율, PF 및 금융기관 건전성', 'ECOS·BIS·금감원 원자료 필요. 민간신용을 가계부채로 대체하지 않음'),
CATEGORIES[4]: ('주택·전세 가격, 거래량, 지역 격차, 주거비, 주택담보대출, 코스피·코스닥, 기업이익·PER·PBR', '한국부동산원·국토교통부·KRX 공식 자료와 이용 조건 확인 필요'),
CATEGORIES[5]: ('국가별 정책금리, 제조업 PMI, 일반정부 부채, 세계 교역량', '중앙은행·IMF·WTO 자료 필요. PMI는 이용권 제약 가능'),
CATEGORIES[6]: ('반도체·AI·자동차/전기차·이차전지·조선·철강·석유화학·바이오·금융의 생산·수출·투자·고용', '산업분류 매핑 및 관세청·KOSIS 세부 자료 필요'),
CATEGORIES[7]: ('자산 불평등, 세대별 자산, 청년 주거부담, 지역경제 격차', '가계금융복지·주거실태·지역통계 필요. 소득지니로 자산격차를 대체하지 않음'),
}
