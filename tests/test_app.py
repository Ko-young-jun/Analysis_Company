from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from economic_reality.catalog import catalog
from economic_reality.store import Store


@pytest.mark.parametrize('populated',[False,True])
def test_all_screens_work(tmp_path,monkeypatch,populated):
    monkeypatch.setenv('ECONOMIC_DATA_DIR',str(tmp_path/'data'))
    monkeypatch.setenv('ECONOMIC_REPORT_DIR',str(tmp_path/'reports'))
    if populated:
        store=Store(tmp_path/'data')
        for meta in catalog(): store.register(meta)
        run=store.begin_run()
        for sid in ['wb:NY.GDP.MKTP.KD.ZG','wb:FP.CPI.TOTL.ZG']:
            store.save_observations(run,sid,[{'country':c,'period':str(y),'value':float(y-2010)} for c in ['KOR','USA','JPN'] for y in range(2015,2026)])
        store.finish_run(run)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    assert not app.exception
    for page in ['지표 탐색','국가 비교','지표 관계','산업과 청년고용','위험과 시나리오','데이터·갱신','보고서']:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, (page,app.exception)
    app.button[0].click().run(timeout=60)
    assert not app.exception
    assert list((tmp_path/'reports').glob('*/report.md'))
