from django.test import TestCase
from unittest.mock import Mock, patch
from datetime import date, datetime
from zoneinfo import ZoneInfo

from logs.services import correct_difficulty, sync_submissions
from django.contrib.auth import get_user_model
from django.urls import reverse
from logs.models import Problem, DoLater, Goal, Log
from logs.models import Contest, ContestAttempt, ContestProblem
from logs.contest_classification import classify_contest, tessoku_section
from logs.goal_progress import calculate_goal_progress
from logs.views import difficulty_stats_for_user

class CorrectDifficultyTest(TestCase):
    def test_400以上はそのまま返る(self):
        self.assertEqual(correct_difficulty(800), 800)

    def test_境界値の400はそのまま返る(self):
        self.assertEqual(correct_difficulty(400), 400)

    def test_負の値でも正の値に補正される(self):
        self.assertGreater(correct_difficulty(-921), 0)

    def test_難易度未推定のNoneはNoneのまま返る(self):
        self.assertIsNone(correct_difficulty(None))


class NavigationVisibilityTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="navigation-user", password="testpass123"
        )

    def test_トップページでもログイン状態なら上部ナビを表示する(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("top"))

        self.assertContains(response, "<nav>", html=False)
        self.assertContains(response, "ダッシュボード")
        self.assertContains(response, "常設")

    def test_ログイン前は上部ナビを表示しない(self):
        response = self.client.get(reverse("top"))

        self.assertNotContains(response, "<nav>", html=False)

    def test_ダッシュボードでは上部ナビを表示する(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "<nav>", html=False)

    def test_デモURLは存在しない(self):
        response = self.client.get("/demo/")

        self.assertEqual(response.status_code, 404)


class GoalFlowTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="goal-user", password="testpass123"
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-goal-user", password="testpass123"
        )
        self.contest = Contest.objects.create(
            contest_id="abc500",
            title="AtCoder Beginner Contest 500",
            series="ABC",
            contest_format="ALGORITHM",
        )
        self.problem = Problem.objects.create(
            problem_id="abc500_c",
            contest_id="abc500",
            problem_name="Goal problem",
            display_difficulty=800,
        )
        self.first_ac_at = datetime(2026, 9, 10, 12, tzinfo=ZoneInfo("Asia/Tokyo"))
        Log.objects.create(
            user=self.user,
            problem=self.problem,
            submitted_contest_id=self.contest.contest_id,
            is_correct=True,
            first_ac_date=self.first_ac_at,
            last_submitted_date=self.first_ac_at,
        )
        ContestAttempt.objects.create(
            user=self.user,
            problem=self.problem,
            submitted_contest_id=self.contest.contest_id,
            is_correct=True,
            first_ac_date=self.first_ac_at,
            last_submitted_date=self.first_ac_at,
        )

    def create_goal(self, **overrides):
        values = {
            "user": self.user,
            "title": "水色を目指す",
            "start_date": date(2026, 9, 1),
            "end_date": date(2026, 9, 30),
            "target_count": 1,
            "contest_types": ["ALGORITHM"],
            "difficulty_min": 400,
            "difficulty_max": 1199,
        }
        values.update(overrides)
        return Goal.objects.create(**values)

    def test_条件内の初ACで目標を達成する(self):
        goal = self.create_goal()

        progress = calculate_goal_progress(goal)

        self.assertEqual(progress["completed_count"], 1)
        self.assertTrue(progress["is_achieved"])
        goal.refresh_from_db()
        self.assertEqual(goal.achieved_at, self.first_ac_at)

    def test_種別または難易度が対象外なら数えない(self):
        evergreen_goal = self.create_goal(contest_types=["EVERGREEN"])
        hard_goal = self.create_goal(difficulty_min=1200, difficulty_max=1999)

        self.assertEqual(
            calculate_goal_progress(evergreen_goal)["completed_count"], 0
        )
        self.assertEqual(calculate_goal_progress(hard_goal)["completed_count"], 0)

    def test_目標を画面から作成できる(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("goals"),
            {
                "title": "ABCを解く",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
                "target_count": 5,
                "contest_types": ["ALGORITHM", "GRAND"],
                "difficulty_min": 400,
                "difficulty_max": 799,
            },
        )

        self.assertRedirects(response, reverse("goals"))
        goal = Goal.objects.get(title="ABCを解く")
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.contest_types, ["ALGORITHM", "GRAND"])

    def test_他ユーザーの目標は削除できない(self):
        goal = self.create_goal(user=self.other_user)
        self.client.force_login(self.user)

        response = self.client.post(reverse("delete_goal", args=[goal.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Goal.objects.filter(id=goal.id).exists())

    def test_上部ナビから目標設定へ移動できる(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, reverse("goals"))
        self.assertContains(response, "目標設定")

    def test_ログイン中は上部に目標の進捗を表示する(self):
        self.create_goal(title="上部に表示する目標", target_count=2)
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, 'aria-label="目標の進捗"')
        self.assertContains(response, "上部に表示する目標")
        self.assertContains(response, "1 / 2問")

    def test_トップページでは目標進捗を表示しない(self):
        self.create_goal(title="トップでは隠す目標", target_count=2)
        self.client.force_login(self.user)

        response = self.client.get(reverse("top"))

        self.assertNotContains(response, "トップでは隠す目標")
        self.assertContains(response, "<nav>", html=False)


class DoLaterFlowTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass123"
        )
        self.problem = Problem.objects.create(
            problem_id="abc001_a",
            contest_id="abc001",
            problem_name="テスト問題",
            difficulty=-921,
            display_difficulty=correct_difficulty(-921),
        )

    def test_クエリセットの中身を確認(self):
        self.client.login(username="testuser", password="testpass123")
        self.client.post(reverse("toggle_do_later", args=["abc001_a"]))
        response = self.client.get(reverse("do_later"))
        print("context keys:", list(response.context.keys()))
        print("object_list:", response.context.get("object_list"))

    def test_後でやるに登録すると一覧に表示される(self):
        self.client.login(username="testuser", password="testpass123")
        self.client.post(reverse("toggle_do_later", args=["abc001_a"]))
        self.assertTrue(
            DoLater.objects.filter(user=self.user, problem=self.problem).exists()
        )
        response = self.client.get(reverse("do_later"))
        item = response.context["problem_list_data"]["sections"][0]["items"][0]
        self.assertEqual(item["name"], "テスト問題")
        self.assertTrue(item["is_do_later"])

    def test_未ログインでは一覧を見られない(self):
        response = self.client.get(reverse("do_later"))
        self.assertEqual(response.status_code, 302)


