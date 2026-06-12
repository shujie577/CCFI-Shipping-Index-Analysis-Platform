"""航运界 ship.sh 新闻：优先公开 API，失败时解析首页 HTML。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .http_client import get_session

SHIP_SH_BASE = 'https://www.ship.sh'
SHIP_SH_API = f'{SHIP_SH_BASE}/api/articles'
SOURCE_NAME = '航运界'

CATEGORY_KEYWORDS = {
    '运价动态': ['运价', 'index', 'scfi', 'ccfi', 'bdi'],
    '港口新闻': ['港口', '码头', '港区', '运河'],
    '政策法规': ['法规', '海商法', 'imo', '政策'],
    '市场分析': ['市场', '原油', '采购', '分析'],
    '技术创新': ['绿色', '低碳', '数字化', 'lng', '智能'],
}

RELATIVE_TIME = [
    (re.compile(r'(\d+)分钟前'), lambda n: timedelta(minutes=n)),
    (re.compile(r'(\d+)小时前'), lambda n: timedelta(hours=n)),
    (re.compile(r'(\d+)天前'), lambda n: timedelta(days=n)),
]
ABS_TIME = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日')


def pull_ship_sh_news(limit: int = 10) -> list:
    session = get_session()
    entries = _pull_from_api(session, limit)
    if not entries:
        entries = _pull_from_homepage(session, limit)
    entries.sort(key=lambda x: x['publish_time'], reverse=True)
    return entries[:limit]


def _pull_from_api(session, limit: int) -> list:
    try:
        resp = session.get(
            SHIP_SH_API,
            params={
                'pagination[pageSize]': limit,
                'sort[0]': 'publishedAt:desc',
                'populate[category]': '*',
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    items = []
    for row in payload.get('data') or []:
        entry = _entry_from_api_row(row)
        if entry:
            items.append(entry)
    return items


def _entry_from_api_row(row: dict) -> dict | None:
    attrs = row.get('attributes') or {}
    title = _clean(attrs.get('title'))
    slug = (attrs.get('slug') or '').strip()
    if not title or not slug:
        return None

    content = _clean(attrs.get('content') or '')
    summary = _clean(attrs.get('summary') or '') or _excerpt(content) or title
    category = _category_from_api(attrs) or _guess_category(f'{title} {summary}')
    published = _parse_api_time(attrs.get('publishedAt') or attrs.get('createdAt'))
    url = f'{SHIP_SH_BASE}/articles/{slug}'
    view_count = int(attrs.get('viewCount') or 0)

    return _make_entry(
        title=title,
        url=url,
        summary=summary,
        content=content or summary,
        category=category,
        published=published,
        external_id=f'shipsh:{slug}',
        view_count=view_count,
    )


def _pull_from_homepage(session, limit: int) -> list:
    try:
        resp = session.get(SHIP_SH_BASE + '/', timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    seen = set()
    items = []

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not re.search(r'/articles/[a-zA-Z0-9_-]+', href):
            continue
        full_url = urljoin(SHIP_SH_BASE, href)
        slug = full_url.rstrip('/').split('/')[-1]
        if slug in seen:
            continue

        parsed = _parse_home_link_text(a.get_text(' ', strip=True))
        if not parsed:
            continue
        seen.add(slug)
        title, category, published = parsed
        items.append(_make_entry(
            title=title,
            url=full_url,
            summary=title,
            content=title,
            category=category,
            published=published,
            external_id=f'shipsh:{slug}',
            view_count=0,
        ))
        if len(items) >= limit:
            break

    return items


def _parse_home_link_text(text: str) -> tuple[str, str, datetime] | None:
    raw = _clean(text)
    if len(raw) < 8:
        return None

    published = timezone.now()
    for pat, builder in RELATIVE_TIME:
        m = pat.search(raw)
        if m:
            published = timezone.now() - builder(int(m.group(1)))
            raw = pat.sub('', raw).strip()
            break
    else:
        m = ABS_TIME.search(raw)
        if m:
            published = timezone.make_aware(datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3))
            ))
            raw = ABS_TIME.sub('', raw).strip()

    category = '行业动态'
    for name in ('行业动态', '市场分析', '专栏文章', '主题活动', '港口资讯', '政策法规', '技术创新', '绿色航运'):
        if raw.startswith(name):
            category = name.replace('专栏文章', '市场分析').replace('主题活动', '行业动态')
            raw = raw[len(name):].strip()
            break

    title = raw.strip(' ·|')
    if len(title) < 6:
        return None
    return title, category, published


def _category_from_api(attrs: dict) -> str:
    cat = attrs.get('category') or {}
    data = cat.get('data') if isinstance(cat, dict) else None
    if not data:
        return ''
    name = _clean((data.get('attributes') or {}).get('name'))
    if name == '专栏文章':
        return '市场分析'
    if name == '主题活动':
        return '行业动态'
    return name or ''


def _parse_api_time(value: str | None) -> datetime:
    dt = parse_datetime(value or '')
    if not dt:
        return timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _excerpt(text: str, max_len: int = 200) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + '…'


def _guess_category(text: str) -> str:
    lower = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in lower for k in keys):
            return cat
    return '行业动态'


def _guess_impact(text: str) -> str:
    lower = text.lower()
    high = ['战争', '红海', '制裁', '袭击', '危机', '中断', '暴涨', 'war', 'strike', 'blockade']
    low = ['报告', '分析', 'outlook', 'report', '专栏']
    if any(w in lower for w in high):
        return 'high'
    if any(w in lower for w in low):
        return 'low'
    return 'medium'


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def _make_entry(
    *,
    title: str,
    url: str,
    summary: str,
    content: str,
    category: str,
    published: datetime,
    external_id: str,
    view_count: int,
) -> dict:
    text = f'{title} {summary}'
    return {
        'external_id': external_id,
        'title': title,
        'summary': summary,
        'content': content,
        'category': category,
        'impact': _guess_impact(text),
        'publish_time': published,
        'source': SOURCE_NAME,
        'url': url[:1000],
        'view_count': view_count,
    }
