import pytest
from economic_reality.sources import parse_worldbank, parse_fred


def test_worldbank_preserves_null_and_provider_date():
    payload = [{'pages':1,'lastupdated':'2025-02-01'}, [{'indicator':{'id':'NY.GDP.MKTP.KD.ZG'},'countryiso3code':'KOR','date':'2024','value':None}, {'indicator':{'id':'NY.GDP.MKTP.KD.ZG'},'countryiso3code':'KOR','date':'2023','value':1.4}]]
    rows = parse_worldbank(payload, 'NY.GDP.MKTP.KD.ZG')
    assert rows[0]['value'] is None
    assert rows[0]['provider_updated'] == '2025-02-01'
    assert rows[0].get('release_date') is None
    with pytest.raises(ValueError):
        parse_worldbank(payload, 'WRONG')


def test_fred_missing_not_zero_and_reject_wrong_column():
    rows = parse_fred('observation_date,UNRATE\n2020-01-01,3.5\n2020-02-01,.\n', 'UNRATE', 'M', 'USA')
    assert rows[0]['period'] == '2020-01'
    assert rows[1]['value'] is None
    with pytest.raises(ValueError):
        parse_fred('observation_date,OTHER\n2020-01-01,5\n', 'UNRATE', 'M', 'USA')
