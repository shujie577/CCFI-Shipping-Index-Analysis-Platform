from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='DataCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=128, unique=True)),
                ('payload', models.JSONField(default=dict)),
                ('source', models.CharField(blank=True, max_length=64)),
                ('fetched_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '数据缓存',
                'verbose_name_plural': '数据缓存',
            },
        ),
    ]
