import requests
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone as django_timezone
from logs.models import Contest, ContestAttempt, Goal, GoalAC, Log, Problem, SubmissionSyncState
from logs.goal_progress import calculate_goal_progress, contest_type_for, goal_window
from collections import defaultdict
import math
import logging
import re
from bs4 import BeautifulSoup

SYNC_COOLDOWN = timedelta(minutes=5)
SUBMISSION_LOOKBACK_SECONDS = 60 * 60
SUBMISSION_PAGE_LIMIT = 100
logger = logging.getLogger(__name__)


def sync_submissions(user, *, full_refresh=False):
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
        if full_refresh:
            return _fetch_and_save_submissions(locked_user, atcoder_name, full_refresh=True)
        return _fetch_and_save_submissions(locked_user, atcoder_name)
    except UnknownProblemError:
        return {"code": "unknown_problem", "error": "未登録の問題情報をAtCoder公式から取得できなかったため、同期を完了できませんでした。時間をおいて再実行してください。"}
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
            GoalAC.objects.filter(goal__user=locked_user).delete()
            Goal.objects.filter(user=locked_user).update(submissions_checked=False, achieved_at=None)
            state.last_submission_epoch = 0
            state.last_succeeded_at = None
            state.save(update_fields=["last_submission_epoch", "last_succeeded_at"])
        locked_user.atcoder_username = new_name or None
        locked_user.save(update_fields=["atcoder_username"])
    return {"code": "success"}


class UnknownProblemError(ValueError):
    pass


def _fetch_and_save_submissions(user, atcoder_name, *, full_refresh=False):
    state = SubmissionSyncState.objects.get(user=user)
    # Snapshot IDs before fetching. Goals created during this sync are checked next time.
    goals = list(Goal.objects.filter(user=user))
    from_second = 0 if full_refresh else max(
        0, state.last_submission_epoch - SUBMISSION_LOOKBACK_SECONDS,
    )
    for goal in goals:
        if not goal.submissions_checked:
            from_second = min(from_second, int(goal_window(goal)[0].timestamp()))
    submissions = _fetch_submissions(atcoder_name, max(0, from_second))
    # Fetch HTML before opening the save transaction. A failure must not advance the cursor.
    missing_problems = _fetch_missing_problems(submissions)
    with transaction.atomic():
        for problem_id, defaults in missing_problems.items():
            # Do not overwrite metadata inserted concurrently by fetch_problems.
            Problem.objects.get_or_create(problem_id=problem_id, defaults=defaults)
        # Serialize with goal deletion; never mark a newly created goal as checked.
        current_goals = list(Goal.objects.select_for_update().filter(
            user=user, pk__in=[goal.pk for goal in goals],
        ))
        result = _save_submissions(user, submissions, goals=current_goals)
        newest = max((s["epoch_second"] for s in submissions), default=0)
        SubmissionSyncState.objects.filter(pk=state.pk).update(
            last_submission_epoch=max(state.last_submission_epoch, newest),
            last_succeeded_at=django_timezone.now(),
        )
        Goal.objects.filter(pk__in=[goal.pk for goal in current_goals]).update(submissions_checked=True)
        for goal in current_goals:
            calculate_goal_progress(goal)
    return result


def _fetch_missing_problems(submissions):
    candidates = defaultdict(list)
    for submission in submissions:
        if submission["contest_id"] not in candidates[submission["problem_id"]]:
            candidates[submission["problem_id"]].append(submission["contest_id"])
    known = set(Problem.objects.filter(problem_id__in=candidates).values_list("problem_id", flat=True))
    metadata = {}
    requested = False
    for problem_id in sorted(candidates.keys() - known):
        for contest_id in candidates[problem_id]:
            # IDs are API data, not arbitrary URL paths.
            if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,50}", value) for value in (problem_id, contest_id)):
                continue
            if requested:
                time.sleep(1.1)
            requested = True
            url = f"https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}"
            try:
                response = requests.get(
                    url, headers={"User-Agent": "atcoder-tracker/0.1"},
                    timeout=(5, 30), allow_redirects=False,
                )
                response.raise_for_status()
                if response.status_code != 200:
                    continue
                soup = BeautifulSoup(response.text, "html.parser")
                heading = soup.select_one("#main-container .h2")
                if heading is None or soup.select_one("#task-statement") is None:
                    continue
                # Editorial buttons are children of the heading on official task pages.
                for element in heading.select("a, button"):
                    element.decompose()
                title = heading.get_text(" ", strip=True)
                index, separator, name = title.partition(" - ")
                if not separator or not index.strip() or not name.strip():
                    continue
                if len(index.strip()) > 50 or len(name.strip()) > 200:
                    continue
                metadata[problem_id] = {
                    "problem_index": index.strip(), "problem_name": name.strip(),
                    "contest_id": contest_id,
                    # Difficulty is unknown; do not invent a value for goal matching.
                    "difficulty": None, "display_difficulty": None,
                }
                break
            except requests.RequestException:
                logger.warning("Official problem lookup failed: %s / %s", contest_id, problem_id)
        if problem_id not in metadata:
            logger.warning("Unable to resolve missing problem: %s", problem_id)
            raise UnknownProblemError(f"Unable to resolve problem: {problem_id}")
    return metadata


