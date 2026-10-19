from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from logs.models import Problem, Log, ContestAttempt, Goal, GoalAC, SubmissionSyncState
from logs.services import sync_submissions, _fetch_missing_problems, UnknownProblemError


OFFICIAL_HTML = """<div id="main-container"><span class="h2">
A-Final - Somersault Slimes (System Test)
<a href="/editorial">Editorial</a></span><div id="task-statement"></div></div>"""


class OfficialProblemFallbackTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="fallback", atcoder_username="coder")
        self.now = timezone.now()
        self.items = [{"id": 1, "problem_id": "ahc072_b", "contest_id": "ahc072",
                       "result": "AC", "epoch_second": int(self.now.timestamp())}]

    def response(self, html=OFFICIAL_HTML, status=200):
        response = Mock(status_code=status, text=html)
        if status >= 400:
            response.raise_for_status.side_effect = requests.HTTPError()
        return response

    def run_sync(self, response):
        with patch("logs.services._fetch_submissions", return_value=self.items), patch(
            "logs.services.requests.get", return_value=response,
        ) as get:
            return sync_submissions(self.user), get

    def test_missing_system_test_problem_is_imported_and_sync_succeeds(self):
        goal = Goal.objects.create(user=self.user, title="Goal", start_date=self.now.date(),
                                   end_date=self.now.date(), target_count=1, contest_types=["HEURISTIC"],
                                   difficulty_min=0, difficulty_max=4000)
        result, get = self.run_sync(self.response())
        self.assertEqual(result["code"], "success")
        problem = Problem.objects.get(pk="ahc072_b")
        self.assertEqual(problem.problem_index, "A-Final")
        self.assertEqual(problem.problem_name, "Somersault Slimes (System Test)")
        self.assertEqual(problem.contest_id, "ahc072")
        self.assertIsNone(problem.display_difficulty)
        self.assertTrue(Log.objects.get(user=self.user).is_correct)
        self.assertTrue(ContestAttempt.objects.get(user=self.user).is_correct)
        self.assertFalse(GoalAC.objects.filter(goal=goal).exists())
        state = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(state.last_submission_epoch, self.items[0]["epoch_second"])
        self.assertIsNotNone(state.last_succeeded_at)
        self.assertFalse(state.is_running)
        get.assert_called_once_with(
            "https://atcoder.jp/contests/ahc072/tasks/ahc072_b",
            headers={"User-Agent": "atcoder-tracker/0.1"},
            timeout=(5, 30), allow_redirects=False,
        )

    def test_known_problem_does_not_request_official_page_or_overwrite_metadata(self):
        Problem.objects.create(problem_id="ahc072_b", problem_name="Existing", contest_id="ahc072", display_difficulty=800)
        result, get = self.run_sync(self.response())
        self.assertEqual(result["code"], "success")
        get.assert_not_called()
        self.assertEqual(Problem.objects.get(pk="ahc072_b").display_difficulty, 800)

    def test_failure_keeps_checkpoint_and_history_unchanged(self):
        for response in (self.response(status=404), self.response(status=302),
                         self.response("<html>Login</html>"),
                         self.response('<div id="main-container"><span class="h2">Invalid</span><div id="task-statement"></div></div>')):
            with self.subTest(response=response):
                SubmissionSyncState.objects.filter(user=self.user).delete()
                with self.assertLogs("logs.services", level="WARNING"):
                    result, _ = self.run_sync(response)
                self.assertEqual(result["code"], "unknown_problem")
                self.assertFalse(Problem.objects.exists())
                self.assertFalse(Log.objects.exists())
                state = SubmissionSyncState.objects.get(user=self.user)
                self.assertEqual(state.last_submission_epoch, 0)
                self.assertIsNone(state.last_succeeded_at)
                self.assertFalse(state.is_running)

    def test_timeout_does_not_advance_checkpoint(self):
        with patch("logs.services._fetch_submissions", return_value=self.items), patch(
            "logs.services.requests.get", side_effect=requests.Timeout,
        ), self.assertLogs("logs.services", level="WARNING"):
            result = sync_submissions(self.user)
        self.assertEqual(result["code"], "unknown_problem")
        self.assertEqual(SubmissionSyncState.objects.get(user=self.user).last_submission_epoch, 0)

    def test_import_is_rolled_back_if_later_save_fails(self):
        with patch("logs.services._save_submissions", side_effect=RuntimeError("DB failure")):
            with self.assertRaises(RuntimeError):
                self.run_sync(self.response())
        self.assertFalse(Problem.objects.exists())
        state = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(state.last_submission_epoch, 0)
        self.assertFalse(state.is_running)

    def test_repeated_problem_is_fetched_once(self):
        with patch("logs.services.requests.get", return_value=self.response()) as get:
            metadata = _fetch_missing_problems(self.items + self.items)
        get.assert_called_once()
        self.assertEqual(list(metadata), ["ahc072_b"])

    def test_alternative_submission_contest_is_tried(self):
        alternate = dict(self.items[0], contest_id="another")
        with patch("logs.services.requests.get", side_effect=[self.response(status=404), self.response()]) as get, patch(
            "logs.services.time.sleep",
        ) as sleep, self.assertLogs("logs.services", level="WARNING"):
            metadata = _fetch_missing_problems(self.items + [alternate])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(metadata["ahc072_b"]["contest_id"], "another")
        sleep.assert_called_once_with(1.1)

    def test_invalid_api_ids_are_not_used_as_urls(self):
        with patch("logs.services.requests.get") as get, self.assertLogs("logs.services", level="WARNING"):
            with self.assertRaises(UnknownProblemError):
                _fetch_missing_problems([dict(self.items[0], contest_id="../login")])
        get.assert_not_called()

    def test_concurrent_catalog_insert_wins(self):
        def fetch(*args, **kwargs):
            Problem.objects.create(problem_id="ahc072_b", problem_name="Catalog name", contest_id="ahc072", display_difficulty=1000)
            return self.response()
        with patch("logs.services._fetch_submissions", return_value=self.items), patch(
            "logs.services.requests.get", side_effect=fetch,
        ):
            result = sync_submissions(self.user)
        self.assertEqual(result["code"], "success")
        self.assertEqual(Problem.objects.get(pk="ahc072_b").problem_name, "Catalog name")
        self.assertEqual(Problem.objects.get(pk="ahc072_b").display_difficulty, 1000)
