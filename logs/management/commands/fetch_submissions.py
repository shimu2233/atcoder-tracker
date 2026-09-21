from accounts.models import CustomUser
from django.core.management.base import BaseCommand, CommandError
from logs.services import sync_submissions


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument("atcoder_username")
    def handle(self,*args,**options):
        app_username=options["atcoder_username"]
        try:
            user = CustomUser.objects.get(username=app_username)
        except CustomUser.DoesNotExist:
            raise CommandError(f"ユーザー '{app_username}' が見つかりません")
        result = sync_submissions(user)
        if "error" in result:
            raise CommandError(result["error"])
        self.stdout.write(self.style.SUCCESS(
            f"完了: 新規 {result['created']}件 / 更新 {result['updated']}件"
        ))


