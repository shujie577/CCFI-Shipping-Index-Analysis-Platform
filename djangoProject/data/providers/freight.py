"""基于航交所 CCFI（中国出口集装箱运价指数）公开分航线指数。"""

from datetime import datetime, timedelta

from data.fetch_meta import attach_fetch_meta

from .macromicro import fetch_index_history
from .sse import fetch_sse_indices

# 官方数据源：https://www.sse.net.cn/index/singleIndex?indexType=ccfi
CCFI_INDEX_CODE = 'CCFI'
CCFI_INDEX_NAME = '中国出口集装箱运价指数'
CCFI_INDEX_NAME_EN = 'CHINA CONTAINERIZED FREIGHT INDEX'
CCFI_SOURCE_URL = 'https://www.sse.net.cn/index/singleIndex?indexType=ccfi'
CCFI_SOURCE_ORG = '上海航运交易所'


CCFI_COMPOSITE_LABEL = '中国出口集装箱运价综合指数'

# 与航交所 CCFI 单期页表格顺序一致
CCFI_ROUTE_ORDER = [
    '日本航线',
    '欧洲航线',
    '美西航线',
    '美东航线',
    '韩国航线',
    '东南亚航线',
    '地中海航线',
    '澳新航线',
    '南非航线',
    '南美航线',
    '东西非航线',
    '波红航线',
]


# 港口对 → CCFI 分航线名称（与航交所 CCFI 单期页 12 条分航线一致）
ROUTE_CCFI_MAP = {
    ('上海港', '鹿特丹港'): '欧洲航线',
    ('上海港', '汉堡港'): '欧洲航线',
    ('上海港', '安特卫普港'): '欧洲航线',
    ('上海港', '洛杉矶港'): '美西航线',
    ('上海港', '长滩港'): '美西航线',
    ('上海港', '纽约港'): '美东航线',
    ('上海港', '萨凡纳港'): '美东航线',
    ('上海港', '新加坡港'): '东南亚航线',
    ('上海港', '曼谷港'): '东南亚航线',
    ('上海港', '釜山港'): '韩国航线',
    ('上海港', '东京港'): '日本航线',
    ('上海港', '横滨港'): '日本航线',
    ('上海港', '比雷埃夫斯港'): '地中海航线',
    ('上海港', '热那亚港'): '地中海航线',
    ('上海港', '悉尼港'): '澳新航线',
    ('上海港', '墨尔本港'): '澳新航线',
    ('上海港', '德班港'): '南非航线',
    ('上海港', '桑托斯港'): '南美航线',
    ('上海港', '拉各斯港'): '东西非航线',
    ('上海港', '吉达港'): '波红航线',
    ('宁波舟山港', '洛杉矶港'): '美西航线',
    ('宁波舟山港', '鹿特丹港'): '欧洲航线',
    ('深圳港', '洛杉矶港'): '美西航线',
    ('深圳港', '悉尼港'): '澳新航线',
    ('青岛港', '洛杉矶港'): '美西航线',
    ('天津港', '洛杉矶港'): '美西航线',
    ('广州港', '鹿特丹港'): '欧洲航线',
    ('香港港', '洛杉矶港'): '美西航线',
    ('新加坡港', '鹿特丹港'): '欧洲航线',
    ('釜山港', '洛杉矶港'): '美西航线',
}

PORTS = sorted(set(p for pair in ROUTE_CCFI_MAP for p in pair))


def build_freight_snapshot(force_refresh: bool = False) -> dict:
    sse, _meta = fetch_sse_indices(force_refresh=force_refresh)
    history = fetch_index_history(force_refresh=force_refresh)
    return {'sse': sse, 'history': history}


def _with_sse_meta(payload: dict, meta, force_refresh: bool) -> dict:
    return attach_fetch_meta(payload, meta, requested_live=force_refresh)


def get_available_ports() -> list:
    return PORTS


class FreightFetchError(Exception):
    """CCFI 分航线指数无法解析或未映射时抛出。"""


def get_ccfi_route_options() -> list:
    """CCFI 可选航线（综合指数 + 12 条分航线），与航交所单期页一致。"""
    return [
        {'route_label': CCFI_COMPOSITE_LABEL},
        *[{'route_label': label} for label in CCFI_ROUTE_ORDER],
    ]


def get_port_pairs_for_comparison():
    """兼容旧接口名：返回 CCFI 航线选项（非港口对）。"""
    return get_ccfi_route_options()


