from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChatChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_id", models.IntegerField(db_index=True)),
                ("page_type", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=500)),
                ("url", models.CharField(blank=True, max_length=1000)),
                ("heading", models.CharField(blank=True, max_length=500)),
                ("text", models.TextField()),
                ("embedding_json", models.TextField(help_text="JSON array of floats")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Chat chunk",
                "verbose_name_plural": "Chat chunks",
            },
        ),
    ]