class ContestClassificationTest(TestCase):
    def test_AHC本編とAHC形式を分ける(self):
        self.assertEqual(classify_contest("ahc071", {"masters2026-qual"})[0], "AHC")
        self.assertEqual(
            classify_contest("masters2026-qual", {"masters2026-qual"})[0],
            "HEURISTIC_OTHER",
        )

    def test_常設教材を判定する(self):
        series, contest_format, is_evergreen = classify_contest("typical90")
        self.assertEqual(series, "LEARNING")
        self.assertEqual(contest_format, "ALGORITHM")
        self.assertTrue(is_evergreen)

    def test_鉄則の問題番号からABCを判定する(self):
        self.assertEqual(tessoku_section("A77"), "A")
        self.assertEqual(tessoku_section("B16"), "B")
        self.assertEqual(tessoku_section("C20"), "C")


class LearningContentViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="learner", password="testpass123"
        )
        self.tessoku = Contest.objects.create(
            contest_id="tessoku-book",
            title="競技プログラミングの鉄則",
            series="LEARNING",
            is_evergreen=True,
        )
        self.problem_a = Problem.objects.create(
            problem_id="typical90_a",
            contest_id="typical90",
            problem_index="001",
            problem_name="Yokan Party",
        )
        self.problem_b = Problem.objects.create(
            problem_id="dp_a",
            contest_id="dp",
            problem_index="A",
            problem_name="Frog 1",
        )
        ContestProblem.objects.create(
            contest=self.tessoku,
            problem=self.problem_a,
            problem_index="A77",
        )
        ContestProblem.objects.create(
            contest=self.tessoku,
            problem=self.problem_b,
            problem_index="B16",
        )

    def test_再録問題を鉄則AとBに分けて表示する(self):
        self.client.login(username="learner", password="testpass123")
        response = self.client.get(
            reverse("learning_content_detail", args=["tessoku-book"])
        )
        self.assertEqual(response.status_code, 200)
        sections = response.context["content_data"]["sections"]
        self.assertEqual([section["name"] for section in sections], ["鉄則A", "鉄則B"])
        self.assertEqual(sections[0]["items"][0]["problem_index"], "A77")
        self.assertEqual(sections[1]["items"][0]["problem_index"], "B16")
        self.assertContains(response, 'id="problem-explorer-root"')

    def test_常設教材一覧に鉄則の掲載問題数を表示する(self):
        self.client.login(username="learner", password="testpass123")
        response = self.client.get(reverse("learning_contents"))
        self.assertEqual(response.status_code, 200)
        tessoku_stat = next(
            stat
            for stat in response.context["content_stats"]
            if stat["content_id"] == "tessoku-book"
        )
        self.assertEqual(tessoku_stat["total"], 2)
        self.assertEqual(
            tessoku_stat["detail_url"],
            reverse("learning_content_detail", args=["tessoku-book"]),
        )
        self.assertContains(response, 'id="learning-dashboard-root"')


class ContestGroupingViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="contest-user", password="testpass123"
        )
        self.ahc = Contest.objects.create(
            contest_id="ahc071",
            title="AtCoder Heuristic Contest 071",
            series="AHC",
            contest_format="HEURISTIC",
        )
        self.heuristic = Contest.objects.create(
            contest_id="masters2026-qual",
            title="Masters Championship Qual",
            series="HEURISTIC_OTHER",
            contest_format="HEURISTIC",
        )
        self.ahc_problem = Problem.objects.create(
            problem_id="ahc071_a",
            contest_id="ahc071",
            problem_index="A",
            problem_name="AHC problem",
        )
        self.other_problem = Problem.objects.create(
            problem_id="masters2026_qual_a",
            contest_id="masters2026-qual",
            problem_index="A",
            problem_name="Other heuristic problem",
        )
        for contest, problem in (
            (self.ahc, self.ahc_problem),
            (self.heuristic, self.other_problem),
        ):
            ContestProblem.objects.create(
                contest=contest,
                problem=problem,
                problem_index="A",
            )
            ContestAttempt.objects.create(
                user=self.user,
                problem=problem,
                submitted_contest_id=contest.contest_id,
                last_submitted_date="2026-01-01T00:00:00Z",
            )

    def test_AHCとAHC形式を別グループで表示する(self):
        self.client.login(username="contest-user", password="testpass123")
        response = self.client.get(reverse("contest_problems"))
        self.assertEqual(response.status_code, 200)
        categories = {
            category["key"]: category
            for category in response.context["contest_data"]["categories"]
        }
        self.assertEqual(
            [group["series"] for group in categories["heuristic"]["groups"]],
            ["AHC", "HEURISTIC_OTHER"],
        )
        self.assertEqual(categories["algorithm"]["groups"], [])
        self.assertEqual(categories["grand"]["groups"], [])
        self.assertContains(response, 'id="contest-explorer-root"')


class SubmissionContestTrackingTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="multi-contest-user",
            password="testpass123",
            atcoder_username="atcoder-user",
        )
        self.problem = Problem.objects.create(
            problem_id="abc086_a",
            contest_id="abc086",
            problem_index="A",
            problem_name="Product",
        )

    @patch("logs.services.requests.get")
    def test_同じ問題の提出を開催枠ごとに保存する(self, get):
        response = Mock()
        response.json.return_value = [
            {
                "problem_id": "abc086_a",
                "contest_id": "abc086",
                "result": "WA",
                "epoch_second": 100,
            },
            {
                "problem_id": "abc086_a",
                "contest_id": "abs",
                "result": "WA",
                "epoch_second": 200,
            },
            {
                "problem_id": "abc086_a",
                "contest_id": "abs",
                "result": "AC",
                "epoch_second": 300,
            },
        ]
        get.return_value = response

        sync_submissions(self.user)

        attempts = ContestAttempt.objects.filter(user=self.user)
        self.assertEqual(attempts.count(), 2)
        self.assertFalse(attempts.get(submitted_contest_id="abc086").is_correct)
        self.assertTrue(attempts.get(submitted_contest_id="abs").is_correct)


class DifficultyStatsClassificationTest(TestCase):
    def test_通常コンテストだけを難易度集計する(self):
        user = get_user_model().objects.create_user(
            username="difficulty-user", password="testpass123"
        )
        normal = Problem.objects.create(
            problem_id="abc001_a",
            contest_id="abc001",
            problem_index="A",
            problem_name="Normal",
            display_difficulty=800,
        )
        learning = Problem.objects.create(
            problem_id="typical90_b",
            contest_id="typical90",
            problem_index="002",
            problem_name="Learning",
            display_difficulty=1200,
        )
        for problem, contest_id in (
            (normal, "abc001"),
            (learning, "typical90"),
        ):
            ContestAttempt.objects.create(
                user=user,
                problem=problem,
                submitted_contest_id=contest_id,
                is_correct=True,
                last_submitted_date="2026-01-01T00:00:00Z",
            )

        stats = difficulty_stats_for_user(user)

        self.assertEqual([stat["band"] for stat in stats], ["800-1199"])
