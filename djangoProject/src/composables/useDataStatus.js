/** 解析 API 返回的数据来源标注，供页面展示。 */
export function pickDataStatus(payload) {
  if (!payload || typeof payload !== 'object') return null
  const note = payload.data_note || ''
  if (!note && !payload.cache_fallback && !payload.from_cache) return null
  return {
    live: !!payload.live,
    fromCache: !!payload.from_cache,
    cacheFallback: !!payload.cache_fallback,
    status: payload.data_status || '',
    note,
    fetchedAt: payload.fetched_at || '',
    cacheFetchedAt: payload.cache_fetched_at || '',
  }
}

export function statusTagType(status) {
  if (status?.cacheFallback) return 'warning'
  if (status?.fromCache) return 'info'
  return 'success'
}
