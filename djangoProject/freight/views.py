from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from data.live import wants_live
from .services import ShippingDataService


def _service(request) -> ShippingDataService:
    return ShippingDataService(force_refresh=wants_live(request))


def _finalize_payload(data: dict, request) -> dict:
    """补全 requested_live；业务层已写入 live / data_note 等。"""
    data.setdefault('requested_live', wants_live(request))
    if not data.get('fetched_at'):
        data['fetched_at'] = timezone.now().isoformat()
    return data


class CcfiRoutesView(APIView):
    """航交所 CCFI 单期页全部分航线指数（中国出口集装箱运价指数）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        live = wants_live(request)
        try:
            from data.providers.freight import get_ccfi_route_table
            data = get_ccfi_route_table(force_refresh=live)
        except Exception as exc:
            return Response(
                {'error': f'无法获取 CCFI 指数: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(_finalize_payload(data, request))


class RealtimeFreightRateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        route_label = request.query_params.get('route_label')
        origin = request.query_params.get('origin')
        destination = request.query_params.get('destination')
        if not route_label and (not origin or not destination):
            return Response({'error': '请选择 CCFI 航线'}, status=400)
        live = wants_live(request)
        try:
            if route_label:
                rate = _service(request).get_realtime_ccfi_by_route(route_label)
            else:
                rate = _service(request).get_realtime_freight_rate(origin, destination)
        except Exception as exc:
            return Response(
                {'error': f'无法获取 CCFI 指数: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(_finalize_payload(rate, request))


class PortPairsView(APIView):
    """CCFI 航线列表（综合指数 + 12 条分航线）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_service(request).get_ccfi_route_options())


class AvailablePortsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_service(request).get_available_ports())


class HistoricalFreightRatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        route_label = request.query_params.get('route_label')
        origin = request.query_params.get('origin')
        destination = request.query_params.get('destination')
        days = int(request.query_params.get('days', 90))
        if not route_label and (not origin or not destination):
            return Response({'error': '请选择 CCFI 航线'}, status=400)
        try:
            if route_label:
                data = _service(request).get_historical_ccfi_by_route(route_label, days)
            else:
                data = _service(request).get_historical_freight_rates(origin, destination, days)
        except Exception as exc:
            return Response(
                {'error': f'无法获取历史指数: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        data = _finalize_payload(data, request)
        response = Response(data)
        response['X-Data-Live'] = '1' if data.get('live') else '0'
        response['X-Data-Status'] = data.get('data_status', '')
        response['X-Fetched-At'] = data.get('fetched_at', '')
        return response
