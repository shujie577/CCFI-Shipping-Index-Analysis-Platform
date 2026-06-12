"""内网 / 离线模式下的内置数据（无外网时使用）。"""

from datetime import datetime, timedelta


def _index_series(base: float, days: int = 365) -> list:
    end = datetime.now().date()
    series = []
    value = base
    for i in range(days):
        day = end - timedelta(days=days - 1 - i)
        series.append({'date': day.strftime('%Y-%m-%d'), 'value': round(value, 2)})
        value += ((i % 5) - 2) * 1.5
    return series


def _sse_payload() -> dict:
    routes = {
        '欧洲40ft': {'previous': 3200.0, 'current': 3250.0, 'change': 50.0},
        '美西40ft': {'previous': 2800.0, 'current': 2750.0, 'change': -50.0},
        '东南亚20ft': {'previous': 680.0, 'current': 690.0, 'change': 10.0},
    }
    scfi = {
        'composite_current': 1850.0,
        'composite_previous': 1820.0,
        'composite_change': 30.0,
        'composite_change_pct': 1.65,
        'routes': routes,
        'publish_note': '内网内置数据（非实时）',
    }
    ccfi = {
        'composite_current': 1280.0,
        'composite_previous': 1270.0,
        'composite_change': 10.0,
        'composite_change_pct': 0.79,
        'routes': {},
        'publish_note': '内网内置数据（非实时）',
    }
    return {'scfi': scfi, 'ccfi': ccfi, 'routes_scfi': routes, 'routes_ccfi': {}}


def _port_rankings() -> list:
    raw = [
        ('上海港', 51.0), ('新加坡港', 41.1), ('宁波舟山港', 39.3), ('深圳港', 33.4),
        ('青岛港', 30.9), ('广州港', 26.0), ('釜山港', 24.3), ('天津港', 23.5),
        ('香港港', 14.8), ('鹿特丹港', 13.8), ('洛杉矶港', 10.3), ('长滩港', 9.6),
        ('汉堡港', 8.5), ('安特卫普港', 13.5), ('杰贝阿里港', 15.5),
    ]
    return [
        {
            'rank': i + 1,
            'port_name': name,
            'annual_teu': int(teu * 1_000_000),
            'growth_rate': 0.02,
            'data_year': 2024,
        }
        for i, (name, teu) in enumerate(raw)
    ]


def _schedules(origin: str, destination: str) -> list:
    base = datetime.now()
    dep1 = (base + timedelta(days=7)).strftime('%Y-%m-%d')
    arr1 = (base + timedelta(days=28)).strftime('%Y-%m-%d')
    dep2 = (base + timedelta(days=10)).strftime('%Y-%m-%d')
    arr2 = (base + timedelta(days=32)).strftime('%Y-%m-%d')
    return [
        {
            'id': 1,
            'carrier': 'COSCO',
            'vessel': 'COSCO SHIPPING UNIVERSE',
            'voyage': '001E',
            'departure_date': dep1,
            'arrival_date': arr1,
            'transit_days': 21,
            'status': 'scheduled',
            'cutoff_time': (base + timedelta(days=4)).strftime('%Y-%m-%d'),
            'origin': origin,
            'destination': destination,
            'source': 'local_seed',
        },
        {
            'id': 2,
            'carrier': 'MSC',
            'vessel': 'MSC GULSUN',
            'voyage': 'FW502W',
            'departure_date': dep2,
            'arrival_date': arr2,
            'transit_days': 22,
            'status': 'scheduled',
            'cutoff_time': (base + timedelta(days=7)).strftime('%Y-%m-%d'),
            'origin': origin,
            'destination': destination,
            'source': 'local_seed',
        },
    ]


SEEDS = {
    'sse_indices': _sse_payload,
    'macromicro_index_history': lambda: {
        'series': {
            'SCFI': _index_series(1850.0),
            'CCFI': _index_series(1280.0),
        },
        'source': 'local_seed',
    },
    'eastmoney_shipping_indices': lambda: {
        'indices': [
            {'name': 'BDI', 'code': 'BDI', 'label': '波罗的海干散货指数', 'value': 1520.0, 'change': 0.8},
            {'name': 'BDTI', 'code': 'BDTI', 'label': '原油运输指数', 'value': 980.0, 'change': -0.3},
            {'name': 'BCTI', 'code': 'BCTI', 'label': '成品油运输指数', 'value': 760.0, 'change': 0.5},
        ],
        'history': {
            'BDI': _index_series(1520.0, 30),
            'BDTI': _index_series(980.0, 30),
            'BCTI': _index_series(760.0, 30),
        },
        'source': 'local_seed',
    },
    'wikipedia_port_rankings': _port_rankings,
}


def get_seed(key: str):
    if key.startswith('schedules_'):
        parts = key.replace('schedules_', '', 1).split('_', 1)
        if len(parts) == 2:
            return _schedules(parts[0], parts[1])
        return _schedules('上海港', '洛杉矶港')

    factory = SEEDS.get(key)
    return factory() if factory else None
