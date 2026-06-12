"""上海航运交易所 SCFI / CCFI 公开页面数据。"""

import re
from datetime import datetime

from bs4 import BeautifulSoup
from django.conf import settings

from ..fetch_helpers import resolve_data
from .http_client import get_session

CACHE_KEY = 'sse_indices'
CACHE_TTL = 6 * 3600


def fetch_sse_indices(force_refresh: bool = False):
    return resolve_data(
        CACHE_KEY,
        _fetch_sse_indices_from_web,
        force_refresh=force_refresh,
        ttl=CACHE_TTL,
        source='sse.net.cn',
    )


def _fetch_sse_indices_from_web() -> dict:
    session = get_session()
    scfi = _parse_scfi_page(session)
    ccfi = _parse_ccfi_page(session)
    return {
        'scfi': scfi,
        'ccfi': ccfi,
        'routes_scfi': scfi.get('routes', {}),
        'routes_ccfi': ccfi.get('routes', {}),
    }


def _parse_scfi_page(session) -> dict:
    """SCFI 单期页：公开可见综合指数；分航线 USD 格多为空。"""
    url = settings.DATA_SOURCE_URLS['sse']
    resp = session.get(url, params={'indexType': 'scfi'})
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(resp.text, 'lxml')

    result = {
        'composite_current': None,
        'composite_previous': None,
        'composite_change': None,
        'composite_change_pct': None,
        'routes': {},
        'publish_note': '数据来源：上海航运交易所 SCFI 公开页面',
    }

    for row in soup.find_all('tr'):
        cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
        if len(cells) < 2:
            continue
        row_text = ' '.join(cells)

        if '综合指数' in row_text or 'Comprehensive Index' in row_text:
            nums = _extract_numbers(cells)
            if len(nums) >= 2:
                prev, curr = (nums[-3], nums[-2]) if len(nums) >= 3 else (nums[0], nums[1])
                result['composite_previous'] = prev
                result['composite_current'] = curr
            continue

        route_name = cells[0]
        if not route_name or route_name in ('航线', 'Line Service', '分航线'):
            continue
        if '分航线' in route_name:
            continue
        nums = _extract_numbers(cells[3:6] if len(cells) >= 6 else cells[1:])
        if len(nums) >= 2:
            prev, curr = nums[0], nums[1]
            change = nums[2] if len(nums) > 2 else round(curr - prev, 2)
            result['routes'][_normalize_scfi_route(route_name)] = {
                'previous': prev,
                'current': curr,
                'change': change,
            }

    if result['composite_current'] is None:
        for row in soup.find_all('tr'):
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if '综合指数' in ' '.join(cells):
                nums = _extract_numbers(cells)
                if len(nums) >= 2:
                    result['composite_previous'] = nums[0]
                    result['composite_current'] = nums[1]
                    break

    return result


def _parse_ccfi_page(session) -> dict:
    """
    CCFI 单期页：4 列（航线 / 上期 / 本期 / 涨跌%），未登录即可读分航线指数。
    见 https://www.sse.net.cn/index/singleIndex?indexType=ccfi
    """
    url = settings.DATA_SOURCE_URLS['sse']
    resp = session.get(url, params={'indexType': 'ccfi'})
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(resp.text, 'lxml')

    result = {
        'composite_current': None,
        'composite_previous': None,
        'composite_change_pct': None,
        'current_period': None,
        'previous_period': None,
        'routes': {},
        'publish_note': '数据来源：上海航运交易所 CCFI（中国出口集装箱运价指数）公开页面',
    }

    for th in soup.find_all('th'):
        text = th.get_text(' ', strip=True)
        m_curr = re.search(r'本期(\d{4}-\d{2}-\d{2})', text)
        m_prev = re.search(r'上期(\d{4}-\d{2}-\d{2})', text)
        if m_curr and not result['current_period']:
            result['current_period'] = m_curr.group(1)
        if m_prev and not result['previous_period']:
            result['previous_period'] = m_prev.group(1)

    if not result['current_period'] or not result['previous_period']:
        prev_d, curr_d = _extract_ccfi_periods(resp.text)
        result['previous_period'] = result['previous_period'] or prev_d
        result['current_period'] = result['current_period'] or curr_d

    for row in soup.find_all('tr'):
        cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'])]
        if len(cells) < 4:
            continue

        name = cells[0]
        nums = _extract_numbers(cells[1:4])
        if len(nums) < 2:
            continue

        prev, curr = nums[0], nums[1]
        change_pct = nums[2] if len(nums) > 2 else None

        if '综合指数' in name:
            result['composite_previous'] = prev
            result['composite_current'] = curr
            result['composite_change_pct'] = change_pct
            continue

        if '航线' not in name and 'SERVICE' not in name:
            continue

        route_key = _normalize_ccfi_route(name)
        result['routes'][route_key] = {
            'previous': prev,
            'current': curr,
            'change_pct': change_pct,
        }

    return result


