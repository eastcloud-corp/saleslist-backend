# Generated migration - ClientDmCandidate for DM候補保存

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0002_add_company_info_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientDmCandidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("results", models.JSONField(default=list, verbose_name="生成結果（4件: GPT-A/B, Gemini-A/B）")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dm_candidates",
                        to="clients.client",
                        verbose_name="クライアント",
                    ),
                ),
            ],
            options={
                "verbose_name": "クライアントDM候補",
                "verbose_name_plural": "クライアントDM候補",
                "db_table": "client_dm_candidates",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="clientdmcandidate",
            index=models.Index(fields=["client"], name="client_dm_cand_client_idx"),
        ),
    ]
