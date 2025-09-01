# Generated manually for sales history expansion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_projectcompany_appointment_count_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_company', models.ForeignKey(on_delete=models.CASCADE, related_name='sales_history', to='projects.projectcompany', verbose_name='案件企業')),
                ('status', models.CharField(max_length=50, verbose_name='営業ステータス')),
                ('status_date', models.DateField(verbose_name='ステータス日付')),
                ('staff_name', models.CharField(blank=True, max_length=100, verbose_name='担当者')),
                ('notes', models.TextField(blank=True, verbose_name='履歴メモ')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
            ],
            options={
                'verbose_name': '営業履歴',
                'verbose_name_plural': '営業履歴',
                'db_table': 'sales_history',
                'ordering': ['-status_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='saleshistory',
            index=models.Index(fields=['project_company'], name='sales_history_project_company_idx'),
        ),
        migrations.AddIndex(
            model_name='saleshistory',
            index=models.Index(fields=['status'], name='sales_history_status_idx'),
        ),
        migrations.AddIndex(
            model_name='saleshistory',
            index=models.Index(fields=['status_date'], name='sales_history_status_date_idx'),
        ),
    ]