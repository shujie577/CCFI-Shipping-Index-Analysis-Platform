from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from data.live import wants_live

from .services import get_accumulated_news, get_article_by_id, sync_news_from_sources


class NewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        default_limit = getattr(settings, 'NEWS_HOME_DISPLAY_LIMIT', 8)
        limit = int(request.query_params.get('limit', default_limit))
        offset = int(request.query_params.get('offset', 0))
        live = wants_live(request)

        try:
            result = get_accumulated_news(limit=limit, offset=offset, sync_live=live)
        except Exception as exc:
            return Response(
                {'error': f'无法同步新闻: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        fetched_at = result.get('synced_at') or timezone.now().isoformat()
        return Response({
            'total': result['total'],
            'news': result['news'],
            'new_count': result.get('new_count', 0),
            'requested_live': live,
            'live': result.get('live', False),
            'from_cache': result.get('from_cache', False),
            'cache_fallback': result.get('cache_fallback', False),
            'data_status': result.get('data_status', 'live'),
            'data_note': result.get('data_note', ''),
            'fetched_at': fetched_at,
            'cache_fetched_at': result.get('cache_fetched_at'),
        })


class NewsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, news_id):
        article = get_article_by_id(news_id)
        if not article:
            return Response({'error': '新闻不存在'}, status=status.HTTP_404_NOT_FOUND)
        data = article.to_dict()
        data['live'] = False
        data['from_cache'] = True
        data['data_status'] = 'database'
        data['data_note'] = '来自本地新闻库'
        return Response(data)


class NewsSyncView(APIView):
    """手动触发航运界新闻同步。"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            new_count = sync_news_from_sources()
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        result = get_accumulated_news(limit=1)
        return Response({
            'message': '同步完成',
            'new_count': new_count,
            'total': result['total'],
            'fetched_at': timezone.now().isoformat(),
            'live': True,
            'from_cache': False,
            'cache_fallback': False,
            'data_status': 'live',
            'data_note': '',
        })
