from django.urls import path
from .views import NewsView, NewsDetailView, NewsSyncView

urlpatterns = [
    path('list/', NewsView.as_view(), name='news-list'),
    path('sync/', NewsSyncView.as_view(), name='news-sync'),
    path('<int:news_id>/', NewsDetailView.as_view(), name='news-detail'),
]