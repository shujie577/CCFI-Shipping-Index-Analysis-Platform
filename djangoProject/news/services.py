from django.conf import settings
from django.utils import timezone

from data.providers.ship_sh import pull_ship_sh_news
from data.fetch_meta import format_cache_time

from .models import NewsArticle

# 首页展示条数（列表高度适中）
DISPLAY_LIMIT = getattr(settings, 'NEWS_HOME_DISPLAY_LIMIT', 8)


def sync_news_from_sources() -> int:
    """从航运界 ship.sh 拉取并写入数据库，已存在的不重复。返回本次新增条数。"""
    entries = pull_ship_sh_news()
    created = 0
    for entry in entries:
        _, is_new = NewsArticle.objects.update_or_create(
            external_id=entry['external_id'],
            defaults={
                'title': entry['title'],
                'summary': entry['summary'],
                'content': entry['content'],
                'category': entry['category'],
                'impact': entry['impact'],
                'source': entry['source'],
                'url': entry['url'],
                'view_count': entry.get('view_count', 0),
                'publish_time': entry['publish_time'],
            },
        )
        if is_new:
            created += 1
    return created


def get_accumulated_news(limit: int = DISPLAY_LIMIT, offset: int = 0, *, sync_live: bool = False) -> dict:
    """
    累计新闻库：sync_live 时先从航运界拉取，再返回最新 limit 条。
    拉取失败时回退库内数据并标注 cache_fallback。
    """
    synced_at = None
    new_count = 0
    sync_failed = False
    data_note = ''
    cache_fetched_at = None

    if sync_live or NewsArticle.objects.count() == 0:
        try:
            new_count = sync_news_from_sources()
            synced_at = timezone.now()
        except Exception as exc:
            sync_failed = True
            data_note = f'航运界新闻拉取失败，已显示本地库内数据：{exc}'
            latest = NewsArticle.objects.order_by('-first_seen_at').first()
            if latest:
                cache_fetched_at = format_cache_time(latest.first_seen_at)

    qs = NewsArticle.objects.all()
    total = qs.count()
    articles = list(qs[offset:offset + limit])

    if sync_failed and total == 0:
        raise RuntimeError(data_note.replace('已显示本地库内数据：', ''))

    return {
        'news': [a.to_dict() for a in articles],
        'total': total,
        'new_count': new_count,
        'synced_at': synced_at.isoformat() if synced_at else None,
        'display_limit': limit,
        'live': bool(synced_at and not sync_failed),
        'from_cache': sync_failed,
        'cache_fallback': sync_failed,
        'data_status': 'cache_fallback' if sync_failed else ('live' if synced_at else 'database'),
        'data_note': data_note,
        'cache_fetched_at': cache_fetched_at,
    }


def get_article_by_id(news_id: int):
    try:
        return NewsArticle.objects.get(pk=news_id)
    except NewsArticle.DoesNotExist:
        return None
