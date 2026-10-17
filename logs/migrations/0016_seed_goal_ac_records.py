from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import re

from django.db import migrations
from django.db.models import F


# Freeze the previous classification rules for migration reproducibility.
EVERGREEN = {"practice", "APG4b", "APG4bPython", "abs", "practice2", "typical90", "math-and-algorithm", "tessoku-book"}


def seed_records(apps, schema_editor):
    alias = schema_editor.connection.alias
    Log = apps.get_model("logs", "Log")
    Attempt = apps.get_model("logs", "ContestAttempt")
    Goal = apps.get_model("logs", "Goal")
    GoalAC = apps.get_model("logs", "GoalAC")
    Contest = apps.get_model("logs", "Contest")
    for model in (Log, Attempt):
        model.objects.using(alias).filter(first_ac_date__isnull=False, last_ac_date__isnull=True).update(last_ac_date=F("first_ac_date"))
    contests = {c.pk: c for c in Contest.objects.using(alias).all()}

    def contest_type(contest_id):
        contest = contests.get(contest_id)
        if contest:
            if contest.is_evergreen:
                return "EVERGREEN"
            if contest.series == "AGC":
                return "GRAND"
            if contest.contest_format == "HEURISTIC":
                return "HEURISTIC"
        else:
            if contest_id in EVERGREEN:
                return "EVERGREEN"
            if re.fullmatch(r"agc\d{3}", contest_id):
                return "GRAND"
            if re.fullmatch(r"ahc\d{3}", contest_id):
                return "HEURISTIC"
        return "ALGORITHM"

    jst = ZoneInfo("Asia/Tokyo")
    for goal in Goal.objects.using(alias).iterator():
        start = datetime.combine(goal.start_date, time.min, tzinfo=jst)
        end = datetime.combine(goal.end_date + timedelta(days=1), time.min, tzinfo=jst)
        logs = list(Log.objects.using(alias).filter(
            user_id=goal.user_id, first_ac_date__gte=start, first_ac_date__lt=end,
            problem__display_difficulty__gte=goal.difficulty_min,
            problem__display_difficulty__lte=goal.difficulty_max,
        ))
        attempts = defaultdict(list)
        for attempt in Attempt.objects.using(alias).filter(
            user_id=goal.user_id, problem_id__in=[log.problem_id for log in logs],
            is_correct=True, first_ac_date__isnull=False,
        ):
            attempts[attempt.problem_id].append(attempt)
        records = []
        for log in logs:
            ids = {a.submitted_contest_id for a in attempts[log.problem_id] if a.first_ac_date == log.first_ac_date}
            if not ids:
                ids = {log.submitted_contest_id}
            if any(contest_type(cid) in goal.contest_types for cid in ids):
                records.append(GoalAC(goal_id=goal.pk, problem_id=log.problem_id, ac_date=log.first_ac_date))
        GoalAC.objects.using(alias).bulk_create(records, ignore_conflicts=True)
    # Leave submissions_checked=False: repeated ACs need the next API sync.


class Migration(migrations.Migration):
    dependencies = [("logs", "0015_contestattempt_last_ac_date_goal_submissions_checked_and_more")]
    operations = [migrations.RunPython(seed_records, migrations.RunPython.noop)]
