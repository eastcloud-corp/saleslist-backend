# Generated manually for Phase 1: 再実行ガード実装
# Date: 2025-01-XX

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0008_company_ai_last_enriched_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='ai_last_enrichment_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('success', '成功'),
                    ('partial', '部分成功'),
                    ('failed', '失敗'),
                    ('skipped', 'スキップ'),
                ],
                max_length=16,
                verbose_name='AI補完最終ステータス',
            ),
        ),
    ]
