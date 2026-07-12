from django.core.management.base import BaseCommand
import requests
import time
from datetime import datetime, timezone
from accounts.models import CustomUser
from django.core.management.base import BaseCommand, CommandError
from logs.models import Log
class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument("atcoder_username")
    def handle(self,*args,**options):
        app_username=options["atcoder_username"]
        try:
            user = CustomUser.objects.get(username=app_username)
        except CustomUser.DoesNotExist:
            raise CommandError(f"ユーザー '{app_username}' が見つかりません")

        atcoder_name = user.atcoder_username
        if not atcoder_name:
            raise CommandError(f"ユーザー '{app_username}' に AtCoder ユーザー名が設定されていません")

        self.stdout.write(f"同期開始: {user.username} (AtCoder: {atcoder_name})")
        self.stdout.write(f"取得対象: {atcoder_name}")
        all_submissions = []
        headers = {
            "User-Agent": "atcoder-tracker/0.1",
        }
        params = {
            "user": atcoder_name,
            "from_second": 0,
        }
        cnt=0
        while True:
            response = requests.get("https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions", params=params, headers=headers)
            submissions = response.json()
            self.stdout.write(f"取得件数: {len(submissions)}")
            all_submissions.extend(submissions)
            last = max(submissions, key=lambda s: s["epoch_second"])
            num = last["epoch_second"] + 1
            if len(submissions)<500:
                break
            time.sleep(1)
            cnt+=1
            if cnt==100:
                break
            params["from_second"]=num
        problem_dictionary={}
        for i in all_submissions:
            pid=i["problem_id"]
            problem_dictionary.setdefault(pid,[]).append(i)
        self.stdout.write(f"合計: {len(all_submissions)}件")
        self.stdout.write(f"問題数: {len(problem_dictionary)}")
        first_key = list(problem_dictionary.keys())[0]
        self.stdout.write(f"{first_key}: {len(problem_dictionary[first_key])}件の提出")
        for problem_id, submissions_of_problem in problem_dictionary.items():
            is_correct = any(s["result"] == "AC" for s in submissions_of_problem)
            ac_submissions = [s for s in submissions_of_problem if s["result"] == "AC"]
            last_submitted_second=max(s["epoch_second"] for s in submissions_of_problem)
            last_submitted_date=datetime.fromtimestamp(last_submitted_second, tz=timezone.utc)
            if ac_submissions:
                first_ac_second = min(s["epoch_second"] for s in ac_submissions)
                first_ac_date = datetime.fromtimestamp(first_ac_second, tz=timezone.utc)
            else:
                first_ac_date = None
            contest_id=submissions_of_problem[0]["contest_id"]
            log, created = Log.objects.update_or_create(
                user=user,
                problem_id=problem_id,
                defaults={
                    "contest_id": contest_id,
                    "is_correct": is_correct,
                    "first_ac_date": first_ac_date,
                    "last_submitted_date": last_submitted_date,
                    "problem_name": problem_id, 
                },
            )
            self.stdout.write(f"{contest_id} {problem_id} : {is_correct} , {first_ac_date} , last_sub={last_submitted_date}")
