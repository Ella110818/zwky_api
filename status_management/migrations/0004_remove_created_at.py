# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("status_management", "0003_status_created_at"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="status",
            name="created_at",
        ),
    ] 