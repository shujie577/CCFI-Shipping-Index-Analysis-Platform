"""维基百科 — 全球集装箱港口吞吐量排名（公开统计数据）。"""

import re

from django.conf import settings

from ..fetch_helpers import resolve_data
from .http_client import get_session

CACHE_KEY = 'wikipedia_port_rankings'
CACHE_TTL = 7 * 24 * 3600

# 中文显示名
PORT_ZH = {
    'Shanghai': '上海港',
    'Singapore': '新加坡港',
    'Ningbo': '宁波舟山港',
    'Ningbo-Zhoushan': '宁波舟山港',
    'Shenzhen': '深圳港',
    'Qingdao': '青岛港',
    'Guangzhou': '广州港',
    'Busan': '釜山港',
    'Tianjin': '天津港',
    'Hong Kong': '香港港',
    'Rotterdam': '鹿特丹港',
    'Port Klang': '巴生港',
    'Dubai': '杰贝阿里港',
    'Jebel Ali': '杰贝阿里港',
    'Antwerp': '安特卫普港',
    'Antwerp-Bruges': '安特卫普港',
    'Los Angeles': '洛杉矶港',
    'Long Beach': '长滩港',
    'Hamburg': '汉堡港',
    'Sydney': '悉尼港',
}


def fetch_port_rankings(force_refresh: bool = False) -> list:
    return resolve_data(
        CACHE_KEY,
        _fetch_port_rankings_from_web,
        force_refresh=force_refresh,
        ttl=CACHE_TTL,
        source='wikipedia',
    )


def _fetch_port_rankings_from_web() -> list:
    session = get_session()
    resp = session.get(
        settings.DATA_SOURCE_URLS['wikipedia_api'],
        params={
            'action': 'parse',
            'page': 'List_of_busiest_container_ports',
            'prop': 'wikitext',
            'format': 'json',
        },
    )
    resp.raise_for_status()
    wikitext = resp.json()['parse']['wikitext']['*']
    rankings = _parse_wikitext(wikitext)
    if len(rankings) < 5:
        rankings = _fallback_rankings()
    return rankings


def _parse_wikitext(text: str) -> list:
    rankings = []
    year_cols = {}
    header_done = False

    for line in text.split('\n'):
        if line.startswith('|-'):
            header_done = False
            continue
        if '! ' in line and 'TEU' in line:
            parts = [p.strip() for p in line.split('!!')]
            for i, p in enumerate(parts):
                m = re.search(r'(\d{4}).*?TEU', p, re.I)
                if m:
                    year_cols[i] = int(m.group(1))
            header_done = True
            continue
        if not line.startswith('|') or not header_done:
            continue
        if 'style=' in line and 'background' in line:
            continue

        cells = [c.strip() for c in line.split('||')]
        if len(cells) < 4:
            continue

        rank_match = re.search(r'(\d+)', cells[0])
        if not rank_match:
            continue
        rank = int(rank_match.group(1))

        port_raw = re.sub(r'\[\[([^|\]]+)\|?[^\]]*\]\]', r'\1', cells[1])
        port_raw = re.sub(r'\[\[([^\]]+)\]\]', r'\1', port_raw)
        port_name = port_raw.split('(')[0].strip()

        teu = None
        growth = None
        for cell in reversed(cells):
            num = re.search(r'([\d,.]+)\s*(million)?', cell, re.I)
            if num and teu is None:
                val = float(num.group(1).replace(',', ''))
                if num.group(2) or val < 200:
                    val = int(val * 1_000_000)
                else:
                    val = int(val * 1000) if val < 50000 else int(val)
                teu = val
            pct = re.search(r'([+\-]?\d+\.?\d*)\s*%', cell)
            if pct and growth is None:
                growth = float(pct.group(1)) / 100

        if teu is None:
            continue

        zh_name = PORT_ZH.get(port_name, f'{port_name}港' if not port_name.endswith('港') else port_name)
        rankings.append({
            'rank': rank,
            'port_name': zh_name,
            'port_name_en': port_name,
            'annual_teu': teu,
            'growth_rate': growth if growth is not None else 0.0,
            'data_year': max(year_cols.values()) if year_cols else 2024,
        })

    rankings.sort(key=lambda x: x['annual_teu'], reverse=True)
    for i, item in enumerate(rankings):
        item['rank'] = i + 1
    return rankings[:50]


def _fallback_rankings() -> list:
    """Lloyd's List 2024 公开排名摘要（百万 TEU）。"""
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
            'growth_rate': 0.0,
            'data_year': 2024,
        }
        for i, (name, teu) in enumerate(raw)
    ]
