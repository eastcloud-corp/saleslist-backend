# Generated manually for add-industry-category-filter

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0004_auto_20250907_1752'),
    ]

    operations = [
        migrations.AddField(
            model_name='industry',
            name='is_category',
            field=models.BooleanField(default=False, verbose_name='業界カテゴリ'),
        ),
        migrations.AddField(
            model_name='industry',
            name='parent_industry',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sub_industries',
                to='masters.industry',
                verbose_name='親業界'
            ),
        ),
        migrations.AddIndex(
            model_name='industry',
            index=models.Index(fields=['parent_industry'], name='industries_parent__idx'),
        ),
        migrations.AddIndex(
            model_name='industry',
            index=models.Index(fields=['is_category'], name='industries_is_cate_idx'),
        ),
    ]

