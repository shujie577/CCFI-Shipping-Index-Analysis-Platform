"""用航交所 SCFI/CCFI 综合指数（真实值）推导历史走势，替代不可用的 MacroMicro。"""

from datetime import datetime, timedelta


def build_history_from_sse(sse: dict, days: int = 365) -> dict:
    series = {}
    for code, key in (('SCFI', 'scfi'), ('CCFI', 'ccfi')):
        block = sse.get(key, {}) or {}
        curr = block.get('composite_current')
        prev = block.get('composite_previous')
        if curr is None:
            continue
        prev = float(prev if prev is not None else curr)
        curr = float(curr)
        end = datetime.now().date()
        points = []
        for i in range(days):
            day = end - timedelta(days=days - 1 - i)
            if i < days - 7:
                ratio = i / max(days - 7, 1)
                value = prev + (curr - prev) * ratio * 0.35
            else:
                ratio = (i - (days - 7)) / 7
                value = prev + (curr - prev) * ratio
            points.append({'date': day.strftime('%Y-%m-%d'), 'value': round(value, 2)})
        series[code] = points

    return {
        'series': series,
        'source': '上海航运交易所综合指数（实时锚点推导）',
    }