def _fetch_submissions(atcoder_name, from_second):
    by_id = {}
    headers = {"User-Agent": "atcoder-tracker/0.1"}
    required = {"id", "problem_id", "contest_id", "result", "epoch_second"}
    for page in range(SUBMISSION_PAGE_LIMIT):
        if page:
            time.sleep(1.1)
        response = requests.get(
            "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions",
            params={"user": atcoder_name, "from_second": from_second},
            headers=headers, timeout=(5, 30),
        )
        response.raise_for_status()
        submissions = response.json()
        if not isinstance(submissions, list) or any(
            not isinstance(item, dict)
            or not required.issubset(item)
            or not all(isinstance(item[key], str) and item[key] for key in ("problem_id", "contest_id", "result"))
            or type(item["id"]) is not int or item["id"] < 0
            or type(item["epoch_second"]) is not int
            or not from_second <= item["epoch_second"] <= 253402300799
            for item in submissions
        ):
            raise ValueError("Invalid submissions response")
        previous_count = len(by_id)
        by_id.update((item["id"], item) for item in submissions)
        if len(submissions) < 500:
            return sorted(by_id.values(), key=lambda item: (item["epoch_second"], item["id"]))
        next_second = max(item["epoch_second"] for item in submissions)
        if next_second <= from_second and len(by_id) == previous_count:
            raise ValueError("Submission pagination did not advance")
        # Include the last second again, so submissions on the boundary are not skipped.
        from_second = next_second
    raise ValueError("Submission pagination limit reached")


def _merge_attempt(model, lookup, submissions):
    ac_dates = [datetime.fromtimestamp(s["epoch_second"], tz=timezone.utc)
                for s in submissions if s["result"] == "AC"]
    last_date = datetime.fromtimestamp(max(s["epoch_second"] for s in submissions), tz=timezone.utc)
    defaults = {
        "is_correct": bool(ac_dates),
        "first_ac_date": min(ac_dates) if ac_dates else None,
        "last_ac_date": max(ac_dates) if ac_dates else None,
        "last_submitted_date": last_date,
    }
    if model is Log:
        defaults["submitted_contest_id"] = submissions[0]["contest_id"]
    obj, created = model.objects.get_or_create(**lookup, defaults=defaults)
    if created:
        return True, False
    # ACs are accumulated. Rejudging/removing previously observed ACs is out of scope.
    first_dates = [d for d in (obj.first_ac_date, defaults["first_ac_date"]) if d is not None]
    last_dates = [d for d in (obj.last_ac_date, obj.first_ac_date, defaults["last_ac_date"]) if d is not None]
    merged = {
        "is_correct": obj.is_correct or bool(ac_dates),
        "first_ac_date": min(first_dates) if first_dates else None,
        "last_ac_date": max(last_dates) if last_dates else None,
        "last_submitted_date": max(obj.last_submitted_date, last_date),
    }
    changed = [key for key, value in merged.items() if getattr(obj, key) != value]
    if changed:
        for key in changed:
            setattr(obj, key, merged[key])
        obj.save()
    return False, bool(changed)


def _save_submissions(user, submissions, *, goals):
    problems = Problem.objects.in_bulk({s["problem_id"] for s in submissions})
    if any(s["problem_id"] not in problems for s in submissions):
        raise UnknownProblemError("Update problem data before syncing")
    by_problem = defaultdict(list)
    by_contest = defaultdict(list)
    for submission in submissions:
        by_problem[submission["problem_id"]].append(submission)
        by_contest[(submission["problem_id"], submission["contest_id"])].append(submission)
    created_count = updated_count = 0
    for problem_id, items in by_problem.items():
        created, updated = _merge_attempt(Log, {"user": user, "problem": problems[problem_id]}, items)
        created_count += created
        updated_count += updated
    for (problem_id, contest_id), items in by_contest.items():
        _merge_attempt(ContestAttempt, {
            "user": user, "problem": problems[problem_id], "submitted_contest_id": contest_id,
        }, items)
    contests = Contest.objects.in_bulk({s["contest_id"] for s in submissions})
    for goal in goals:
        start, end = goal_window(goal)
        for submission in submissions:
            if submission["result"] != "AC":
                continue
            problem = problems[submission["problem_id"]]
            ac_date = datetime.fromtimestamp(submission["epoch_second"], tz=timezone.utc)
            if not start <= ac_date < end:
                continue
            if problem.display_difficulty is None or not goal.difficulty_min <= problem.display_difficulty <= goal.difficulty_max:
                continue
            contest_id = submission["contest_id"]
            if contest_type_for(contest_id, contests.get(contest_id)) not in goal.contest_types:
                continue
            record, created = GoalAC.objects.get_or_create(goal=goal, problem=problem, defaults={"ac_date": ac_date})
            if not created and ac_date < record.ac_date:
                record.ac_date = ac_date
                record.save(update_fields=["ac_date"])
    return {"code": "success", "created": created_count, "updated": updated_count}


def correct_difficulty(difficulty):
    if difficulty is None:
        return None
    if difficulty >= 400:
        return round(difficulty)
    return round(400 / math.exp(1 - difficulty / 400))
