from django.core.management.base import BaseCommand
from logs.models import Tag
DEFAULT_TAGS = [
    "全探索",
    "貪欲法",
    "動的計画法(DP)",
    "二分探索",
    "グラフ探索(BFS/DFS)",
    "Union-Find",
    "累積和",
    "ソート",
    "数学",
    "文字列処理",
    "データ構造",
    "実装",
    "発想",
]
class Command(BaseCommand):
    def handle(self, *args, **options):
        cnt=0
        for tag_name in DEFAULT_TAGS:
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={"is_default": True},
            )
            if created:
                cnt+=1
        self.stdout.write(f"新規{cnt}件、全{len(DEFAULT_TAGS)}件")