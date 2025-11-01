from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('companies', '0003_company_facebook_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyUpdateCandidate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=100, verbose_name='対象フィールド')),
                ('candidate_value', models.TextField(verbose_name='候補値')),
                ('value_hash', models.CharField(blank=True, max_length=128, verbose_name='値ハッシュ')),
                ('source_type', models.CharField(choices=[('RULE', 'Rule'), ('AI', 'AI'), ('MANUAL', 'Manual')], default='RULE', max_length=16, verbose_name='取得ソース種別')),
                ('source_detail', models.CharField(blank=True, max_length=255, verbose_name='ソース詳細')),
                ('confidence', models.PositiveSmallIntegerField(default=100, verbose_name='確信度')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('merged', 'Merged'), ('rejected', 'Rejected'), ('expired', 'Expired')], default='pending', max_length=16, verbose_name='ステータス')),
                ('collected_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='取得日時')),
                ('merged_at', models.DateTimeField(blank=True, null=True, verbose_name='反映日時')),
                ('rejected_at', models.DateTimeField(blank=True, null=True, verbose_name='否認日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='update_candidates', to='companies.company', verbose_name='企業')),
            ],
            options={
                'verbose_name': '企業補完候補',
                'verbose_name_plural': '企業補完候補',
                'db_table': 'company_update_candidates',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompanyReviewBatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_review', 'In Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('partial', 'Partial')], default='pending', max_length=16, verbose_name='ステータス')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_company_review_batches', to=settings.AUTH_USER_MODEL, verbose_name='担当者')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_batches', to='companies.company', verbose_name='企業')),
            ],
            options={
                'verbose_name': '企業レビュー',
                'verbose_name_plural': '企業レビュー',
                'db_table': 'company_review_batches',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompanyUpdateHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=100, verbose_name='対象フィールド')),
                ('old_value', models.TextField(blank=True, verbose_name='旧値')),
                ('new_value', models.TextField(blank=True, verbose_name='新値')),
                ('source_type', models.CharField(choices=[('RULE', 'Rule'), ('AI', 'AI'), ('MANUAL', 'Manual')], default='RULE', max_length=16, verbose_name='ソース種別')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='承認日時')),
                ('comment', models.TextField(blank=True, verbose_name='コメント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_company_updates', to=settings.AUTH_USER_MODEL, verbose_name='承認者')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='update_history', to='companies.company', verbose_name='企業')),
            ],
            options={
                'verbose_name': '企業更新履歴',
                'verbose_name_plural': '企業更新履歴',
                'db_table': 'company_update_history',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompanyReviewItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=100, verbose_name='対象フィールド')),
                ('current_value', models.TextField(blank=True, verbose_name='現在値')),
                ('candidate_value', models.TextField(verbose_name='候補値')),
                ('confidence', models.PositiveSmallIntegerField(default=100, verbose_name='確信度')),
                ('decision', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('updated', 'Updated')], default='pending', max_length=16, verbose_name='判断')),
                ('comment', models.TextField(blank=True, verbose_name='コメント')),
                ('decided_at', models.DateTimeField(blank=True, null=True, verbose_name='判断日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='companies.companyreviewbatch', verbose_name='レビュー')),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='review_items', to='companies.companyupdatecandidate', verbose_name='候補')),
                ('decided_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='decided_company_review_items', to=settings.AUTH_USER_MODEL, verbose_name='決裁者')),
            ],
            options={
                'verbose_name': '企業レビュー項目',
                'verbose_name_plural': '企業レビュー項目',
                'db_table': 'company_review_items',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='companyupdatecandidate',
            index=models.Index(fields=['company', 'field'], name='company_upd_company_575986_idx'),
        ),
        migrations.AddIndex(
            model_name='companyupdatecandidate',
            index=models.Index(fields=['status'], name='company_upd_status_d6483b_idx'),
        ),
        migrations.AddIndex(
            model_name='companyupdatecandidate',
            index=models.Index(fields=['source_type'], name='company_upd_source__fc818a_idx'),
        ),
        migrations.AddIndex(
            model_name='companyreviewbatch',
            index=models.Index(fields=['status'], name='company_re_status_67a29a_idx'),
        ),
        migrations.AddIndex(
            model_name='companyreviewbatch',
            index=models.Index(fields=['company'], name='company_re_company_4d93a7_idx'),
        ),
        migrations.AddIndex(
            model_name='companyreviewitem',
            index=models.Index(fields=['batch'], name='company_re_batch_i_62b0ee_idx'),
        ),
        migrations.AddIndex(
            model_name='companyreviewitem',
            index=models.Index(fields=['decision'], name='company_re_decisio_0b7ffb_idx'),
        ),
        migrations.AddIndex(
            model_name='companyupdatehistory',
            index=models.Index(fields=['company', 'field'], name='company_upd_company_a908b8_idx'),
        ),
    ]
