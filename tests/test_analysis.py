import pandas as pd
import pytest
from economic_reality.analysis import changes, indexed, relationship


def test_yoy_uses_calendar_not_previous_available_row():
    df = pd.DataFrame({'period':['2020','2022'],'value':[100.,121.]})
    out = changes(df, 'A')
    assert out['yoy'].isna().all()


def test_inflation_change_is_pp_not_percent():
    out = changes(pd.DataFrame({'period':['2020','2021'],'value':[4.,2.]}),'A')
    assert out.iloc[-1]['change'] == -2
    assert out.iloc[-1]['yoy'] == -50


def test_index_does_not_allow_negative_or_zero_base():
    with pytest.raises(ValueError):
        indexed(pd.DataFrame({'period':['2020','2021'],'value':[0.,2.]}),'2020')


def test_relationship_insufficient_evidence_is_not_zero_correlation():
    df = pd.DataFrame({'period':['2020','2021'],'value':[2.,3.]})
    result = relationship(df,df,'A',lag=0)
    assert result['correlation'] is None
