from django.db import models


class DataCache(models.Model):
    """缓存从外部源拉取的数据，网络失败时仍可返回最近一次真实数据。"""

    key = models.CharField(max_length=128, unique=True)
    payload = models.JSONField(default=dict)
    source = models.CharField(max_length=64, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '数据缓存'
        verbose_name_plural = '数据缓存'

    def __str__(self):
        return f'{self.key} @ {self.fetched_at:%Y-%m-%d %H:%M}'
