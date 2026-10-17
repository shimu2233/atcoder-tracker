from datetime import datetime, date, timedelta
from unittest.mock import patch, Mock
from io import StringIO

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from logs.models import Problem, Contest, ContestAttempt, Log, Goal, GoalAC, SubmissionSyncState, DoLater
from logs.goal_progress import JST, calculate_goal_progress
from logs.services import sync_submissions, change_atcoder_username, _fetch_submissions


def submission(number, when, result="AC", problem="abc500_a", contest="abc500"):
    return {"id": number, "epoch_second": int(when.timestamp()), "result": result,
            "problem_id": problem, "contest_id": contest}


class IncrementalSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="incremental", atcoder_username="coder")
        self.problem = Problem.objects.create(problem_id="abc500_a", problem_name="A", contest_id="abc500", display_difficulty=800)
        Contest.objects.create(contest_id="abc500", title="ABC", series="ABC")
        self.start = datetime(2026, 10, 18, tzinfo=JST)
        self.now = datetime(2026, 10, 18, 18, tzinfo=JST)

    def goal(self, **kwargs):
        values = dict(user=self.user, title="Goal", start_date=date(2026, 10, 18),
                      end_date=date(2026, 10, 20), target_count=1, contest_types=["ALGORITHM"],
                      difficulty_min=400, difficulty_max=1199)
        values.update(kwargs)
        return Goal.objects.create(**values)

    def sync(self, items, **kwargs):
        SubmissionSyncState.objects.filter(user=self.user).update(last_started_at=None)
        response = Mock()
        response.json.return_value = items
        with patch("logs.services.requests.get", return_value=response) as get:
            result = sync_submissions(self.user, **kwargs)
            return result, get.call_args.kwargs["params"]["from_second"]

    def test_initial_sync_then_lookback_and_idempotence(self):
        item = submission(1, self.now)
        result, start = self.sync([item])
        self.assertEqual(start, 0)
        self.assertEqual(result["created"], 1)
        state = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(state.last_submission_epoch, item["epoch_second"])
        self.assertIsNotNone(state.last_succeeded_at)
        result, start = self.sync([item])
        self.assertEqual(start, item["epoch_second"] - 3600)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(Log.objects.count(), 1)
        self.assertEqual(ContestAttempt.objects.count(), 1)

    def test_merge_preserves_ac_and_dates_for_log_and_attempt(self):
        first = self.now - timedelta(minutes=30)
        self.sync([submission(1, first)])
        self.sync([submission(2, self.now, "WA")])
        self.sync([submission(3, self.now + timedelta(minutes=10))])
        for model in (Log, ContestAttempt):
            obj = model.objects.get(user=self.user)
            self.assertTrue(obj.is_correct)
            self.assertEqual(obj.first_ac_date, first)
            self.assertEqual(obj.last_ac_date, self.now + timedelta(minutes=10))
        self.sync([submission(0, first - timedelta(minutes=1))], full_refresh=True)
        for model in (Log, ContestAttempt):
            obj = model.objects.get(user=self.user)
            self.assertEqual(obj.first_ac_date, first - timedelta(minutes=1))
            self.assertEqual(obj.last_submitted_date, self.now + timedelta(minutes=10))

    def test_empty_sync_keeps_position_and_updates_success_time(self):
        self.sync([submission(1, self.now)])
        before = SubmissionSyncState.objects.get(user=self.user)
        result, _ = self.sync([])
        after = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(result["code"], "success")
        self.assertEqual(after.last_submission_epoch, before.last_submission_epoch)
        self.assertGreaterEqual(after.last_succeeded_at, before.last_succeeded_at)

    def test_new_goal_backfills_once_and_counts_repeated_ac(self):
        self.sync([submission(1, self.now - timedelta(days=3)), submission(2, self.now)])
        goal = self.goal()
        result, start = self.sync([submission(2, self.now)])
        self.assertEqual(start, int(self.start.timestamp()))
        goal.refresh_from_db()
        self.assertTrue(goal.submissions_checked)
        self.assertEqual(calculate_goal_progress(goal)["completed_count"], 1)
        _, next_start = self.sync([submission(2, self.now)])
        self.assertEqual(next_start, int(self.now.timestamp()) - 3600)
        self.assertEqual(GoalAC.objects.count(), 1)

    def test_overlapping_goals_and_first_in_period_ac_survive_later_ac(self):
        first_goal = self.goal()
        second_goal = self.goal(title="Second")
        first = self.start + timedelta(hours=1)
        self.sync([submission(1, first), submission(2, self.now)])
        self.assertEqual(GoalAC.objects.count(), 2)
        self.assertEqual(GoalAC.objects.get(goal=first_goal).ac_date, first)
        self.sync([submission(3, self.now + timedelta(days=5))])
        for goal in (first_goal, second_goal):
            self.assertEqual(calculate_goal_progress(goal)["completed_count"], 1)
            self.assertEqual(GoalAC.objects.get(goal=goal).ac_date, first)
        first_goal.delete()
        self.assertEqual(GoalAC.objects.count(), 1)

    def test_jst_boundaries_and_filters_use_actual_submission_contest(self):
        goal = self.goal(end_date=self.start.date())
        outside = self.goal(title="Wrong type", contest_types=["EVERGREEN"])
        hard = self.goal(title="Wrong difficulty", difficulty_min=1200, difficulty_max=1500)
        self.sync([
            submission(1, self.start - timedelta(seconds=1)),
            submission(2, self.start),
            submission(3, self.start + timedelta(days=1)),
        ])
        self.assertEqual(GoalAC.objects.get(goal=goal).ac_date, self.start)
        self.assertFalse(GoalAC.objects.filter(goal__in=[outside, hard]).exists())

    def test_end_boundary_is_excluded(self):
        goal = self.goal(end_date=self.start.date())
        self.sync([submission(1, self.start + timedelta(days=1))])
        self.assertFalse(GoalAC.objects.filter(goal=goal).exists())

    def test_existing_problem_reac_in_new_contest_type_counts(self):
        goal = self.goal(contest_types=["EVERGREEN"])
        self.sync([submission(1, self.start - timedelta(days=1)),
                   submission(2, self.now, contest="abs")])
        self.assertEqual(calculate_goal_progress(goal)["completed_count"], 1)
        self.assertEqual(Log.objects.get(user=self.user).submitted_contest_id, "abc500")

    def test_unknown_problem_does_not_advance_or_partially_save(self):
        goal = self.goal()
        result, _ = self.sync([submission(1, self.now), submission(2, self.now, problem="unknown")])
        self.assertEqual(result["code"], "unknown_problem")
        self.assertFalse(Log.objects.exists())
        self.assertFalse(GoalAC.objects.exists())
        state = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(state.last_submission_epoch, 0)
        self.assertIsNone(state.last_succeeded_at)
        self.assertFalse(state.is_running)
        goal.refresh_from_db()
        self.assertFalse(goal.submissions_checked)

    def test_save_failure_rolls_back_history_goals_and_checkpoint(self):
        goal = self.goal()
        with patch("logs.services.calculate_goal_progress", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                self.sync([submission(1, self.now)])
        self.assertFalse(Log.objects.exists())
        self.assertFalse(ContestAttempt.objects.exists())
        self.assertFalse(GoalAC.objects.exists())
        state = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(state.last_submission_epoch, 0)
        self.assertIsNone(state.last_succeeded_at)
        self.assertFalse(state.is_running)
        goal.refresh_from_db()
        self.assertFalse(goal.submissions_checked)

    def test_network_failure_keeps_existing_checkpoint(self):
        self.sync([submission(1, self.now)])
        state = SubmissionSyncState.objects.get(user=self.user)
        before = state.last_submission_epoch
        SubmissionSyncState.objects.filter(pk=state.pk).update(last_started_at=None)
        with patch("logs.services.requests.get", side_effect=requests.Timeout):
            self.assertEqual(sync_submissions(self.user)["code"], "fetch_failed")
        state.refresh_from_db()
        self.assertEqual(state.last_submission_epoch, before)
        self.assertFalse(state.is_running)

    def test_name_change_resets_records_and_keeps_goal_and_cooldown(self):
        goal = self.goal()
        DoLater.objects.create(user=self.user, problem=self.problem)
        self.sync([submission(1, self.now)])
        before = SubmissionSyncState.objects.get(user=self.user).last_started_at
        change_atcoder_username(self.user, "another")
        state = SubmissionSyncState.objects.get(user=self.user)
        self.assertEqual(state.last_submission_epoch, 0)
        self.assertIsNone(state.last_succeeded_at)
        self.assertEqual(state.last_started_at, before)
        self.assertFalse(GoalAC.objects.exists())
        self.assertFalse(Log.objects.exists())
        self.assertFalse(ContestAttempt.objects.exists())
        self.assertTrue(DoLater.objects.exists())
        goal.refresh_from_db()
        self.assertFalse(goal.submissions_checked)
        self.assertIsNone(goal.achieved_at)

    def test_goal_created_during_fetch_is_checked_on_next_sync(self):
        captured = []
        def fetch(*args):
            captured.append(self.goal())
            return [submission(1, self.now)]
        with patch("logs.services._fetch_submissions", side_effect=fetch):
            self.assertEqual(sync_submissions(self.user)["code"], "success")
        goal = captured[0]
        goal.refresh_from_db()
        self.assertFalse(goal.submissions_checked)
        self.assertFalse(GoalAC.objects.filter(goal=goal).exists())
        _, start = self.sync([submission(1, self.now)])
        self.assertEqual(start, int(self.start.timestamp()))
        goal.refresh_from_db()
        self.assertTrue(goal.submissions_checked)

    def test_full_option_refetches_but_does_not_remove_observed_acs(self):
        goal = self.goal()
        self.sync([submission(1, self.now)])
        result, start = self.sync([submission(1, self.now, "WA")], full_refresh=True)
        self.assertEqual(start, 0)
        self.assertTrue(Log.objects.get().is_correct)
        self.assertEqual(GoalAC.objects.filter(goal=goal).count(), 1)
        with patch("logs.management.commands.fetch_submissions.sync_submissions", return_value={"created": 0, "updated": 0}) as sync:
            call_command("fetch_submissions", self.user.username, full=True, stdout=StringIO())
            self.assertTrue(sync.call_args.kwargs["full_refresh"])

    def test_unique_goal_problem(self):
        goal = self.goal()
        GoalAC.objects.create(goal=goal, problem=self.problem, ac_date=self.now)
        with self.assertRaises(IntegrityError), transaction.atomic():
            GoalAC.objects.create(goal=goal, problem=self.problem, ac_date=self.now)


class PaginationTests(TestCase):
    def setUp(self):
        self.when = datetime(2026, 10, 18, tzinfo=JST)

    @patch("logs.services.time.sleep")
    @patch("logs.services.requests.get")
    def test_same_second_boundary_is_included_and_ids_deduplicated(self, get, sleep):
        first = [submission(i, self.when + timedelta(seconds=i)) for i in range(499)]
        boundary = submission(499, self.when + timedelta(seconds=500))
        extra = submission(500, self.when + timedelta(seconds=500))
        get.return_value.json.side_effect = [first + [boundary], [boundary, extra]]
        result = _fetch_submissions("coder", 0)
        self.assertEqual(len(result), 501)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["from_second"], boundary["epoch_second"])
        sleep.assert_called_once_with(1.1)

    @patch("logs.services.time.sleep")
    @patch("logs.services.requests.get")
    def test_stalled_page_fails_instead_of_skipping(self, get, sleep):
        get.return_value.json.return_value = [submission(i, self.when) for i in range(500)]
        with self.assertRaises(ValueError):
            _fetch_submissions("coder", int(self.when.timestamp()))
        self.assertEqual(get.call_count, 2)

    @patch("logs.services.time.sleep")
    @patch("logs.services.requests.get")
    def test_page_limit_is_failure(self, get, sleep):
        get.return_value.json.return_value = [submission(i, self.when) for i in range(500)]
        with patch("logs.services.SUBMISSION_PAGE_LIMIT", 1):
            with self.assertRaises(ValueError):
                _fetch_submissions("coder", 0)

    @patch("logs.services.requests.get")
    def test_invalid_id_or_timestamp_is_rejected(self, get):
        for field, value in (("id", "bad"), ("epoch_second", -1), ("result", None)):
            item = submission(1, self.when)
            item[field] = value
            get.return_value.json.return_value = [item]
            with self.subTest(field=field), self.assertRaises(ValueError):
                _fetch_submissions("coder", 0)


