from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from .contest_classification import classify_contest


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


def goal_window(goal):
    return (
        datetime.combine(goal.start_date, time.min, tzinfo=JST),
        datetime.combine(goal.end_date + timedelta(days=1), time.min, tzinfo=JST),
    )


def calculate_goal_progress(goal, persist_achievement=True):
    records = list(goal.ac_records.order_by("ac_date", "problem_id"))
    completed_count = len(records)
    is_achieved = completed_count >= goal.target_count
    if persist_achievement:
        achieved_at = records[goal.target_count - 1].ac_date if is_achieved else None
        if achieved_at != goal.achieved_at:
            goal.achieved_at = achieved_at
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