def get_ccfi_route_table(force_refresh: bool = False) -> dict:
    """返回航交所 CCFI 单期页全部分航线指数（与官网表格一致）。"""
    sse, meta = fetch_sse_indices(force_refresh=force_refresh)
    ccfi = sse.get('ccfi', {})
    routes = sse.get('routes_ccfi', {})
    rows = []
    for name in CCFI_ROUTE_ORDER:
        data = routes.get(name)
        if not data:
            continue
        rows.append({
            'route_label': name,
            'index_previous': data.get('previous'),
            'index_value': data.get('current'),
            'change_pct': data.get('change_pct'),
        })
    return _with_sse_meta({
        'index_code': CCFI_INDEX_CODE,
        'index_name': CCFI_INDEX_NAME,
        'index_name_en': CCFI_INDEX_NAME_EN,
        'source': CCFI_SOURCE_ORG,
        'source_url': CCFI_SOURCE_URL,
        'composite_previous': ccfi.get('composite_previous'),
        'composite_current': ccfi.get('composite_current'),
        'composite_change_pct': ccfi.get('composite_change_pct'),
        'current_period': ccfi.get('current_period'),
        'previous_period': ccfi.get('previous_period'),
        'routes': rows,
    }, meta, force_refresh)


def get_realtime_ccfi_by_route(route_label: str, force_refresh: bool = False) -> dict:
    """按 CCFI 航线名或综合指数名返回实时指数。"""
    sse, meta = fetch_sse_indices(force_refresh=force_refresh)
    ccfi = sse.get('ccfi', {})
    route_label, index_value, index_previous, change_pct, trend = _resolve_route_label(
        sse, route_label
    )
    return _with_sse_meta({
        'route_label': route_label,
        'index_code': CCFI_INDEX_CODE,
        'index_name': CCFI_INDEX_NAME,
        'index_name_en': CCFI_INDEX_NAME_EN,
        'index_value': index_value,
        'index_previous': index_previous,
        'change_pct': change_pct,
        'current_period': ccfi.get('current_period'),
        'previous_period': ccfi.get('previous_period'),
        'composite_current': ccfi.get('composite_current'),
        'date': ccfi.get('current_period'),
        'trend': trend,
        'source': CCFI_SOURCE_ORG,
        'source_url': CCFI_SOURCE_URL,
    }, meta, force_refresh)


CCFI_CHART_WEEKS = 6  # 约 1.5 个月（CCFI 周度，6 个刻度）
CCFI_LOGIN_NOTE = '除本期、上期外，更多历史指数需登录上海航运交易所查看'


def get_realtime_freight_rate(origin_port: str, dest_port: str, force_refresh: bool = False) -> dict:
    """兼容旧接口：港口对 → CCFI 分航线。"""
    route_label, _, _, _, _ = _resolve_index(
        fetch_sse_indices(force_refresh=force_refresh)[0], origin_port, dest_port
    )
    payload = get_realtime_ccfi_by_route(route_label, force_refresh=force_refresh)
    payload['origin'] = origin_port
    payload['destination'] = dest_port
    return payload


