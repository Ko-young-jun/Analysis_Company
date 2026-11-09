import json
import pytest
from economic_reality.sources import update, SourceError
from economic_reality.store import Store
from economic_reality.report import generate
from economic_reality.analysis import coverage


def test_pipeline_and_report_use_exact_observations(tmp_path):
    # 공급자 형식의 합성 테스트 자료. 운영 수집 결과로 사용하지 않는다.
    def fetch(url):
        return json.dumps([{'pages':1,'lastupdated':'2025-01-01'},[{'indicator':{'id':'NY.GDP.MKTP.KD.ZG'},'countryiso3code':'KOR','date':str(y),'value':v} for y,v in [(2020,-1.0),(2021,4.0),(2022,2.0)]]]).encode()
    store=Store(tmp_path/'data')
    run,result=update(store,only=['wb:NY.GDP.MKTP.KD.ZG'],fetch=fetch)
    assert result[0][1:] == ('success',3)
    report=generate(store,tmp_path/'reports')
    text=report.read_text()
    assert '2.00 %' in text
    assert '수집 상태 보고서' not in text
    assert list(report.parent.glob('charts/*.png'))
    assert (report.parent/'evidence.csv').exists()
    second=generate(store,tmp_path/'reports')
    assert report.exists() and (second.parent/'changes.diff').exists()
    assert len(list((tmp_path/'data'/'raw').iterdir()))==1


def test_denied_network_is_logged_and_not_success(tmp_path):
    def fail(url): raise SourceError('프록시 연결 거부')
    store=Store(tmp_path/'data')
    _,result=update(store,source='worldbank',fetch=fail)
    assert result[0][1]=='failed'
    assert all(r[1]=='skipped' for r in result[1:])
    assert store.frame().empty
    report=generate(store,tmp_path/'reports')
    assert '실제 데이터 미확보' in report.read_text()
    assert '성장률: 0' not in report.read_text()


def test_manual_import_retains_provenance(tmp_path):
    from economic_reality.sources import import_csv
    meta={'id':'local:wage','name':'임금 검증','category':'물가와 실질구매력','unit':'원','frequency':'M','source':'검증용 가상 출처','source_url':'https://example.org/test','adjustment':'비계절조정','price_basis':'명목','note':'합성 테스트 전용'}
    m=tmp_path/'meta.json'; m.write_text(json.dumps(meta))
    c=tmp_path/'values.csv'; c.write_text('country,period,value,release_date,status\nKOR,2025-01,100,2025-02-10,잠정치\n')
    s=Store(tmp_path/'db')
    import_csv(s,c,m)
    row=s.frame().iloc[0]
    assert row.release_date=='2025-02-10'
    assert row.status=='잠정치'
    assert (s.root/row.raw_path).exists()
