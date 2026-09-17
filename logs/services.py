import requests
import time
from datetime import datetime, timezone
from logs.models import ContestAttempt, Log, Problem
import math

def sync_submissions(user):
    """指定ユーザーのAtCoder提出履歴を取得してLogに保存する"""
    atcoder_name = user.atcoder_username
    if not atcoder_name:
        return {"error": "AtCoderユーザー名が設定されていません"}

    all_submissions = []
    headers = {"User-Agent": "atcoder-tracker/0.1"}
    params = {"user": atcoder_name, "from_second": 0}
    cnt = 0

    while True:
        response = requests.get(
            "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions",
            params=params, headers=headers,
        )
        submissions = response.json()
        all_submissions.extend(submissions)
        if len(submissions) < 500:
            break
        last = max(submissions, key=lambda s: s["epoch_second"])
        params["from_second"] = last["epoch_second"] + 1
        time.sleep(1)
        cnt += 1
        if cnt == 100:
            break

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

    return {"created": created_count, "updated": updated_count}



def correct_difficulty(difficulty):
    if difficulty is None:
        return None
    if difficulty >= 400:
        return round(difficulty)
    return round(400 / math.exp(1 - difficulty / 400))
