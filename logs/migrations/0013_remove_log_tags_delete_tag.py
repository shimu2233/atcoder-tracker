from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("logs", "0012_goal"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="log",
            name="tags",
        ),
        migrations.DeleteModel(
            name="Tag",
        ),
    ]
