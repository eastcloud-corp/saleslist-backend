# Generated migration file - add company info fields to Client model
# Run: python manage.py migrate clients

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='contact_person_position',
            field=models.CharField(blank=True, max_length=100, verbose_name='担当者役職'),
        ),
        migrations.AddField(
            model_name='client',
            name='facebook_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='Facebookリンク'),
        ),
        migrations.AddField(
            model_name='client',
            name='employee_count',
            field=models.IntegerField(blank=True, null=True, verbose_name='従業員数'),
        ),
        migrations.AddField(
            model_name='client',
            name='revenue',
            field=models.BigIntegerField(blank=True, null=True, verbose_name='売上規模'),
        ),
        migrations.AddField(
            model_name='client',
            name='prefecture',
            field=models.CharField(blank=True, max_length=10, verbose_name='都道府県'),
        ),
    ]