class LegacyGoalMigrationTests(TransactionTestCase):
    def test_existing_progress_survives_migration(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        before = [("logs", "0014_submissionsyncstate")]
        after = [("logs", "0016_seed_goal_ac_records")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            User = apps.get_model("accounts", "CustomUser")
            OldProblem = apps.get_model("logs", "Problem")
            OldGoal = apps.get_model("logs", "Goal")
            OldLog = apps.get_model("logs", "Log")
            OldContest = apps.get_model("logs", "Contest")
            OldAttempt = apps.get_model("logs", "ContestAttempt")
            user = User.objects.create(username="legacy")
            problem = OldProblem.objects.create(problem_id="abc500_a", problem_name="A", contest_id="abc500", display_difficulty=800)
            OldContest.objects.create(contest_id="abc500", title="ABC", series="ABC")
            when = datetime(2026, 10, 18, 12, tzinfo=JST)
            OldLog.objects.create(user=user, problem=problem, submitted_contest_id="abc500", is_correct=True, first_ac_date=when, last_submitted_date=when)
            OldAttempt.objects.create(user=user, problem=problem, submitted_contest_id="abc500", is_correct=True, first_ac_date=when, last_submitted_date=when)
            goal = OldGoal.objects.create(user=user, title="Legacy", start_date=date(2026, 10, 18), end_date=date(2026, 10, 20), target_count=1, contest_types=["ALGORITHM"], difficulty_min=400, difficulty_max=1199)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            goal = Goal.objects.get(pk=goal.pk)
            self.assertEqual(calculate_goal_progress(goal)["completed_count"], 1)
            self.assertFalse(goal.submissions_checked)
            self.assertEqual(Log.objects.get(user_id=user.pk).last_ac_date, when)
            self.assertEqual(ContestAttempt.objects.get(user_id=user.pk).last_ac_date, when)
            self.assertEqual(SubmissionSyncState.objects.filter(user_id=user.pk).count(), 0)
        finally:
            MigrationExecutor(connection).migrate(after)
