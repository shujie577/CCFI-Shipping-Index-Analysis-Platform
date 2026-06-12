"""MacroMicro 公开图表接口 — 用于 SCFI/CCFI 历史走势。"""

import logging
from datetime import datetime

from django.conf import settings

from ..cache_store import get_cached, set_cached
from ..fetch_helpers import intranet_only, resolve_data
from .http_client import get_session
from .sse import fetch_sse_indices
from .sse_history import build_history_from_sse

logger = logging.getLogger(__name__)

CACHE_KEY = 'macromicro_index_history'
CACHE_TTL = 12 * 3600


def _ts_to_date(ts) -> str:
    if isinstance(ts, (int, float)) and ts > 1e11:
        dt = datetime.utcfromtimestamp(ts / 1000)
    elif isinstance(ts, (int, float)):
        dt = datetime.utcfromtimestamp(ts)
    else:
        return str(ts)[:10]
    return dt.strftime('%Y-%m-%d')


def fetch_index_history(force_refresh: bool = False) -> dict:
    """MacroMicro 历史 → 失败则用航交所实时 SCFI/CCFI 综合指数推导（锚点为真实值）。"""
    if intranet_only():
        payload, _meta = resolve_data(
            CACHE_KEY,
            _fetch_index_history_from_web,
            force_refresh=force_refresh,
            ttl=CACHE_TTL,
            source='macromicro',
        )
        return payload

    if not force_refresh:
        cached = get_cached(CACHE_KEY, max_age_seconds=CACHE_TTL, reject_sources={'local_seed'})
        if cached:
            return cached

    try:
        payload = _fetch_index_history_from_web()
        set_cached(CACHE_KEY, payload, source='macromicro')
        return payload
    except Exception as exc:
        logger.warning('MacroMicro 不可用: %s', exc)

    cached = get_cached(CACHE_KEY, reject_sources={'local_seed'})
    if cached and not force_refresh:
        return cached

    sse, _meta = fetch_sse_indices(force_refresh=force_refresh)
    payload = build_history_from_sse(sse)
    if not payload.get('series'):
        raise LookupError('航交所综合指数为空，无法推导历史走势')
    set_cached(CACHE_KEY, payload, source='sse.net.cn')
    return payload


def _fetch_index_history_from_web() -> dict:
    session = get_session()
    session.headers.update({
        'Referer': settings.DATA_SOURCE_URLS['macromicro_referer'],
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
    })
    resp = session.get(settings.DATA_SOURCE_URLS['macromicro'])
    resp.raise_for_status()
    body = resp.json()
    if not body.get('success'):
        raise ValueError(f'MacroMicro 返回失败: {body.get("msg", "unknown")}')

    series = {}
    data = body.get('data') or {}
    for key, meta in data.items():
        if not isinstance(meta, dict):
            continue
        name = (meta.get('name') or meta.get('label') or key).upper()
        points = meta.get('data') or meta.get('values') or []
        parsed = []
        for pt in points:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                ts, val = pt[0], pt[1]
                if isinstance(ts, (int, float)) and ts > 1e11:
                    dt = datetime.utcfromtimestamp(ts / 1000)
                else:
                    dt = datetime.utcfromtimestamp(ts)
                parsed.append({'date': dt.strftime('%Y-%m-%d'), 'value': float(val)})
            elif isinstance(pt, dict):
                parsed.append({
                    'date': pt.get('date') or pt.get('x', ''),
                    'value': float(pt.get('value') or pt.get('y') or 0),
                })
        if 'CCFI' in name:
            series['CCFI'] = parsed
        elif 'SCFI' in name:
            series['SCFI'] = parsed

    if not series:
        for key, val in data.items():
            if isinstance(val, dict) and 'data' in val:
                label = (val.get('name') or val.get('label') or str(key)).upper()
                if 'CCFI' in label:
                    code = 'CCFI'
                elif 'SCFI' in label:
                    code = 'SCFI'
                else:
                    continue
                series[code] = [
                    {'date': _ts_to_date(p[0]), 'value': float(p[1])}
                    for p in val['data']
                    if isinstance(p, (list, tuple)) and len(p) >= 2
                ]

    if not series:
        raise ValueError('MacroMicro 响应无 SCFI/CCFI 序列')
    return {'series': series, 'source': 'macromicro.me'}
