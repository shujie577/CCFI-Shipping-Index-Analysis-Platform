import request from './index'

export default {
    getRealtimeRate(routeLabel, refresh = false) {
        return request.get('/freight/realtime-rate/', {
            params: { route_label: routeLabel, ...(refresh ? { refresh: 1 } : {}) },
            skipAuthRedirect: true,
        })
    },
    getCcfiRoutes() {
        return request.get('/freight/port-pairs/')
    },
    getAvailablePorts() {
        return request.get('/freight/available-ports/')
    },
    getHistoricalRates(routeLabel, refresh = false) {
        return request.get('/freight/historical-rates/', {
            params: { route_label: routeLabel, ...(refresh ? { refresh: 1 } : {}) },
            skipAuthRedirect: true,
        })
    },
    getCcfiRouteTable(refresh = false) {
        return request.get('/freight/ccfi-routes/', {
            params: refresh ? { refresh: 1 } : {}
        })
    }
}
