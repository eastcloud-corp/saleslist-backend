# Generated manually for Phase 3-③: 再探索戦略の分岐設計
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('companies', '0009_company_ai_last_enrichment_status'),
    ]
    operations = [
        migrations.AddField(
            model_name='company',
            name='next_retry_strategy',
            field=models.CharField(
                blank=True,
                choices=[
                    ('none', '再探索しない'),
                    ('relax_prefecture', '都道府県条件を緩和'),
                    ('name_variant_expansion', '表記揺れを拡張'),
                    ('english_name_search', '英語名で検索'),
                    ('official_site_focused', '公式サイトに集中'),
                ],
                max_length=32,
                null=True,
                verbose_name='次回再探索戦略',
            ),
        ),
    ]
