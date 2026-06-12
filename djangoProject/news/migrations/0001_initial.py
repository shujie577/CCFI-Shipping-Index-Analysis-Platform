from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='NewsArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(db_index=True, max_length=64, unique=True)),
                ('title', models.CharField(max_length=500)),
                ('summary', models.TextField(blank=True)),
                ('content', models.TextField(blank=True)),
                ('category', models.CharField(default='行业动态', max_length=32)),
                ('impact', models.CharField(default='medium', max_length=16)),
                ('source', models.CharField(blank=True, max_length=100)),
                ('url', models.URLField(blank=True, max_length=1000)),
                ('publish_time', models.DateTimeField(db_index=True)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '航运新闻',
                'verbose_name_plural': '航运新闻',
                'ordering': ['-publish_time'],
            },
        ),
    ]
