"""船期 — Hapag-Lloyd 公开 Schedule API（无需 API Key）。"""

from datetime import datetime, timedelta

from django.conf import settings

from ..fetch_helpers import resolve_data
from .http_client import get_session

CACHE_TTL = 3600

PORT_LOCODE = {
    '上海港': 'CNSHA',
    '宁波舟山港': 'CNNGB',
    '深圳港': 'CNSZN',
    '广州港': 'CNCAN',
    '青岛港': 'CNTAO',
    '天津港': 'CNTXG',
    '新加坡港': 'SGSIN',
    '釜山港': 'KRPUS',
    '香港港': 'HKHKG',
    '杰贝阿里港': 'AEJEA',
    '鹿特丹港': 'NLRTM',
    '汉堡港': 'DEHAM',
    '洛杉矶港': 'USLAX',
    '长滩港': 'USLGB',
    '安特卫普港': 'BEANR',
    '悉尼港': 'AUSYD',
}

CARRIER_SCAC = {
    'MAERSK': 'MAEU',
    'MSC': 'MSCU',
    'COSCO': 'COSU',
    'CMA CGM': 'CMDU',
    'ONE': 'ONEY',
    'HMM': 'HDMU',
    'HAPAG-LLOYD': 'HLCU',
    'EVERGREEN': 'EGLV',
}


def fetch_vessel_schedules(origin: str, destination: str, weeks: int = 4, force_refresh: bool = False) -> list:
    cache_key = f'schedules_{origin}_{destination}'

    def _fetch():
        locode_from = PORT_LOCODE.get(origin)
        locode_to = PORT_LOCODE.get(destination)
        if not locode_from or not locode_to:
            raise ValueError(f'暂不支持该港口船期查询: {origin} -> {destination}')

        schedules = []
        api_key = getattr(settings, 'SEARATES_API_KEY', '') or ''
        if api_key:
            schedules = _fetch_searates(locode_from, locode_to, weeks, api_key)

        if not schedules:
            schedules = _fetch_hapag_lloyd(locode_from, locode_to, weeks)

        if not schedules:
            raise ConnectionError(
                f'无法从船公司公开接口获取 {origin}→{destination} 船期'
            )
        return schedules

    return resolve_data(
        cache_key,
        _fetch,
        force_refresh=force_refresh,
        ttl=CACHE_TTL,
        source='carrier_api',
    )


def _fetch_hapag_lloyd(locode_from: str, locode_to: str, weeks: int) -> list:
    session = get_session()
    start = datetime.now().strftime('%Y-%m-%d')
    url = settings.DATA_SOURCE_URLS['hapag_lloyd_schedule']
    params = {
        'startLocation': locode_from,
        'endLocation': locode_to,
        'startDate': start,
        'numberOfWeeks': weeks,
    }
    resp = session.get(url, params=params)
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []

    rows = []
    items = data if isinstance(data, list) else data.get('schedules') or data.get('data') or []
    if isinstance(data, dict) and not items:
        items = data.get('pointToPoint', []) or data.get('routes', [])

    idx = 0
    for item in items[:20]:
        idx += 1
        carrier = item.get('carrierName') or item.get('carrier') or 'HAPAG-LLOYD'
        voyage = item.get('voyageNumber') or item.get('voyage') or item.get('serviceCode') or ''
        dep = _first_date(item, ['departureDate', 'etd', 'departure', 'startDate'])
        arr = _first_date(item, ['arrivalDate', 'eta', 'arrival', 'endDate'])
        if not dep:
            continue
        if not arr:
            arr = (datetime.strptime(dep, '%Y-%m-%d') + timedelta(days=21)).strftime('%Y-%m-%d')

        dep_dt = datetime.strptime(dep[:10], '%Y-%m-%d')
        arr_dt = datetime.strptime(arr[:10], '%Y-%m-%d')
        transit = (arr_dt - dep_dt).days

        status = 'scheduled'
        delay_note = item.get('delay') or item.get('status')
        if delay_note and 'delay' in str(delay_note).lower():
            status = 'delayed'

        rows.append({
            'id': idx,
            'carrier': carrier.upper() if isinstance(carrier, str) else 'HAPAG-LLOYD',
            'voyage': str(voyage)[:20],
            'departure_date': dep[:10],
            'arrival_date': arr[:10],
            'transit_days': max(transit, 1),
            'status': status,
            'cutoff_time': (dep_dt - timedelta(days=3)).strftime('%Y-%m-%d'),
            'source': 'Hapag-Lloyd 公开船期 API',
        })

    return rows


def _fetch_searates(locode_from: str, locode_to: str, weeks: int, api_key: str) -> list:
    session = get_session()
    session.headers['Authorization'] = f'Bearer {api_key}'
    start = datetime.now().strftime('%Y-%m-%d')
    url = settings.DATA_SOURCE_URLS['searates_schedule']
    params = {
        'origin': locode_from,
        'destination': locode_to,
        'from_date': start,
        'weeks': weeks,
        'cargo_type': 'GC',
        'sort': 'departure',
    }
    resp = session.get(url, params=params)
    if resp.status_code != 200:
        return []
    body = resp.json()
    schedules = body.get('data', {}).get('schedules') or body.get('schedules') or []
    rows = []
    for idx, item in enumerate(schedules[:20], 1):
        dep = _first_date(item, ['departure_date', 'etd'])
        arr = _first_date(item, ['arrival_date', 'eta'])
        if not dep:
            continue
        dep_dt = datetime.strptime(dep[:10], '%Y-%m-%d')
        arr_dt = datetime.strptime((arr or dep)[:10], '%Y-%m-%d')
        rows.append({
            'id': idx,
            'carrier': item.get('carrier_name', 'UNKNOWN'),
            'voyage': item.get('voyage', ''),
            'departure_date': dep[:10],
            'arrival_date': (arr or dep)[:10],
            'transit_days': max((arr_dt - dep_dt).days, 1),
            'status': 'scheduled',
            'cutoff_time': (dep_dt - timedelta(days=3)).strftime('%Y-%m-%d'),
            'source': 'SeaRates API',
        })
    return rows


def _first_date(item: dict, keys: list) -> str | None:
    for key in keys:
        val = item.get(key)
        if val:
            return str(val)[:10]
    legs = item.get('legs') or item.get('scheduleLegs') or []
    if legs and isinstance(legs[0], dict):
        for key in keys:
            val = legs[0].get(key)
            if val:
                return str(val)[:10]
    return None
