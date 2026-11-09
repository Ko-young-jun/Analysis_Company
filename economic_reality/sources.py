"""공개 API/CSV. TLS·프록시 설정을 유지하고 원문과 실패 이력을 저장한다."""
import csv
import io
import json
import os
from datetime import date
from urllib.parse import urlencode, urlparse

import pandas as pd
import requests

from .catalog import COUNTRIES, catalog


class SourceError(Exception):
    pass


def parse_worldbank(payload, code):
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[0], dict):
        raise ValueError('World Bank 응답 형식 오류')
    if int(payload[0].get('pages', 1)) != 1:
        raise ValueError('응답 페이지 누락: 조회 범위를 줄이세요')
    if payload[1] is None:
        return []
    rows = []
    for row in payload[1]:
        if row['indicator']['id'] != code or row['countryiso3code'] not in COUNTRIES:
            raise ValueError('요청과 다른 지표 또는 국가')
        rows.append(dict(country=row['countryiso3code'], period=row['date'], value=row['value'],
                         provider_updated=payload[0].get('lastupdated'), status='미확인'))
    return rows


def parse_fred(text, code, frequency, country):
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or code not in reader.fieldnames:
        raise ValueError('FRED 시리즈 열 누락')
    date_col = 'observation_date' if 'observation_date' in reader.fieldnames else 'DATE'
    if date_col not in reader.fieldnames:
        raise ValueError('FRED 날짜 열 누락')
    rows = []
    for row in reader:
        period = str(pd.Period(row[date_col], freq=frequency))
        raw = row[code]
        rows.append(dict(country=country, period=period, value=None if raw in ('', '.') else float(raw), status='미확인'))
    return rows


def request(url):
    # requests honors REQUESTS_CA_BUNDLE; use platform CA when only SSL_CERT_FILE is set.
    verify = os.environ.get('REQUESTS_CA_BUNDLE') or os.environ.get('SSL_CERT_FILE') or True
    try:
        response = requests.get(url, timeout=(10, 30), verify=verify)
    except requests.exceptions.ProxyError as exc:
        raise SourceError('프록시 연결 거부: 네트워크 허용 도메인의 적용 상태를 확인하세요') from exc
    except requests.exceptions.SSLError as exc:
        raise SourceError('TLS 인증서 검증 실패: 환경의 CA 신뢰 설정 확인 필요') from exc
    except requests.RequestException as exc:
        raise SourceError(f'네트워크 요청 실패 ({type(exc).__name__})') from exc
    if response.status_code != 200:
        raise SourceError(f'HTTP {response.status_code}: 공식 공급자 또는 프록시 접근 실패')
    if len(response.content) > 20_000_000:
        raise SourceError('응답 크기 제한 초과')
    return response.content


def update(store, source='all', start=2015, end=None, only=None, fetch=request):
    end = end or date.today().year
    if not 1960 <= start <= end <= date.today().year:
        raise ValueError('시작/종료 연도를 확인하세요')
    specs = catalog()
    for meta in specs:
        store.register(meta)
    selected = [m for m in specs if (source == 'all' or m['adapter'] == source) and (not only or m['id'] in only)]
    if not selected:
        raise ValueError('수집할 지표가 없습니다')
    run = store.begin_run()
    results = []
    blocked = set()
    try:
        for m in selected:
            if m['adapter'] == 'worldbank':
                url = 'https://api.worldbank.org/v2/country/' + ';'.join(COUNTRIES) + '/indicator/' + m['code'] + '?' + urlencode(dict(format='json', date=f'{start}:{end}', per_page=20000, source=2))
                suffix = 'json'
            else:
                url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?' + urlencode(dict(id=m['code'], cosd=f'{start}-01-01', coed=f'{end}-12-31'))
                suffix = 'csv'
            host = urlparse(url).hostname
            raw = None
            try:
                if host in blocked:
                    store.attempt(run, m['id'], url, 'skipped', '같은 출처의 프록시 거부로 이번 실행에서 미시도')
                    results.append((m['id'], 'skipped', 0))
                    continue
                body = fetch(url)
                raw = store.raw(body, suffix)
                if suffix == 'json':
                    rows = parse_worldbank(json.loads(body), m['code'])
                else:
                    rows = parse_fred(body.decode('utf-8-sig'), m['code'], m['frequency'], m['country'])
                    rows = [r for r in rows if start <= int(r['period'][:4]) <= end and r['period'] <= date.today().isoformat()]
                store.save_observations(run, m['id'], rows, raw)
                count = sum(r['value'] is not None for r in rows)
                status = 'success' if count else 'empty'
                store.attempt(run, m['id'], url, status, '원문 결측은 그대로 보존', count, raw)
                results.append((m['id'], status, count))
            except (SourceError, ValueError, KeyError, TypeError) as exc:
                if isinstance(exc, SourceError) and '프록시 연결 거부' in str(exc):
                    blocked.add(host)
                store.attempt(run, m['id'], url, 'failed', str(exc), raw_path=raw)
                results.append((m['id'], 'failed', 0))
    finally:
        store.finish_run(run)
    return run, results


def import_csv(store, csv_path, metadata_path):
    """공식 다운로드를 정규화한 CSV. 출처·정의는 metadata JSON으로 명시한다."""
    from pathlib import Path
    metadata_body = Path(metadata_path).read_bytes()
    meta = json.loads(metadata_body)
    if not meta['id'].startswith('local:'):
        raise ValueError('수동 가져오기는 local: 접두사 ID를 사용하세요')
    if urlparse(meta['source_url']).scheme != 'https':
        raise ValueError('공식 원문 HTTPS URL 필요')
    body = Path(csv_path).read_bytes()
    reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig')))
    if not {'country','period','value','release_date','status'} <= set(reader.fieldnames or []):
        raise ValueError('CSV 필수 열: country,period,value,release_date,status')
    rows = []
    for row in reader:
        if row['status'] not in ('속보치','잠정치','확정치','미확인'):
            raise ValueError('공표 상태를 확인하세요')
        if row['country'] not in COUNTRIES:
            raise ValueError('등록되지 않은 국가 코드')
        rows.append(dict(country=row['country'],period=row['period'],value=None if row['value']=='' else float(row['value']), release_date=row['release_date'] or None,status=row['status']))
    store.register(meta)
    run = store.begin_run()
    raw = store.raw(body, 'csv')
    store.raw(metadata_body, 'metadata.json')
    try:
        store.save_observations(run, meta['id'], rows, raw)
        store.attempt(run,meta['id'],meta['source_url'],'success','수동 가져오기: 출처 메타데이터는 제공자 입력; 공식성 별도 확인',len(rows),raw)
    except Exception:
        store.attempt(run,meta['id'],meta['source_url'],'failed','CSV 검증 실패',raw_path=raw)
        raise
    finally:
        store.finish_run(run)
    return run
