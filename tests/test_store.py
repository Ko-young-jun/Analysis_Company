from economic_reality.store import Store


def test_revisions_and_missing_are_preserved(tmp_path):
    s = Store(tmp_path)
    meta = dict(id='test', name='검증용', category='한국 거시경제', unit='%', frequency='A', source='테스트', source_url='https://example.org', adjustment='해당 없음', price_basis='해당 없음', note='운영에 사용하지 않는 테스트')
    s.register(meta)
    r1 = s.begin_run()
    s.save_observations(r1, 'test', [dict(country='KOR', period='2020', value=2.0)])
    s.finish_run(r1)
    r2 = s.begin_run()
    s.save_observations(r2, 'test', [dict(country='KOR', period='2020', value=1.0)])
    s.finish_run(r2)
    assert s.frame().iloc[0].value == 1
    assert s.frame(as_of=r1).iloc[0].value == 2
    r3 = s.begin_run()
    s.save_observations(r3, 'test', [dict(country='KOR', period='2020', value=None)])
    s.finish_run(r3)
    assert s.frame().value.isna().all()
    assert len(s.history('test', 'KOR')) == 3


def test_invalid_batch_is_atomic(tmp_path):
    import pytest
    s = Store(tmp_path)
    s.register(dict(id='test', name='검증용', category='한국 거시경제', unit='%', frequency='A', source='테스트', source_url='https://example.org', adjustment='해당 없음', price_basis='해당 없음', note='검증'))
    run = s.begin_run()
    with pytest.raises(ValueError):
        s.save_observations(run, 'test', [dict(country='KOR', period='2020', value=2), dict(country='KOR', period='bad', value=3)])
    assert s.frame().empty


def test_unfinished_run_does_not_replace_published_observation(tmp_path):
    s=Store(tmp_path)
    s.register(dict(id='test', name='검증', category='한국 거시경제', unit='%', frequency='A', source='테스트', source_url='https://example.org', adjustment='해당 없음', price_basis='해당 없음', note='검증'))
    old=s.begin_run(); s.save_observations(old,'test',[dict(country='KOR',period='2020',value=1)]); s.finish_run(old)
    pending=s.begin_run(); s.save_observations(pending,'test',[dict(country='KOR',period='2020',value=2)])
    assert s.frame().iloc[0].value==1
    s.finish_run(pending)
    assert s.frame().iloc[0].value==2
