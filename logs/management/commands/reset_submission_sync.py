from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from logs.models import SubmissionSyncState


class Command(BaseCommand):
    help = "停止した同期の実行中状態を解除します。対象の同期が停止済みであることを確認してください。"

    def add_arguments(self, parser):
        parser.add_argument("username", help="アプリのユーザー名")
        parser.add_argument("--confirm-stopped", action="store_true", help="対象の同期プロセスが停止済みであることを確認")

    def handle(self, *args, **options):
        if not options["confirm_stopped"]:
            raise CommandError("同期プロセスの停止を確認し、--confirm-stopped を指定してください。")
        with transaction.atomic():
            try:
                user = get_user_model().objects.select_for_update().get(username=options["username"])
            except get_user_model().DoesNotExist:
                raise CommandError("ユーザーが見つかりません")
            count = SubmissionSyncState.objects.filter(user=user, is_running=True).update(is_running=False)
        self.stdout.write(self.style.SUCCESS(f"実行中状態を解除しました（{count}件）"))
