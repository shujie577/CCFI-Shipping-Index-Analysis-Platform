"""统一拉取逻辑：内网模式 / 失败回退缓存。"""

from __future__ import annotations

import logging
from typing import Any, Callable, Tuple

from django.conf import settings
from django.utils import timezone

from .cache_store import REJECT_WHEN_LIVE, get_cache_row, get_cached, set_cached
from .fetch_meta import FetchMeta, format_cache_time

logger = logging.getLogger(__name__)


def intranet_only() -> bool:
    return bool(getattr(settings, 'INTRANET_ONLY', False))


def _meta_from_row(row, *, mode: str, message: str) -> FetchMeta:
    cache_at = format_cache_time(row.fetched_at) if row else None
    return FetchMeta(
        mode=mode,
        live=False,
        from_cache=True,
        cache_fallback=(mode == 'cache_fallback'),
        cache_fetched_at=cache_at,
        source=row.source if row else '',
        message=message,
    )


def resolve_data(
    key: str,
    fetch_func: Callable[[], Any],
    *,
    force_refresh: bool = False,
    ttl: int | None = None,
    source: str = '',
) -> Tuple[Any, FetchMeta]:
    """
    返回 (payload, FetchMeta)。
    - live：本次从外网拉取成功
    - cache_ttl：未 refresh，使用未过期缓存
    - cache_fallback：外网失败，回退本地缓存
    """
    now = timezone.now().isoformat()

    if intranet_only():
        row = get_cache_row(key)
        if row is not None:
            msg = f'内网模式，使用本地缓存（更新于 {format_cache_time(row.fetched_at)}）'
            return row.payload, _meta_from_row(row, mode='intranet', message=msg)
        from .seed_data import get_seed

        seed = get_seed(key)
        if seed is not None:
            set_cached(key, seed, source='local_seed')
            return seed, FetchMeta(
                mode='seed',
                live=False,
                from_cache=True,
                source='local_seed',
                message='内网模式，使用内置示例数据',
                fetched_at=now,
            )
        raise LookupError(f'内网模式无本地数据: {key}')

    if not force_refresh:
        row = get_cache_row(key)
        if row is not None:
            age = (timezone.now() - row.fetched_at).total_seconds()
            if ttl is None or age <= ttl:
                msg = f'缓存数据（更新于 {format_cache_time(row.fetched_at)}）'
                return row.payload, _meta_from_row(row, mode='cache_ttl', message=msg)

    try:
        payload = fetch_func()
        set_cached(key, payload, source=source)
        return payload, FetchMeta(
            mode='live',
            live=True,
            from_cache=False,
            cache_fallback=False,
            source=source,
            message='',
            fetched_at=now,
        )
    except Exception as exc:
        row = get_cache_row(key)
        if row is not None and row.source not in REJECT_WHEN_LIVE:
            logger.warning('外网拉取失败，已回退缓存 key=%s: %s', key, exc)
            msg = (
                f'外网拉取失败，已使用本地缓存（更新于 {format_cache_time(row.fetched_at)}）'
            )
            return row.payload, _meta_from_row(row, mode='cache_fallback', message=msg)
        raise
