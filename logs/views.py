from django.shortcuts import render
from django.views.generic import TemplateView,ListView,UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Log, Tag, Problem
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q,Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from logs.services import sync_submissions
from django.urls import reverse_lazy
@login_required
def sync_view(request):
    if request.method == "POST":
        result = sync_submissions(request.user)
        if "error" in result:
            messages.error(request, result["error"])
        else:
            messages.success(
                request,
                f"同期しました（新規 {result['created']}件 / 更新 {result['updated']}件）"
            )
    return redirect("dashboard")
class TopView(TemplateView):
    template_name = "logs/top.html"
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "logs/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        total_by_category = {}
        for row in (
            Problem.objects
            .exclude(category="")
            .values("category")
            .annotate(total=Count("problem_id"))
        ):
            total_by_category[row["category"]] = row["total"]

        my_stats = {}
        for row in (
            Log.objects
            .filter(user=user)
            .exclude(problem__category="")
            .values("problem__category")
            .annotate(
                attempted=Count("id"),
                ac=Count("id", filter=Q(is_correct=True)),
            )
        ):
            my_stats[row["problem__category"]] = {
                "attempted": row["attempted"],
                "ac": row["ac"],
            }
        category_stats = []
        for category in sorted(total_by_category.keys()):
            total = total_by_category[category]
            stat = my_stats.get(category, {"attempted": 0, "ac": 0})
            attempted = stat["attempted"]
            ac = stat["ac"]

            category_stats.append({
                "category": category,
                "total": total,
                "attempted": attempted,
                "ac": ac,
                "attempt_rate": round(attempted / total * 100) if total else 0,
                "ac_rate": round(ac / total * 100) if total else 0,
            })
        context["category_stats"] = category_stats
        context["chart_labels"] = [s["category"] for s in category_stats]
        context["chart_attempt_rates"] = [s["attempt_rate"] for s in category_stats]
        context["chart_ac_rates"] = [s["ac_rate"] for s in category_stats]
        
        logs = (
            Log.objects
            .filter(user=user, problem__category="")
            .select_related("problem")
        )

        bands = {}
        for log in logs:
            d = log.problem.display_difficulty
            if d is None:
                continue
            band_start = int(d) // 400 * 400
            bands.setdefault(band_start, {"total": 0, "ac": 0})
            bands[band_start]["total"] += 1
            if log.is_correct:
                bands[band_start]["ac"] += 1

        difficulty_stats = []
        for band_start in sorted(bands.keys()):
            stat = bands[band_start]
            difficulty_stats.append({
                "band": f"{band_start}-{band_start + 399}",
                "total": stat["total"],
                "ac": stat["ac"],
                "ac_rate": round(stat["ac"] / stat["total"] * 100),
            })

        context["difficulty_stats"] = difficulty_stats
        context["difficulty_labels"] = [s["band"] for s in difficulty_stats]
        context["difficulty_ac_rates"] = [s["ac_rate"] for s in difficulty_stats]
        context["difficulty_totals"] = [s["total"] for s in difficulty_stats]
        return context
class TessokuView(LoginRequiredMixin, TemplateView):
    template_name = "logs/tessoku.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        my_logs = {}
        for log in Log.objects.filter(user=user).select_related("problem"):
            my_logs[log.problem_id] = log
        from collections import defaultdict
        by_category = defaultdict(list)

        problems = Problem.objects.exclude(category="").order_by("problem_id")
        for problem in problems:
            log = my_logs.get(problem.problem_id)
            if log is None:
                status = "未提出"
                status_order = 0
            elif log.is_correct:
                status = "AC済み"
                status_order = 2
            else:
                status = "未AC"
                status_order = 1

            by_category[problem.category].append({
                "problem": problem,
                "log":log,
                "status": status,
                "status_order": status_order,
                "url": f"https://atcoder.jp/contests/{problem.contest_id}/tasks/{problem.problem_id}",
            })
        category_problems = {}
        for category, items in by_category.items():
            category_problems[category] = sorted(items, key=lambda x: x["status_order"])

        context["category_problems"] = category_problems
        return context

class ContestProblemsView(LoginRequiredMixin, TemplateView):
    template_name = "logs/contest_problems.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        logs = (
            Log.objects
            .filter(user=user, problem__category="")
            .select_related("problem")
        )

        log_by_pid = {log.problem_id: log for log in logs}

        attempted_contest_ids = {
            log.problem.contest_id
            for log in logs
            if not log.problem.contest_id.startswith("adt_")   
        }

        all_problems = (
            Problem.objects
            .filter(contest_id__in=attempted_contest_ids, category="")
            .order_by("problem_id")
        )

        from collections import defaultdict
        by_index = defaultdict(list)

        for problem in all_problems:
            log = log_by_pid.get(problem.problem_id)
            if log is None:
                status = "未提出"
                status_order = 1
            elif log.is_correct:
                status = "AC済み"
                status_order = 2
            else:
                status = "未AC"
                status_order = 0

            by_index[problem.problem_index].append({
                "problem": problem,
                "log":log,
                "status": status,
                "status_order": status_order,
                "url": f"https://atcoder.jp/contests/{problem.contest_id}/tasks/{problem.problem_id}",
            })

        index_problems = {}
        for index in sorted(by_index.keys()):
            index_problems[index] = sorted(by_index[index], key=lambda x: x["status_order"])

        context["index_problems"] = index_problems
        return context
class DailyTrainingView(LoginRequiredMixin, TemplateView):
    template_name = "logs/daily_training.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        my_logs = {}
        for log in Log.objects.filter(user=user).select_related("problem"):
            my_logs[log.problem_id] = log

        attempted_contest_ids = {
            log.problem.contest_id
            for log in Log.objects.filter(user=user).select_related("problem")
            if log.problem.contest_id.startswith("adt_")
        }

        problems = (
            Problem.objects
            .filter(contest_id__in=attempted_contest_ids)
            .order_by("problem_id")
        )

        from collections import defaultdict
        by_label = defaultdict(list)

        for problem in problems:
            parts = problem.contest_id.split("_")
            label = parts[1] if len(parts) > 1 else "その他"

            log = my_logs.get(problem.problem_id)
            if log is None:
                status = "未提出"
                status_order = 1
            elif log.is_correct:
                status = "AC済み"
                status_order = 2
            else:
                status = "未AC"
                status_order = 0

            by_label[label].append({
                "problem": problem,
                "log":log,
                "status": status,
                "status_order": status_order,
                "url": f"https://atcoder.jp/contests/{problem.contest_id}/tasks/{problem.problem_id}",
            })

        label_problems = {}
        for label in sorted(by_label.keys()):
            label_problems[label] = sorted(by_label[label], key=lambda x: x["status_order"])

        context["label_problems"] = label_problems
        return context
class LogUpdateView(LoginRequiredMixin, UpdateView):
    model = Log
    fields = ["memo", "do_later"]
    template_name = "logs/log_edit.html"
    success_url = reverse_lazy("contest_problems")

    def get_queryset(self):
        return Log.objects.filter(user=self.request.user)
class DoLaterListView(LoginRequiredMixin, ListView):
    template_name = "logs/do_later.html"
    context_object_name = "logs"

    def get_queryset(self):
        return (Log.objects
                .filter(user=self.request.user, do_later=True)
                .select_related("problem"))

class UnsolvedListView(LoginRequiredMixin, ListView):
    template_name = "logs/unsolved.html"
    context_object_name = "logs"

    def get_queryset(self):
        return (Log.objects
                .filter(user=self.request.user, is_correct=False)
                .select_related("problem")
                .order_by("problem__display_difficulty"))
