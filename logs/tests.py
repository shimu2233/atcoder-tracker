from django.test import TestCase
from unittest.mock import Mock, patch

from logs.services import correct_difficulty, sync_submissions
from django.contrib.auth import get_user_model
from django.urls import reverse
from logs.models import Problem, DoLater
from logs.models import Contest, ContestAttempt, ContestProblem
from logs.contest_classification import classify_contest, tessoku_section
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
        self.assertContains(response, "テスト問題")

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
        response = self.client.get(reverse("tessoku"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "鉄則A")
        self.assertContains(response, "A77")
        self.assertContains(response, "鉄則B")
        self.assertContains(response, "B16")

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
        self.assertContains(response, "<h2>AHC</h2>", html=True)
        self.assertContains(response, "AHC形式（AHC以外）")


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
