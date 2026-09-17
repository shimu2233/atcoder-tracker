import requests
import time
from bs4 import BeautifulSoup
from django.db import transaction
from django.core.management.base import BaseCommand
from logs.contest_classification import classify_contest
from logs.models import Contest, ContestProblem, Problem
from logs.services import correct_difficulty


def fetch_official_heuristic_contest_ids(session, headers):
    """Collect completed and currently listed heuristic contests from AtCoder."""
    contest_ids = set()
    for category in (1200, 1250):
        for page in range(1, 30):
            response = session.get(
                "https://atcoder.jp/contests/archive",
                params={
                    "category": category,
                    "ratedType": 0,
                    "page": page,
                    "lang": "ja",
                },
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            page_ids = {
                anchor["href"].split("/")[2]
                for anchor in soup.select('table tbody a[href^="/contests/"]')
            }
            new_ids = page_ids - contest_ids
            if not page_ids or not new_ids:
                break
            contest_ids.update(page_ids)
            time.sleep(1)

    response = session.get(
        "https://atcoder.jp/contests",
        params={"lang": "ja"},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for row in soup.select("table tbody tr"):
        if not row.select_one('span[title="Heuristic"]'):
            continue
        anchor = row.select_one('a[href^="/contests/"]')
        if anchor:
            contest_ids.add(anchor["href"].split("/")[2])
    return contest_ids


class Command(BaseCommand):
    def handle(self, *args, **options):
        headers = {
            "User-Agent": "atcoder-tracker/0.1",
        }
        session = requests.Session()
        response=session.get("https://kenkoooo.com/atcoder/resources/problems.json",headers=headers, timeout=30)
        response.raise_for_status()
        problems = response.json()
        self.stdout.write(f"problems.json: {len(problems)}件")
        time.sleep(1)
        response = session.get("https://kenkoooo.com/atcoder/resources/problem-models.json",headers=headers, timeout=30)
        response.raise_for_status()
        problem_models = response.json()
        self.stdout.write(f"problem-models.json: {len(problem_models)}件")
        time.sleep(1)
        response = session.get("https://kenkoooo.com/atcoder/resources/contests.json", headers=headers, timeout=30)
        response.raise_for_status()
        contests = response.json()
        self.stdout.write(f"contests.json: {len(contests)}件")
        time.sleep(1)
        response = session.get("https://kenkoooo.com/atcoder/resources/contest-problem.json", headers=headers, timeout=30)
        response.raise_for_status()
        contest_problems = response.json()
        self.stdout.write(f"contest-problem.json: {len(contest_problems)}件")

        try:
            heuristic_ids = fetch_official_heuristic_contest_ids(session, headers)
            self.stdout.write(f"AtCoder公式ヒューリスティック分類: {len(heuristic_ids)}件")
        except requests.RequestException as exc:
            heuristic_ids = set(
                Contest.objects.filter(contest_format="HEURISTIC")
                .exclude(series="AHC")
                .values_list("contest_id", flat=True)
            )
            self.stderr.write(
                self.style.WARNING(
                    f"AtCoder公式分類を取得できなかったため既存データを使用します: {exc}"
                )
            )

        problem_objects = []
        for p in problems:
            pid = p["id"]
            model = problem_models.get(pid, {})
            difficulty = model.get("difficulty")

            display = correct_difficulty(difficulty)
            problem_objects.append(
                Problem(
                    problem_id=pid,
                    problem_name=p["name"],
                    contest_id=p["contest_id"],
                    problem_index=p["problem_index"],
                    difficulty=difficulty,
                    display_difficulty=display,
                    is_experimental=model.get("is_experimental", False),
                )
            )
        Problem.objects.bulk_create(
            problem_objects,
            update_conflicts=True,
            update_fields=["problem_name", "contest_id", "problem_index", "difficulty" , "display_difficulty", "is_experimental"],
            unique_fields=["problem_id"],
        )

        contest_objects = []
        for contest in contests:
            series, contest_format, is_evergreen = classify_contest(
                contest["id"], heuristic_ids
            )
            contest_objects.append(
                Contest(
                    contest_id=contest["id"],
                    title=contest["title"],
                    start_epoch_second=contest["start_epoch_second"],
                    duration_second=contest["duration_second"],
                    rate_change=contest["rate_change"],
                    series=series,
                    contest_format=contest_format,
                    is_evergreen=is_evergreen,
                )
            )
        Contest.objects.bulk_create(
            contest_objects,
            update_conflicts=True,
            update_fields=[
                "title",
                "start_epoch_second",
                "duration_second",
                "rate_change",
                "series",
                "contest_format",
                "is_evergreen",
            ],
            unique_fields=["contest_id"],
        )

        known_contests = set(Contest.objects.values_list("contest_id", flat=True))
        known_problems = set(Problem.objects.values_list("problem_id", flat=True))
        relation_objects = [
            ContestProblem(
                contest_id=item["contest_id"],
                problem_id=item["problem_id"],
                problem_index=item["problem_index"],
            )
            for item in contest_problems
            if item["contest_id"] in known_contests
            and item["problem_id"] in known_problems
        ]
        with transaction.atomic():
            ContestProblem.objects.all().delete()
            ContestProblem.objects.bulk_create(relation_objects, batch_size=2000)

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: 問題{len(problem_objects)}件、コンテスト{len(contest_objects)}件、"
                f"掲載関係{len(relation_objects)}件を保存しました"
            )
        )
