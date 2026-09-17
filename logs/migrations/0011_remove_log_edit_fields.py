from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("logs", "0010_contestattempt"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="log",
            name="memo",
        ),
        migrations.RemoveField(
            model_name="log",
            name="do_later",
        ),
    ]
