import requests
import time
from django.core.management.base import BaseCommand
from logs.models import Problem
class Command(BaseCommand):
    def handle(self, *args, **options):
        headers = {
            "User-Agent": "atcoder-tracker/0.1",
        }
        response=requests.get("https://kenkoooo.com/atcoder/resources/problems.json",headers=headers,)
        problems = response.json()
        self.stdout.write(f"problems.json: {len(problems)}件")
        time.sleep(1)
        response = requests.get("https://kenkoooo.com/atcoder/resources/problem-models.json",headers=headers,)
        problem_models = response.json()
        self.stdout.write(f"problem-models.json: {len(problem_models)}件")
        problem_objects = []
        for p in problems:
            pid = p["id"]
            model = problem_models.get(pid, {})
            
            problem_objects.append(
                Problem(
                    problem_id=pid,
                    problem_name=p["name"],
                    contest_id=p["contest_id"],
                    difficulty=model.get("difficulty"),
                    is_experimental=model.get("is_experimental", False),
                )
            )

        Problem.objects.bulk_create(
            problem_objects,
            update_conflicts=True,
            update_fields=["problem_name", "contest_id", "difficulty", "is_experimental"],
            unique_fields=["problem_id"],
        )

        self.stdout.write(self.style.SUCCESS(f"完了: {len(problem_objects)}件の問題を保存しました"))