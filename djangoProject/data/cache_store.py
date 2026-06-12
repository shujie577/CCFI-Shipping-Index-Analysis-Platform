from django.utils import timezone

from .models import DataCache

REJECT_WHEN_LIVE = frozenset({'local_seed'})


def get_cache_row(key: str):
    try:
        return DataCache.objects.get(key=key)
    except DataCache.DoesNotExist:
        return None


def get_cached(key: str, max_age_seconds: int | None = None, reject_sources: frozenset | set | None = None):
    row = get_cache_row(key)
    if row is None:
        return None
    if reject_sources and row.source in reject_sources:
        return None
    if max_age_seconds is not None:
        age = (timezone.now() - row.fetched_at).total_seconds()
        if age > max_age_seconds:
            return None
    return row.payload


def set_cached(key: str, payload, source: str = ''):
    DataCache.objects.update_or_create(
        key=key,
        defaults={'payload': payload, 'source': source},
    )
    return payload


def get_cached_or_raise(key: str):
    payload = get_cached(key)
    if payload is None:
        raise LookupError(f'无缓存数据: {key}')
    return payload


def clear_seed_cache():
    return DataCache.objects.filter(source='local_seed').delete()[0]
