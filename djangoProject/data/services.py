"""统一对外数据服务 — 替代原 ShippingDataService 仿真逻辑。"""

from datetime import datetime, timedelta

from . import cache_store
from django.utils import timezone

from .providers import (
    build_freight_snapshot,
    fetch_index_history,
    fetch_port_rankings,
    fetch_sse_indices,
    fetch_vessel_schedules,
)
from .providers.eastmoney_index import fetch_eastmoney_indices
from .providers.freight import (
    get_available_ports,
    get_ccfi_route_options,
    get_historical_ccfi_by_route,
    get_historical_freight_rates,
    get_port_pairs_for_comparison,
    get_port_throughput,
    get_realtime_ccfi_by_route,
    get_realtime_freight_rate,
)


class RealShippingDataService:
    """从公开数据源获取航运数据。"""

    def __init__(self, force_refresh: bool = False):
        self.force_refresh = force_refresh

    def get_realtime_freight_rate(self, origin_port, dest_port):
        return get_realtime_freight_rate(origin_port, dest_port, force_refresh=self.force_refresh)

    def get_realtime_ccfi_by_route(self, route_label):
        return get_realtime_ccfi_by_route(route_label, force_refresh=self.force_refresh)

    def get_historical_ccfi_by_route(self, route_label, days=90):
        return get_historical_ccfi_by_route(route_label, days, force_refresh=self.force_refresh)

    def get_ccfi_route_options(self):
        return get_ccfi_route_options()

    def get_port_throughput(self, period='week'):
        return get_port_throughput(period, force_refresh=self.force_refresh)

    def get_all_port_ranking(self, period='month', limit=50):
        data = get_port_throughput(period, force_refresh=self.force_refresh)
        return data[:limit]

    def get_historical_freight_rates(self, origin_port, dest_port, days=90):
        return get_historical_freight_rates(
            origin_port, dest_port, days, force_refresh=self.force_refresh
        )

    def get_port_pairs_for_comparison(self):
        return get_port_pairs_for_comparison()

    def get_available_ports(self):
        return get_available_ports()


def get_index_dashboard_data(force_refresh: bool = False) -> dict:
    """航运指数看板 — CCFI/SCFI 综合指数来自航交所公开页。"""
    sse = fetch_sse_indices(force_refresh=force_refresh)
    try:
        history_payload = fetch_index_history(force_refresh=force_refresh)
        series = history_payload.get('series', {})
    except Exception:
        cached = cache_store.get_cached('macromicro_index_history')
        series = (cached or {}).get('series', {})

    indices = []
    scfi = sse.get('scfi', {})
    ccfi = sse.get('ccfi', {})
    if scfi.get('composite_current'):
        indices.append({
            'name': 'SCFI',
            'code': 'SCFI',
            'value': scfi['composite_current'],
            'change': scfi.get('composite_change_pct') or 0,
        })
    if ccfi.get('composite_current'):
        indices.insert(0, {
            'name': 'CCFI（中国出口集装箱运价指数）',
            'code': 'CCFI',
            'value': ccfi['composite_current'],
            'change': ccfi.get('composite_change_pct') or 0,
            'source_url': 'https://www.sse.net.cn/index/singleIndex?indexType=ccfi',
            'current_period': ccfi.get('current_period'),
        })

    for code, label in (('SCFI', 'SCFI'), ('CCFI', 'CCFI')):
        if any(i['code'] == code for i in indices):
            continue
        pts = series.get(code, [])
        if pts:
            last = pts[-1]['value']
            prev = pts[-2]['value'] if len(pts) > 1 else last
            chg = round((last - prev) / prev * 100, 2) if prev else 0
            indices.append({'name': label, 'code': code, 'value': last, 'change': chg})

    dates = []
    history = []
    for code in ('SCFI', 'CCFI'):
        pts = series.get(code, [])
        if not pts:
            continue
        tail = pts[-30:]
        if not dates:
            dates = [datetime.strptime(p['date'], '%Y-%m-%d').strftime('%m/%d') for p in tail]
        history.append({
            'name': code,
            'values': [p['value'] for p in tail],
        })

    if not dates and indices:
        dates = [
            (datetime.now() - timedelta(days=i)).strftime('%m/%d')
            for i in range(30, 0, -1)
        ]
        for idx in indices:
            history.append({'name': idx['name'], 'values': [idx['value']] * 30})

    try:
        em, _meta = fetch_eastmoney_indices(force_refresh=force_refresh)
        for em_idx in em.get('indices', []):
            if not any(i['code'] == em_idx['code'] for i in indices):
                indices.append({
                    'name': em_idx['code'],
                    'code': em_idx['code'],
                    'value': em_idx['value'],
                    'change': em_idx.get('change', 0),
                })
            em_hist = em.get('history', {}).get(em_idx['code'], [])
            if em_hist:
                if not dates:
                    dates = [
                        datetime.strptime(p['date'], '%Y-%m-%d').strftime('%m/%d')
                        for p in em_hist
                    ]
                history.append({
                    'name': em_idx['code'],
                    'values': [p['value'] for p in em_hist],
                })
    except Exception:
        pass

    return {
        'indices': indices,
        'dates': dates,
        'history': history,
        'source': '上海航运交易所 + MacroMicro + 东方财富行业指数',
        'fetched_at': timezone.now().isoformat(),
    }


def get_schedules(origin: str, destination: str, force_refresh: bool = False):
    return fetch_vessel_schedules(origin, destination, force_refresh=force_refresh)


def warm_all_caches():
    """预拉取全部外部数据。"""
    from news.services import sync_news_from_sources

    build_freight_snapshot(force_refresh=True)
    data = get_index_dashboard_data(force_refresh=True)
    cache_store.set_cached('index_dashboard', data, source='sse+macromicro')
    sync_news_from_sources()
    fetch_port_rankings(force_refresh=True)
    try:
        from .providers.schedules import fetch_vessel_schedules
        fetch_vessel_schedules('上海港', '洛杉矶港')
    except Exception:
        pass
    return True
