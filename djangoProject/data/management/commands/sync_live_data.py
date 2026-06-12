from django.core.management.base import BaseCommand

from data.services import warm_all_caches


class Command(BaseCommand):
    help = '从公开数据源同步运价指数、新闻、港口排名等真实数据到本地缓存'

    def handle(self, *args, **options):
        self.stdout.write('正在拉取外部数据（可能需要 30–60 秒）...')
        try:
            warm_all_caches()
            self.stdout.write(self.style.SUCCESS('同步完成。'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'同步部分失败: {exc}'))
            raise
