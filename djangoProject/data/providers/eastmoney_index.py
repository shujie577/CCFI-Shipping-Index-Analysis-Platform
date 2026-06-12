"""东方财富 — 航运/油运行业指数（公开 JSON 接口）。"""

import json
from datetime import datetime

from django.conf import settings

from ..fetch_helpers import resolve_data
from .http_client import get_session

CACHE_KEY = 'eastmoney_shipping_indices'
CACHE_TTL = 3600

INDEX_CODES = {
    'BDI': ('EMI00107664', '波罗的海干散货指数'),
    'BDTI': ('EMI00107668', '原油运输指数'),
    'BCTI': ('EMI00107669', '成品油运输指数'),
}


def fetch_eastmoney_indices(force_refresh: bool = False) -> dict:
    return resolve_data(
        CACHE_KEY,
        _fetch_eastmoney_indices_from_web,
        force_refresh=force_refresh,
        ttl=CACHE_TTL,
        source='eastmoney.com',
    )


def _fetch_eastmoney_indices_from_web() -> dict:
    session = get_session()
    result = {'indices': [], 'history': {}, 'source': '东方财富 industry index'}
    base_tpl = settings.DATA_SOURCE_URLS['eastmoney']

    for code, (em_id, name) in INDEX_CODES.items():
        url = base_tpl.format(code=em_id) + '&p=1&ps=60'
        resp = session.get(url)
        resp.raise_for_status()
        rows = json.loads(resp.text)
        if not rows:
            continue
        latest = rows[-1]
        prev = rows[-2] if len(rows) > 1 else latest
        value = float(latest.get('VALUE', 0))
        prev_val = float(prev.get('VALUE', value))
        change_pct = round((value - prev_val) / prev_val * 100, 2) if prev_val else 0

        result['indices'].append({
            'name': code,
            'code': code,
            'label': name,
            'value': round(value, 2),
            'change': change_pct,
        })

        history = []
        for row in rows[-30:]:
            dt_raw = row.get('DATADATE', '')
            try:
                dt = datetime.strptime(dt_raw[:10], '%Y-%m-%d')
            except ValueError:
                continue
            history.append({
                'date': dt.strftime('%Y-%m-%d'),
                'value': float(row.get('VALUE', 0)),
            })
        result['history'][code] = history

    if not result['indices']:
        raise ValueError('东方财富接口无数据')
    return result
