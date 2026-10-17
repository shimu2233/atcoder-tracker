from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Event, Barrier
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connection, IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from logs.models import SubmissionSyncState, Problem, Log, ContestAttempt, Goal, DoLater
from logs.services import sync_submissions, change_atcoder_username


class SyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="sync-user", atcoder_username="old")
        self.now = timezone.now()

    def state(self, **kwargs):
        return SubmissionSyncState.objects.create(user=self.user, **kwargs)

    @patch("logs.services.requests.get")
    def test_first_sync(self, get):
        get.return_value.json.return_value = []
        self.assertEqual(sync_submissions(self.user)["code"], "success")
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 30))
        state = self.user.submission_sync_state
        self.assertFalse(state.is_running)
        self.assertIsNotNone(state.last_started_at)

    @patch("logs.services.requests.get")
    def test_cooldown_and_exact_boundary(self, get):
        get.return_value.json.return_value = []
        self.state(last_started_at=self.now - timedelta(minutes=5) + timedelta(microseconds=1))
        with patch("logs.services.django_timezone.now", return_value=self.now):
            self.assertEqual(sync_submissions(self.user)["code"], "cooldown")
            get.assert_not_called()
            SubmissionSyncState.objects.update(last_started_at=self.now - timedelta(minutes=5))
            self.assertEqual(sync_submissions(self.user)["code"], "success")

    @patch("logs.services.requests.get")
    def test_running_and_other_user(self, get):
        get.return_value.json.return_value = []
        self.state(is_running=True, last_started_at=self.now - timedelta(hours=1))
        self.assertEqual(sync_submissions(self.user)["code"], "already_running")
        get.assert_not_called()
        other = get_user_model().objects.create_user(username="other", atcoder_username="other")
        self.assertEqual(sync_submissions(other)["code"], "success")

    @patch("logs.services.requests.get")
    def test_failed_requests_release_state(self, get):
        for error in (requests.Timeout(), requests.HTTPError(), ValueError()):
            with self.subTest(error=type(error).__name__):
                SubmissionSyncState.objects.filter(user=self.user).delete()
                get.side_effect = error
                self.assertEqual(sync_submissions(self.user)["code"], "fetch_failed")
                state = SubmissionSyncState.objects.get(user=self.user)
                self.assertFalse(state.is_running)
                self.assertIsNotNone(state.last_started_at)
                self.assertEqual(sync_submissions(self.user)["code"], "cooldown")

    @patch("logs.services.requests.get")
    def test_invalid_payload(self, get):
        get.return_value.json.return_value = {"error": "unavailable"}
        self.assertEqual(sync_submissions(self.user)["code"], "fetch_failed")
        self.assertFalse(SubmissionSyncState.objects.get(user=self.user).is_running)

    @patch("logs.services._fetch_and_save_submissions", side_effect=RuntimeError("unexpected"))
    def test_unexpected_error_releases_state(self, fetch):
        with self.assertRaises(RuntimeError):
            sync_submissions(self.user)
        self.assertFalse(SubmissionSyncState.objects.get(user=self.user).is_running)

    def test_name_change_during_sync_rejected_in_settings(self):
        self.state(is_running=True, last_started_at=self.now)
        self.client.force_login(self.user)
        response = self.client.post(reverse("settings"), {"atcoder_username": "new"})
        self.assertContains(response, "同期実行中は")
        self.user.refresh_from_db()
        self.assertEqual(self.user.atcoder_username, "old")

    def test_name_change_clears_only_history(self):
        state = self.state(last_started_at=self.now)
        problem = Problem.objects.create(problem_id="abc_a", problem_name="A", contest_id="abc")
        Log.objects.create(user=self.user, problem=problem, submitted_contest_id="abc", last_submitted_date=self.now)
        ContestAttempt.objects.create(user=self.user, problem=problem, submitted_contest_id="abc", last_submitted_date=self.now)
        DoLater.objects.create(user=self.user, problem=problem)
        Goal.objects.create(user=self.user, title="goal", start_date=self.now.date(), end_date=self.now.date(), target_count=1, difficulty_min=0, difficulty_max=1000)
        self.client.force_login(self.user)
        response = self.client.post(reverse("settings"), {"atcoder_username": " new "})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.atcoder_username, "new")
        self.assertFalse(Log.objects.filter(user=self.user).exists())
        self.assertFalse(ContestAttempt.objects.filter(user=self.user).exists())
        self.assertTrue(DoLater.objects.filter(user=self.user).exists())
        self.assertTrue(Goal.objects.filter(user=self.user).exists())
        state.refresh_from_db()
        self.assertEqual(state.last_started_at, self.now)

    def test_unchanged_name_keeps_history_and_blank_clears(self):
        problem = Problem.objects.create(problem_id="abc_a", problem_name="A", contest_id="abc")
        Log.objects.create(user=self.user, problem=problem, submitted_contest_id="abc", last_submitted_date=self.now)
        change_atcoder_username(self.user, " old ")
        self.assertTrue(Log.objects.filter(user=self.user).exists())
        change_atcoder_username(self.user, "")
        self.user.refresh_from_db()
        self.assertIsNone(self.user.atcoder_username)
        self.assertFalse(Log.objects.filter(user=self.user).exists())

    def test_reset_command_only_releases_target(self):
        state = self.state(is_running=True, last_started_at=self.now)
        other = get_user_model().objects.create_user(username="other")
        other_state = SubmissionSyncState.objects.create(user=other, is_running=True)
        with self.assertRaises(CommandError):
            call_command("reset_submission_sync", self.user.username, stdout=StringIO())
        call_command("reset_submission_sync", self.user.username, confirm_stopped=True, stdout=StringIO())
        state.refresh_from_db()
        other_state.refresh_from_db()
        self.assertFalse(state.is_running)
        self.assertEqual(state.last_started_at, self.now)
        self.assertTrue(other_state.is_running)

    @patch("logs.services.requests.get")
    def test_stale_user_uses_latest_name(self, get):
        get.return_value.json.return_value = []
        change_atcoder_username(self.user, "new")
        sync_submissions(self.user)
        self.assertEqual(get.call_args.kwargs["params"]["user"], "new")

    def test_state_is_unique_per_user(self):
        self.state()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.state()

    def test_failed_name_change_rolls_back_deleted_history(self):
        problem = Problem.objects.create(problem_id="abc_a", problem_name="A", contest_id="abc")
        Log.objects.create(user=self.user, problem=problem, submitted_contest_id="abc", last_submitted_date=self.now)
        with patch.object(get_user_model(), "save", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                change_atcoder_username(self.user, "new")
        self.user.refresh_from_db()
        self.assertEqual(self.user.atcoder_username, "old")
        self.assertTrue(Log.objects.filter(user=self.user).exists())

    @patch("logs.services._fetch_and_save_submissions")
    def test_name_change_attempt_while_fetching_cannot_clear_history(self, fetch):
        def during_fetch(user, name):
            self.assertEqual(name, "old")
            self.assertIn("error", change_atcoder_username(user, "new"))
            return {"code": "success", "created": 0, "updated": 0}

        fetch.side_effect = during_fetch
        self.assertEqual(sync_submissions(self.user)["code"], "success")
        self.user.refresh_from_db()
        self.assertEqual(self.user.atcoder_username, "old")

    @patch("logs.services.requests.get")
    def test_web_and_command_obey_cooldown(self, get):
        self.state(last_started_at=self.now)
        self.client.force_login(self.user)
        response = self.client.post(reverse("sync"), follow=True)
        self.assertIn("日本時間", " ".join(response.context["dashboard_data"]["messages"]))
        with self.assertRaises(CommandError):
            call_command("fetch_submissions", self.user.username, stdout=StringIO())
        get.assert_not_called()


class SyncConcurrencyTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("Actual row-lock concurrency requires PostgreSQL")
        self.user = get_user_model().objects.create_user(username="race", atcoder_username="old")

    def worker(self, callback):
        close_old_connections()
        try:
            return callback()
        finally:
            close_old_connections()

    def test_simultaneous_syncs_only_one_fetch(self):
        barrier = Barrier(2)
        entered, release = Event(), Event()

        def fetch(*args):
            entered.set()
            if not release.wait(10):
                raise AssertionError("Worker was not released")
            return {"code": "success", "created": 0, "updated": 0}

        def run():
            barrier.wait(timeout=10)
            return sync_submissions(self.user)

        with patch("logs.services._fetch_and_save_submissions", side_effect=fetch) as mocked:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(self.worker, run) for _ in range(2)]
                try:
                    self.assertTrue(entered.wait(10))
                    # The rejected request finishes while the winner is still fetching.
                    from concurrent.futures import wait, FIRST_COMPLETED
                    done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                    self.assertEqual(len(done), 1)
                    self.assertEqual(next(iter(done)).result()["code"], "already_running")
                finally:
                    release.set()
                self.assertEqual(sorted(f.result()["code"] for f in futures), ["already_running", "success"])
            mocked.assert_called_once()

    def test_name_change_racing_sync_cannot_mix_history(self):
        barrier = Barrier(2)
        problem = Problem.objects.create(problem_id="race_a", problem_name="A", contest_id="race")
        fetched = []

        def fetch(user, name):
            fetched.append(name)
            Log.objects.create(user=user, problem=problem, submitted_contest_id="race", last_submitted_date=timezone.now())
            return {"code": "success", "created": 1, "updated": 0}

        def run_sync():
            barrier.wait(timeout=10)
            return sync_submissions(self.user)

        def run_change():
            barrier.wait(timeout=10)
            return change_atcoder_username(self.user, "new")

        with patch("logs.services._fetch_and_save_submissions", side_effect=fetch):
            with ThreadPoolExecutor(max_workers=2) as pool:
                sync_future = pool.submit(self.worker, run_sync)
                change_future = pool.submit(self.worker, run_change)
                self.assertEqual(sync_future.result(timeout=15)["code"], "success")
                change_future.result(timeout=15)
        self.user.refresh_from_db()
        if self.user.atcoder_username == "old":
            self.assertEqual(fetched, ["old"])
        elif fetched == ["old"]:
            # A completed old sync was cleared by the subsequent name change.
            self.assertFalse(Log.objects.filter(user=self.user).exists())
        else:
            self.assertEqual(fetched, ["new"])
