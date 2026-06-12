from django.contrib import admin

from .models import DataCache


@admin.register(DataCache)
class DataCacheAdmin(admin.ModelAdmin):
    list_display = ('key', 'source', 'fetched_at')
    search_fields = ('key', 'source')
    readonly_fields = ('fetched_at',)
