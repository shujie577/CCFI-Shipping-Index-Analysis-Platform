from django.contrib import admin

from .models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'category', 'publish_time', 'first_seen_at')
    list_filter = ('category', 'source', 'impact')
    search_fields = ('title', 'summary')
    readonly_fields = ('external_id', 'first_seen_at')
