from django.db import migrations, models
import django.db.models.deletion


def copy_existing_logs(apps, schema_editor):
    Log = apps.get_model("logs", "Log")
    ContestAttempt = apps.get_model("logs", "ContestAttempt")
    ContestAttempt.objects.bulk_create(
        [
            ContestAttempt(
                user_id=log.user_id,
                problem_id=log.problem_id,
                submitted_contest_id=log.submitted_contest_id,
                is_correct=log.is_correct,
                first_ac_date=log.first_ac_date,
                last_submitted_date=log.last_submitted_date,
            )
            for log in Log.objects.all().iterator()
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("logs", "0009_contest_contestproblem"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContestAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitted_contest_id", models.CharField(max_length=100)),
                ("is_correct", models.BooleanField(default=False)),
                ("first_ac_date", models.DateTimeField(blank=True, null=True)),
                ("last_submitted_date", models.DateTimeField()),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="logs.problem")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="accounts.customuser")),
            ],
        ),
        migrations.AddConstraint(
            model_name="contestattempt",
            constraint=models.UniqueConstraint(
                fields=("user", "problem", "submitted_contest_id"),
                name="unique_user_problem_contest_attempt",
            ),
        ),
        migrations.RunPython(copy_existing_logs, migrations.RunPython.noop),
    ]
