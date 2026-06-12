"""请求是否要求跳过缓存、拉取最新数据。"""

from __future__ import annotations

from .fetch_meta import FetchMeta, attach_fetch_meta


def wants_live(request) -> bool:
    if request is None:
        return False
    value = str(request.query_params.get('refresh', '')).lower()
    return value in ('1', 'true', 'yes', 'on')


def enrich_with_fetch_meta(payload: dict, meta: FetchMeta, request) -> dict:
    """将 FetchMeta 写入 API 响应（保留业务字段）。"""
    return attach_fetch_meta(payload, meta, requested_live=wants_live(request))


def meta_response(extra: dict | None = None, *, live: bool, fetched_at: str) -> dict:
    payload = {'live': live, 'fetched_at': fetched_at}
    if extra:
        payload.update(extra)
    return payload
