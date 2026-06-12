import request from './index'

export default {
    getNewsList(limit = 20, offset = 0, refresh = false) {
        return request.get('/news/list/', {
            params: { limit, offset, ...(refresh ? { refresh: 1 } : {}) }
        })
    },
    getNewsDetail(id) {
        return request.get(`/news/${id}/`)
    },
    syncNews() {
        return request.post('/news/sync/')
    }
}
