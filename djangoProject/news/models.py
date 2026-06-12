from django.db import models


class NewsArticle(models.Model):
    """RSS 拉取后持久化，只增不删（累计新闻库）。"""

    external_id = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    category = models.CharField(max_length=32, default='行业动态')
    impact = models.CharField(max_length=16, default='medium')
    source = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    view_count = models.IntegerField(default=0)
    publish_time = models.DateTimeField(db_index=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-publish_time']
        verbose_name = '航运新闻'
        verbose_name_plural = '航运新闻'

    def __str__(self):
        return self.title[:60]

    def to_dict(self):
        return {
            'id': self.pk,
            'title': self.title,
            'summary': self.summary,
            'category': self.category,
            'impact': self.impact,
            'publish_time': self.publish_time.strftime('%Y-%m-%d %H:%M:%S'),
            'views': self.view_count,
            'content': self.content or self.summary,
            'source': self.source,
            'url': self.url,
        }
