from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from .contest_classification import classify_contest
from .models import Contest, ContestAttempt, Log


JST = ZoneInfo("Asia/Tokyo")
CONTEST_TYPE_LABELS = {
    "EVERGREEN": "常設",
    "ALGORITHM": "アルゴリズム",
    "GRAND": "グランド",
    "HEURISTIC": "ヒューリスティック",
}


def contest_type_for(contest_id, contest=None):
    if contest is None:
        series, contest_format, is_evergreen = classify_contest(contest_id)
    else:
        series = contest.series
        contest_format = contest.contest_format
        is_evergreen = contest.is_evergreen

    if is_evergreen:
        return "EVERGREEN"
    if series == "AGC":
        return "GRAND"
    if contest_format == "HEURISTIC":
        return "HEURISTIC"
    return "ALGORITHM"


def calculate_goal_progress(goal, persist_achievement=True):
    start_at = datetime.combine(goal.start_date, time.min, tzinfo=JST)
    end_at = datetime.combine(
        goal.end_date + timedelta(days=1),
        time.min,
        tzinfo=JST,
    )
    logs = list(
        Log.objects.filter(
            user=goal.user,
            first_ac_date__gte=start_at,
            first_ac_date__lt=end_at,
            problem__display_difficulty__gte=goal.difficulty_min,
            problem__display_difficulty__lte=goal.difficulty_max,
        )
        .select_related("problem")
        .order_by("first_ac_date", "problem_id")
    )

    attempts_by_problem = defaultdict(list)
    if logs:
        for attempt in ContestAttempt.objects.filter(
            user=goal.user,
            problem_id__in=[log.problem_id for log in logs],
            is_correct=True,
            first_ac_date__isnull=False,
        ):
            attempts_by_problem[attempt.problem_id].append(attempt)

    contest_ids = {
        attempt.submitted_contest_id
        for attempts in attempts_by_problem.values()
        for attempt in attempts
    }
    contest_ids.update(log.submitted_contest_id for log in logs)
    contests = Contest.objects.in_bulk(contest_ids)
    selected_types = set(goal.contest_types)
    qualified_logs = []

    for log in logs:
        first_ac_contest_ids = {
            attempt.submitted_contest_id
            for attempt in attempts_by_problem.get(log.problem_id, [])
            if attempt.first_ac_date == log.first_ac_date
        }
        if not first_ac_contest_ids:
            first_ac_contest_ids = {log.submitted_contest_id}

        if any(
            contest_type_for(contest_id, contests.get(contest_id)) in selected_types
            for contest_id in first_ac_contest_ids
        ):
            qualified_logs.append(log)

    completed_count = len(qualified_logs)
    is_achieved = completed_count >= goal.target_count
    if is_achieved and goal.achieved_at is None and persist_achievement:
        goal.achieved_at = qualified_logs[goal.target_count - 1].first_ac_date
        goal.save(update_fields=["achieved_at", "updated_at"])

    today = timezone.localdate(timezone=JST)
    if is_achieved:
        status = "achieved"
        status_label = "達成"
    elif today < goal.start_date:
        status = "upcoming"
        status_label = "開始前"
    elif today > goal.end_date:
        status = "expired"
        status_label = "未達成"
    else:
        status = "active"
        status_label = "挑戦中"

    return {
        "completed_count": completed_count,
        "remaining_count": max(goal.target_count - completed_count, 0),
        "progress_percent": min(round(completed_count / goal.target_count * 100), 100),
        "is_achieved": is_achieved,
        "status": status,
        "status_label": status_label,
        "contest_type_labels": [
            CONTEST_TYPE_LABELS[value]
            for value in goal.contest_types
            if value in CONTEST_TYPE_LABELS
        ],
    }
