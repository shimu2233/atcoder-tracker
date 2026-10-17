import requests
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone as django_timezone
from logs.models import ContestAttempt, Log, Problem, SubmissionSyncState
import math

SYNC_COOLDOWN = timedelta(minutes=5)


def sync_submissions(user):
    """Reserve a user's sync before making any external requests."""
    with transaction.atomic():
        locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
        atcoder_name = (locked_user.atcoder_username or "").strip()
        if not atcoder_name:
            return {"code": "missing_username", "error": "AtCoderユーザー名が設定されていません"}
        state, _ = SubmissionSyncState.objects.get_or_create(user=locked_user)
        now = django_timezone.now()
        acquired = SubmissionSyncState.objects.filter(
            pk=state.pk, is_running=False,
        ).filter(
            Q(last_started_at__isnull=True)
            | Q(last_started_at__lte=now - SYNC_COOLDOWN)
        ).update(is_running=True, last_started_at=now)
        if not acquired:
            state.refresh_from_db()
            if state.is_running:
                return {"code": "already_running", "error": "同期を実行中です。完了までお待ちください。"}
            retry_at = state.last_started_at + SYNC_COOLDOWN
            display_time = retry_at.astimezone(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")
            return {
                "code": "cooldown", "retry_at": retry_at,
                "error": f"次回の同期は{display_time}（日本時間）以降に実行できます。",
            }

    try:
        return _fetch_and_save_submissions(locked_user, atcoder_name)
    except (requests.RequestException, ValueError):
        return {"code": "fetch_failed", "error": "提出履歴を取得できませんでした。時間をおいて再実行してください。"}
    finally:
        SubmissionSyncState.objects.filter(pk=state.pk).update(is_running=False)


def change_atcoder_username(user, new_name):
    """Serialize account changes with sync reservations on the same user row."""
    new_name = (new_name or "").strip()
    with transaction.atomic():
        locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
        old_name = (locked_user.atcoder_username or "").strip()
        if old_name != new_name:
            state, _ = SubmissionSyncState.objects.get_or_create(user=locked_user)
            if state.is_running:
                return {"error": "同期実行中はAtCoderユーザー名を変更できません。"}
            Log.objects.filter(user=locked_user).delete()
            ContestAttempt.objects.filter(user=locked_user).delete()
        locked_user.atcoder_username = new_name or None
        locked_user.save(update_fields=["atcoder_username"])
    return {"code": "success"}


def _fetch_and_save_submissions(user, atcoder_name):
    all_submissions = []
    headers = {"User-Agent": "atcoder-tracker/0.1"}
    params = {"user": atcoder_name, "from_second": 0}
    cnt = 0

    while True:
        response = requests.get(
            "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions",
            params=params, headers=headers, timeout=(5, 30),
        )
        response.raise_for_status()
        submissions = response.json()
        required = {"problem_id", "contest_id", "result", "epoch_second"}
        if not isinstance(submissions, list) or any(
            not isinstance(item, dict)
            or not required.issubset(item)
            or not all(isinstance(item[key], str) for key in ("problem_id", "contest_id", "result"))
            or type(item["epoch_second"]) is not int
            or not 0 <= item["epoch_second"] <= 253402300799
            for item in submissions
        ):
            raise ValueError("Invalid submissions response")
        all_submissions.extend(submissions)
        if len(submissions) < 500:
            break
        last = max(submissions, key=lambda s: s["epoch_second"])
        params["from_second"] = last["epoch_second"] + 1
        time.sleep(1)
        cnt += 1
        if cnt == 100:
            raise ValueError("Submission pagination limit reached")

    problem_dictionary = {}
    for s in all_submissions:
        problem_dictionary.setdefault(s["problem_id"], []).append(s)

    created_count = 0
    updated_count = 0
    for problem_id, subs in problem_dictionary.items():
        is_correct = any(s["result"] == "AC" for s in subs)
        ac_subs = [s for s in subs if s["result"] == "AC"]
        last_second = max(s["epoch_second"] for s in subs)
        last_submitted_date = datetime.fromtimestamp(last_second, tz=timezone.utc)
        if ac_subs:
            first_second = min(s["epoch_second"] for s in ac_subs)
            first_ac_date = datetime.fromtimestamp(first_second, tz=timezone.utc)
        else:
            first_ac_date = None

        try:
            problem = Problem.objects.get(problem_id=problem_id)
        except Problem.DoesNotExist:
            continue

        log, created = Log.objects.update_or_create(
            user=user,
            problem=problem,
            defaults={
                "submitted_contest_id": subs[0]["contest_id"],
                "is_correct": is_correct,
                "first_ac_date": first_ac_date,
                "last_submitted_date": last_submitted_date,
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

        submissions_by_contest = {}
        for submission in subs:
            submissions_by_contest.setdefault(submission["contest_id"], []).append(
                submission
            )
        for contest_id, contest_submissions in submissions_by_contest.items():
            contest_ac_submissions = [
                submission
                for submission in contest_submissions
                if submission["result"] == "AC"
            ]
            contest_last_second = max(
                submission["epoch_second"] for submission in contest_submissions
            )
            contest_first_ac_date = None
            if contest_ac_submissions:
                contest_first_ac_date = datetime.fromtimestamp(
                    min(
                        submission["epoch_second"]
                        for submission in contest_ac_submissions
                    ),
                    tz=timezone.utc,
                )
            ContestAttempt.objects.update_or_create(
                user=user,
                problem=problem,
                submitted_contest_id=contest_id,
                defaults={
                    "is_correct": bool(contest_ac_submissions),
                    "first_ac_date": contest_first_ac_date,
                    "last_submitted_date": datetime.fromtimestamp(
                        contest_last_second,
                        tz=timezone.utc,
                    ),
                },
            )

    return {"code": "success", "created": created_count, "updated": updated_count}



def correct_difficulty(difficulty):
    if difficulty is None:
        return None
    if difficulty >= 400:
        return round(difficulty)
    return round(400 / math.exp(1 - difficulty / 400))
