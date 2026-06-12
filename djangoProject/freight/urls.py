from django.urls import path
from .views import (
    RealtimeFreightRateView,
    PortPairsView,
    AvailablePortsView,
    HistoricalFreightRatesView,
    CcfiRoutesView,
)

urlpatterns = [
    path('realtime-rate/', RealtimeFreightRateView.as_view(), name='realtime-rate'),
    path('ccfi-routes/', CcfiRoutesView.as_view(), name='ccfi-routes'),
    path('port-pairs/', PortPairsView.as_view(), name='port-pairs'),
    path('available-ports/', AvailablePortsView.as_view(), name='available-ports'),
    path('historical-rates/', HistoricalFreightRatesView.as_view(), name='historical-rates'),
]