def get_historical_ccfi_by_route(route_label: str, days: int = 45, force_refresh: bool = False) -> dict:
    """
    公开页仅提供上期、本期两期指数；其余周次需登录航交所。
    返回约 1.5 个月周度时间轴，仅两期有真实数值。
    """
    sse, meta = fetch_sse_indices(force_refresh=force_refresh)
    weeks = CCFI_CHART_WEEKS if days >= 42 else max(4, days // 7)
    return _with_sse_meta(
        _build_public_ccfi_chart_series(sse, route_label, weeks=weeks),
        meta,
        force_refresh,
    )


def _build_public_ccfi_chart_series(sse: dict, route_label: str, weeks: int = CCFI_CHART_WEEKS) -> dict:
    ccfi = sse.get('ccfi', {})
    prev_date = ccfi.get('previous_period')
    curr_date = ccfi.get('current_period')
    if not prev_date or not curr_date:
        raise FreightFetchError('未能从航交所页面解析 CCFI 上期/本期日期')

    _, curr_val, prev_val, _, _ = _resolve_route_label(sse, route_label)
    anchor = datetime.strptime(curr_date, '%Y-%m-%d').date()
    axis_dates = [
        (anchor - timedelta(weeks=i)).strftime('%Y-%m-%d')
        for i in range(weeks, -1, -1)
    ]
    value_map = {prev_date: prev_val, curr_date: curr_val}

    series = []
    for d in axis_dates:
        if d in value_map:
            v = value_map[d]
            series.append({
                'date': d,
                'value': v,
                'rate': v,
                'public': True,
                'locked': False,
            })
        else:
            series.append({
                'date': d,
                'value': None,
                'rate': None,
                'public': False,
                'locked': True,
            })

    return {
        'current_period': curr_date,
        'previous_period': prev_date,
        'series': series,
        'public_points': 2,
        'login_required_note': CCFI_LOGIN_NOTE,
    }


def get_historical_freight_rates(origin_port: str, dest_port: str, days: int = 45, force_refresh: bool = False) -> dict:
    """兼容旧接口：港口对 → CCFI 分航线历史。"""
    sse, _ = fetch_sse_indices(force_refresh=force_refresh)
    route_label, _, _, _, _ = _resolve_index(sse, origin_port, dest_port)
    return get_historical_ccfi_by_route(route_label, days, force_refresh=force_refresh)


def get_port_throughput(period: str = 'week', force_refresh: bool = False) -> list:
    from .wikipedia_ports import fetch_port_rankings

    rankings, _meta = fetch_port_rankings(force_refresh=force_refresh)
    multiplier = {'day': 1 / 365, 'week': 7 / 365, 'month': 1 / 12}.get(period, 1 / 12)

    results = []
    for item in rankings:
        annual = item['annual_teu']
        results.append({
            'port_name': item['port_name'],
            'throughput_teu': int(annual * multiplier),
            'growth_rate': round(item.get('growth_rate') or 0.0, 3),
            'rank': item['rank'],
            'data_year': item.get('data_year', 2024),
            'source': "Wikipedia / Lloyd's List 公开吞吐量",
        })
    return results


def _resolve_route_label(sse: dict, route_label: str):
    ccfi = sse.get('ccfi', {})
    label = route_label.strip()
    if label in ('综合指数', CCFI_COMPOSITE_LABEL):
        current = ccfi.get('composite_current')
        previous = ccfi.get('composite_previous')
        change_pct = ccfi.get('composite_change_pct')
        if current is None:
            raise FreightFetchError('航交所 CCFI 页面未解析到综合指数')
        trend = _calc_trend(current, previous, change_pct)
        return CCFI_COMPOSITE_LABEL, round(float(current), 2), (
            round(float(previous), 2) if previous else None
        ), change_pct, trend

    routes = sse.get('routes_ccfi', {})
    route = routes.get(label, {})
    current = route.get('current')
    previous = route.get('previous')
    change_pct = route.get('change_pct')
    if current is None:
        parsed = '、'.join(CCFI_ROUTE_ORDER)
        raise FreightFetchError(f'未知或未解析的 CCFI 航线「{label}」。可选: {parsed}')
    trend = _calc_trend(current, previous, change_pct)
    return label, round(float(current), 2), round(float(previous), 2) if previous else None, change_pct, trend


def _calc_trend(current, previous, change_pct):
    if previous and current:
        if current > previous * 1.01:
            return 'up'
        if current < previous * 0.99:
            return 'down'
        return 'stable'
    if change_pct is not None:
        if change_pct > 0.5:
            return 'up'
        if change_pct < -0.5:
            return 'down'
        return 'stable'
    return 'stable'


def _resolve_index(sse: dict, origin: str, dest: str):
    route_key = ROUTE_CCFI_MAP.get((origin, dest)) or ROUTE_CCFI_MAP.get((dest, origin))
    if not route_key:
        raise FreightFetchError(f'暂不支持该港口对的 CCFI 航线映射: {origin} → {dest}')

    routes = sse.get('routes_ccfi', {})
    route = routes.get(route_key, {})
    current = route.get('current')
    previous = route.get('previous')
    change_pct = route.get('change_pct')

    if current is None:
        parsed = '、'.join(sorted(routes.keys())) if routes else '无'
        raise FreightFetchError(
            f'航交所 CCFI 页面未解析到「{route_key}」（{origin}→{dest}）。'
            f'已解析分航线: {parsed}'
        )

    trend = _calc_trend(current, previous, change_pct)
    return route_key, round(float(current), 2), round(float(previous), 2) if previous else None, change_pct, trend


def _public_series_values(payload: dict) -> list:
    """提取公开两期数值，供预测等模块使用。"""
    return [
        p for p in payload.get('series', [])
        if p.get('public') and p.get('value') is not None
    ]


def _flat_index_series(base: float, days: int):
    end = datetime.now().date()
    start = end - timedelta(days=days - 1)
    return [
        {
            'date': (start + timedelta(days=i)).strftime('%Y-%m-%d'),
            'value': round(base, 2),
            'rate': round(base, 2),
        }
        for i in range(days)
    ]