def _extract_ccfi_periods(html: str) -> tuple:
    """
    从 CCFI 单期页解析上期/本期日期（非页面查询框的“今天”）。
    表头结构：<td>上期<br>2026-05-22</td>、<td>本期<br>2026-05-29</td>
    """
    br_dates = re.findall(r'<br>\s*(\d{4}-\d{2}-\d{2})', html, flags=re.I)
    if len(br_dates) >= 2:
        return br_dates[0], br_dates[1]

    all_dates = sorted(set(re.findall(r'20\d{2}-\d{2}-\d{2}', html)))
    # 优先：相差约 7 天的一对（CCFI 周度发布）
    for i in range(len(all_dates) - 1):
        d1 = datetime.strptime(all_dates[i], '%Y-%m-%d').date()
        d2 = datetime.strptime(all_dates[i + 1], '%Y-%m-%d').date()
        if 5 <= (d2 - d1).days <= 10:
            return all_dates[i], all_dates[i + 1]

    # 排除与主簇间隔过大的“查询日期”（如页面默认今天 2026-06-04）
    filtered = list(all_dates)
    while len(filtered) >= 3:
        d_last = datetime.strptime(filtered[-1], '%Y-%m-%d').date()
        d_prev = datetime.strptime(filtered[-2], '%Y-%m-%d').date()
        if (d_last - d_prev).days > 14:
            filtered.pop(-1)
        else:
            break
    if len(filtered) >= 2:
        return filtered[-2], filtered[-1]
    return None, None


def _extract_numbers(cells):
    nums = []
    for cell in cells:
        cleaned = re.sub(r'[^\d.\-]', '', cell.replace(',', ''))
        if cleaned and cleaned not in ('-', '.'):
            try:
                nums.append(float(cleaned))
            except ValueError:
                pass
    return nums


def _normalize_ccfi_route(name: str) -> str:
    """「欧洲航线 (EUROPE SERVICE)」→「欧洲航线」"""
    name = name.split('(')[0].strip()
    mapping = {
        '日本': '日本航线',
        '欧洲': '欧洲航线',
        '美西': '美西航线',
        '美东': '美东航线',
        '韩国': '韩国航线',
        '东南亚': '东南亚航线',
        '地中海': '地中海航线',
        '澳新': '澳新航线',
        '南非': '南非航线',
        '南美': '南美航线',
        '东西非': '东西非航线',
        '波红': '波红航线',
    }
    for key, label in mapping.items():
        if key in name:
            return label
    return name[:20]


def _normalize_scfi_route(name: str) -> str:
    name = re.sub(r'\s+', '', name)
    if '欧洲' in name and '40' in name:
        return '欧洲40ft'
    if '美西' in name and '40' in name:
        return '美西40ft'
    if '东南亚' in name:
        return '东南亚20ft'
    if '地中海' in name and '40' in name:
        return '地中海40ft'
    return name[:40]
