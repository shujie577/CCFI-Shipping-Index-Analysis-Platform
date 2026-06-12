"""外网拉取 / 缓存回退状态，供 API 与前端标注。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class FetchMeta:
    mode: str  # live | cache_ttl | cache_fallback | seed | intranet
    live: bool = False
    from_cache: bool = False
    cache_fallback: bool = False
    fetched_at: str | None = None
    cache_fetched_at: str | None = None
    source: str = ''
    message: str = ''

    def to_api_fields(self) -> dict:
        return {
            'live': self.live,
            'from_cache': self.from_cache,
            'cache_fallback': self.cache_fallback,
            'data_status': self.mode,
            'data_note': self.message,
            'fetched_at': self.fetched_at or self.cache_fetched_at,
            'cache_fetched_at': self.cache_fetched_at,
            'data_source': self.source,
        }


def attach_fetch_meta(payload: dict, meta: FetchMeta, *, requested_live: bool = False) -> dict:
    out = dict(payload)
    out.update(meta.to_api_fields())
    out['requested_live'] = requested_live
    return out


def merge_api_meta(
    payload: dict,
    *,
    requested_live: bool = False,
    live: bool | None = None,
    from_cache: bool = False,
    cache_fallback: bool = False,
    data_status: str = 'live',
    data_note: str = '',
    fetched_at: str | None = None,
    cache_fetched_at: str | None = None,
    data_source: str = '',
) -> dict:
    """视图层手动合并（新闻、看板等）。"""
    out = dict(payload)
    out.update({
        'requested_live': requested_live,
        'live': live if live is not None else (not from_cache and not cache_fallback),
        'from_cache': from_cache,
        'cache_fallback': cache_fallback,
        'data_status': data_status,
        'data_note': data_note,
        'fetched_at': fetched_at or cache_fetched_at,
        'cache_fetched_at': cache_fetched_at,
        'data_source': data_source,
    })
    return out


def format_cache_time(dt) -> str:
    if dt is None:
        return ''
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)[:19]
