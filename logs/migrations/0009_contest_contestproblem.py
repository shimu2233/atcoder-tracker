from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("logs", "0008_dolater"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contest",
            fields=[
                ("contest_id", models.CharField(max_length=100, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=300)),
                ("start_epoch_second", models.BigIntegerField(default=0)),
                ("duration_second", models.BigIntegerField(default=0)),
                ("rate_change", models.CharField(blank=True, default="-", max_length=50)),
                ("series", models.CharField(default="OTHER", max_length=30)),
                ("contest_format", models.CharField(default="ALGORITHM", max_length=20)),
                ("is_evergreen", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="ContestProblem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("problem_index", models.CharField(blank=True, default="", max_length=50)),
                ("contest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contest_problems", to="logs.contest")),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contest_problems", to="logs.problem")),
            ],
            options={"ordering": ["problem_index", "problem_id"]},
        ),
        migrations.AddConstraint(
            model_name="contestproblem",
            constraint=models.UniqueConstraint(fields=("contest", "problem"), name="unique_contest_problem"),
        ),
    ]
