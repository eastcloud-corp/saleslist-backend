from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0002_company_business_description_company_capital_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='facebook_data_synced_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Facebook同期日時'),
        ),
        migrations.AddField(
            model_name='company',
            name='facebook_friend_count',
            field=models.IntegerField(blank=True, null=True, verbose_name='Facebook友だち数'),
        ),
        migrations.AddField(
            model_name='company',
            name='facebook_latest_post_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Facebook最新投稿日時'),
        ),
        migrations.AddField(
            model_name='company',
            name='facebook_page_id',
            field=models.CharField(blank=True, max_length=128, verbose_name='FacebookページID'),
        ),
        migrations.AddField(
            model_name='company',
            name='latest_activity_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='最新アクティビティ時刻'),
        ),
        migrations.CreateModel(
            name='CompanyFacebookSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('friend_count', models.IntegerField(blank=True, null=True, verbose_name='友だち数')),
                ('friend_count_fetched_at', models.DateTimeField(blank=True, null=True, verbose_name='友だち数取得時刻')),
                ('latest_posted_at', models.DateTimeField(blank=True, null=True, verbose_name='最新投稿時刻')),
                ('latest_post_fetched_at', models.DateTimeField(blank=True, null=True, verbose_name='最新投稿取得時刻')),
                ('source', models.CharField(default='celery', max_length=50, verbose_name='取得元')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('company', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='facebook_snapshots', to='companies.company', verbose_name='企業')),
            ],
            options={
                'verbose_name': 'Facebookスナップショット',
                'verbose_name_plural': 'Facebookスナップショット',
                'db_table': 'company_facebook_snapshots',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['latest_activity_at'], name='companies_latest_activity_idx'),
        ),
        migrations.AddIndex(
            model_name='companyfacebooksnapshot',
            index=models.Index(fields=['company', 'created_at'], name='company_facebook_snapshots_company_created_idx'),
        ),
    ]
