from django.shortcuts import render
from django.views.generic import TemplateView,ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Contest, ContestAttempt, ContestProblem, Log, Tag, Problem,DoLater,Goal
from .forms import GoalForm
from .goal_progress import calculate_goal_progress
from .contest_classification import (
    EVERGREEN_CONTENTS,
    SERIES_LABELS,
    SERIES_ORDER,
    classify_contest,
    tessoku_section,
)
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q,Count,Exists,OuterRef
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from logs.services import sync_submissions


def problem_status(log):
    if log is None:
        return "未提出", 0
    if log.is_correct:
        return "AC済み", 2
    return "未AC", 1


def problem_item_data(problem, problem_index, status, is_do_later, url):
    return {
        "problem_id": problem.problem_id,
        "problem_index": problem_index or problem.problem_index or "",
        "name": problem.problem_name,
        "category": problem.category or "",
        "difficulty": problem.display_difficulty,
        "status": status,
        "is_do_later": is_do_later,
        "url": url,
        "toggle_url": reverse("toggle_do_later", args=[problem.problem_id]),
    }


def difficulty_stats_for_user(user):
    heuristic_ids = set(
        Contest.objects.filter(contest_format="HEURISTIC")
        .values_list("contest_id", flat=True)
    )
    attempts = (
        ContestAttempt.objects.filter(user=user)
        .exclude(submitted_contest_id__in=EVERGREEN_CONTENTS)
        .exclude(submitted_contest_id__in=heuristic_ids)
        .exclude(submitted_contest_id__startswith="adt_")
        .select_related("problem")
    )

    by_problem = {}
    for attempt in attempts:
        if attempt.submitted_contest_id.startswith("ahc"):
            continue
        difficulty = attempt.problem.display_difficulty
        if difficulty is None:
            continue
        stat = by_problem.setdefault(
            attempt.problem_id,
            {"difficulty": difficulty, "is_correct": False},
        )
        stat["is_correct"] = stat["is_correct"] or attempt.is_correct

    bands = {}
    for stat in by_problem.values():
        band_start = int(stat["difficulty"]) // 400 * 400
        bands.setdefault(band_start, {"total": 0, "ac": 0})
        bands[band_start]["total"] += 1
        if stat["is_correct"]:
            bands[band_start]["ac"] += 1

    return [
        {
            "band": f"{band_start}-{band_start + 399}",
            "total": stat["total"],
            "ac": stat["ac"],
            "ac_rate": round(stat["ac"] / stat["total"] * 100),
        }
        for band_start, stat in sorted(bands.items())
    ]


def learning_content_context(user, contest_id):
    relations = list(
        ContestProblem.objects.filter(contest_id=contest_id)
        .select_related("contest", "problem")
        .order_by("problem_index")
    )
    problem_ids = [relation.problem_id for relation in relations]
    log_by_pid = {
        log.problem_id: log
        for log in Log.objects.filter(user=user, problem_id__in=problem_ids)
    }
    do_later_ids = set(
        DoLater.objects.filter(user=user, problem_id__in=problem_ids)
        .values_list("problem_id", flat=True)
    )

    sections = {}
    for relation in relations:
        log = log_by_pid.get(relation.problem_id)
        status, status_order = problem_status(log)
        section = (
            f"鉄則{tessoku_section(relation.problem_index)}"
            if contest_id == "tessoku-book"
            else "問題一覧"
        )
        sections.setdefault(section, []).append({
            "problem": relation.problem,
            "problem_index": relation.problem_index,
            "log": log,
            "status": status,
            "status_order": status_order,
            "is_do_later": relation.problem_id in do_later_ids,
            "url": (
                f"https://atcoder.jp/contests/{contest_id}/tasks/"
                f"{relation.problem_id}"
            ),
        })

    for items in sections.values():
        items.sort(key=lambda item: (item["status_order"], item["problem_index"]))

    contest = Contest.objects.filter(contest_id=contest_id).first()
    content_title = contest.title if contest else EVERGREEN_CONTENTS[contest_id]
    serialized_sections = [
        {
            "name": section_name,
            "items": [
                {
                    "problem_id": item["problem"].problem_id,
                    "problem_index": item["problem_index"],
                    "name": item["problem"].problem_name,
                    "category": item["problem"].category or "",
                    "difficulty": item["problem"].display_difficulty,
                    "status": item["status"],
                    "is_do_later": item["is_do_later"],
                    "url": item["url"],
                    "toggle_url": reverse(
                        "toggle_do_later", args=[item["problem"].problem_id]
                    ),
                }
                for item in items
            ],
        }
        for section_name, items in sections.items()
    ]
    return {
        "content_id": contest_id,
        "content_title": content_title,
        "sections": sections,
        "has_membership_data": bool(relations),
        "content_data": {
            "content_id": contest_id,
            "title": content_title,
            "has_membership_data": bool(relations),
            "sections": serialized_sections,
        },
    }
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

        difficulty_stats = difficulty_stats_for_user(user)

        context["difficulty_stats"] = difficulty_stats
        context["difficulty_labels"] = [s["band"] for s in difficulty_stats]
        context["difficulty_ac_rates"] = [s["ac_rate"] for s in difficulty_stats]
        context["difficulty_totals"] = [s["total"] for s in difficulty_stats]
        context["dashboard_data"] = {
            "difficulty_stats": difficulty_stats,
            "messages": [str(message) for message in messages.get_messages(self.request)],
        }
        return context
class LearningContentsView(LoginRequiredMixin, TemplateView):
    template_name = "logs/learning_contents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        stats = []
        for content_id, fallback_title in EVERGREEN_CONTENTS.items():
            relations = ContestProblem.objects.filter(contest_id=content_id)
            problem_ids = relations.values_list("problem_id", flat=True)
            logs = Log.objects.filter(user=user, problem_id__in=problem_ids)
            total = relations.count()
            attempted = logs.count()
            ac = logs.filter(is_correct=True).count()
            contest = Contest.objects.filter(contest_id=content_id).first()
            stats.append({
                "content_id": content_id,
                "title": contest.title if contest else fallback_title,
                "total": total,
                "attempted": attempted,
                "ac": ac,
                "attempt_rate": round(attempted / total * 100) if total else 0,
                "ac_rate": round(ac / total * 100) if total else 0,
                "detail_url": reverse("learning_content_detail", args=[content_id]),
            })
        context["content_stats"] = stats
        return context


class LearningContentDetailView(LoginRequiredMixin, TemplateView):
    template_name = "logs/learning_content_detail.html"

    def get_context_data(self, **kwargs):
        content_id = kwargs["content_id"]
        if content_id not in EVERGREEN_CONTENTS:
            from django.http import Http404
            raise Http404("常設教材が見つかりません")
        context = super().get_context_data(**kwargs)
        context.update(learning_content_context(self.request.user, content_id))
        return context


class ContestProblemsView(LoginRequiredMixin, TemplateView):
    template_name = "logs/contest_problems.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        logs = list(Log.objects.filter(user=user).select_related("problem"))
        log_by_pid = {log.problem_id: log for log in logs}
        attempts = list(
            ContestAttempt.objects.filter(user=user).select_related("problem")
        )
        attempted_contest_ids = sorted({
            attempt.submitted_contest_id
            for attempt in attempts
            if attempt.submitted_contest_id not in EVERGREEN_CONTENTS
            and not attempt.submitted_contest_id.startswith("adt_")
        })
        do_later_ids = set(
            DoLater.objects.filter(user=user).values_list("problem_id", flat=True)
        )

        contests = {
            contest.contest_id: contest
            for contest in Contest.objects.filter(contest_id__in=attempted_contest_ids)
        }
        grouped = {series: [] for series in SERIES_ORDER}
        attempts_by_contest = {}
        for attempt in attempts:
            attempts_by_contest.setdefault(attempt.submitted_contest_id, []).append(attempt)
        for contest_id in attempted_contest_ids:
            contest = contests.get(contest_id)
            series = contest.series if contest else classify_contest(contest_id)[0]
            relations = list(
                ContestProblem.objects.filter(contest_id=contest_id)
                .select_related("problem")
                .order_by("problem_index")
            )
            items = []
            for relation in relations:
                log = log_by_pid.get(relation.problem_id)
                status, status_order = problem_status(log)
                items.append({
                    "problem": relation.problem,
                    "problem_index": relation.problem_index,
                    "log": log,
                    "is_do_later": relation.problem_id in do_later_ids,
                    "status": status,
                    "status_order": status_order,
                    "url": (
                        f"https://atcoder.jp/contests/{contest_id}/tasks/"
                        f"{relation.problem_id}"
                    ),
                })
            if not items:
                for attempt in attempts:
                    if attempt.submitted_contest_id != contest_id:
                        continue
                    log = log_by_pid.get(attempt.problem_id)
                    status, status_order = problem_status(log)
                    items.append({
                        "problem": attempt.problem,
                        "problem_index": attempt.problem.problem_index,
                        "log": log,
                        "is_do_later": attempt.problem_id in do_later_ids,
                        "status": status,
                        "status_order": status_order,
                        "url": (
                            f"https://atcoder.jp/contests/{contest_id}/tasks/"
                            f"{attempt.problem_id}"
                        ),
                    })
            contest_attempts = attempts_by_contest.get(contest_id, [])
            last_submitted_at = max(
                (attempt.last_submitted_date for attempt in contest_attempts),
                default=None,
            )
            grouped.setdefault(series, []).append({
                "contest_id": contest_id,
                "title": contest.title if contest else contest_id,
                "last_submitted_at": (
                    last_submitted_at.isoformat() if last_submitted_at else ""
                ),
                "items": sorted(
                    items,
                    key=lambda item: (item["status_order"], item["problem_index"]),
                ),
            })

        contest_groups = [
            {"series": series, "label": SERIES_LABELS[series], "contests": grouped[series]}
            for series in SERIES_ORDER
            if grouped.get(series)
        ]
        context["contest_groups"] = contest_groups

        category_labels = {
            "algorithm": "アルゴリズム",
            "heuristic": "ヒューリスティック",
            "grand": "グランド",
        }
        categories = {
            key: {"key": key, "label": label, "groups": []}
            for key, label in category_labels.items()
        }
        for group in contest_groups:
            if group["series"] == "AGC":
                category_key = "grand"
            elif group["series"] in {"AHC", "HEURISTIC_OTHER"}:
                category_key = "heuristic"
            else:
                category_key = "algorithm"

            categories[category_key]["groups"].append({
                "series": group["series"],
                "label": group["label"],
                "contests": [
                    {
                        "contest_id": contest["contest_id"],
                        "title": contest["title"],
                        "last_submitted_at": contest["last_submitted_at"],
                        "items": [
                            {
                                "problem_id": item["problem"].problem_id,
                                "problem_index": item["problem_index"],
                                "name": item["problem"].problem_name,
                                "category": item["problem"].category or "",
                                "difficulty": item["problem"].display_difficulty,
                                "status": item["status"],
                                "is_do_later": item["is_do_later"],
                                "url": item["url"],
                                "toggle_url": reverse(
                                    "toggle_do_later",
                                    args=[item["problem"].problem_id],
                                ),
                            }
                            for item in contest["items"]
                        ],
                    }
                    for contest in group["contests"]
                ],
            })
        context["contest_data"] = {"categories": list(categories.values())}
        return context
class DailyTrainingView(LoginRequiredMixin, TemplateView):
    template_name = "logs/daily_training.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        my_logs = {}
        for log in Log.objects.filter(user=user).select_related("problem"):
            my_logs[log.problem_id] = log

        attempted_contest_ids = set(
            ContestAttempt.objects.filter(
                user=user,
                submitted_contest_id__startswith="adt_",
            ).values_list("submitted_contest_id", flat=True)
        )

        relations = (
            ContestProblem.objects
            .filter(contest_id__in=attempted_contest_ids)
            .select_related("problem")
            .order_by("contest_id", "problem_index")
        )

        from collections import defaultdict
        by_label = defaultdict(list)
        do_later_ids = set(
            DoLater.objects.filter(user=user).values_list("problem_id", flat=True)
        )
        for relation in relations:
            problem = relation.problem
            parts = relation.contest_id.split("_")
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
                "problem_index": relation.problem_index,
                "contest_id": relation.contest_id,
                "log":log,
                "is_do_later": problem.problem_id in do_later_ids,
                "status": status,
                "status_order": status_order,
                "url": f"https://atcoder.jp/contests/{relation.contest_id}/tasks/{problem.problem_id}",
            })

        label_problems = {}
        for label in sorted(by_label.keys()):
            label_problems[label] = sorted(by_label[label], key=lambda x: x["status_order"])

        context["label_problems"] = label_problems
        context["problem_list_data"] = {
            "sections": [
                {
                    "name": label,
                    "items": [
                        problem_item_data(
                            item["problem"],
                            item["problem_index"],
                            item["status"],
                            item["is_do_later"],
                            item["url"],
                        )
                        for item in items
                    ],
                }
                for label, items in label_problems.items()
            ],
            "empty_message": "デイリートレーニングの問題はありません。",
            "remove_when_unbookmarked": False,
        }
        return context
class DoLaterListView(LoginRequiredMixin, ListView):
    template_name = "logs/do_later.html"
    context_object_name = "do_laters"

    def get_queryset(self):
        return (DoLater.objects
                .filter(user=self.request.user)
                .select_related("problem"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entries = list(context["do_laters"])
        problem_ids = [entry.problem_id for entry in entries]
        log_by_pid = {
            log.problem_id: log
            for log in Log.objects.filter(
                user=self.request.user, problem_id__in=problem_ids
            )
        }
        context["problem_list_data"] = {
            "sections": [{
                "name": "後でやる",
                "items": [
                    problem_item_data(
                        entry.problem,
                        entry.problem.problem_index,
                        problem_status(log_by_pid.get(entry.problem_id))[0],
                        True,
                        (
                            f"https://atcoder.jp/contests/{entry.problem.contest_id}/tasks/"
                            f"{entry.problem_id}"
                        ),
                    )
                    for entry in entries
                ],
            }],
            "empty_message": "「後でやる」に登録した問題はありません。",
            "remove_when_unbookmarked": True,
        }
        return context

class UnsolvedListView(LoginRequiredMixin, ListView):
    template_name = "logs/unsolved.html"
    context_object_name = "logs"

    def get_queryset(self):
        return (Log.objects
                .filter(user=self.request.user, is_correct=False)
                .select_related("problem")
                .annotate(
                    is_do_later=Exists(
                        DoLater.objects.filter(
                            user=self.request.user,
                            problem_id=OuterRef("problem_id"),
                        )
                    )
                )
                .order_by("problem__display_difficulty"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = list(context["logs"])
        context["problem_list_data"] = {
            "sections": [{
                "name": "未AC",
                "items": [
                    problem_item_data(
                        log.problem,
                        log.problem.problem_index,
                        "未AC",
                        log.is_do_later,
                        (
                            f"https://atcoder.jp/contests/{log.problem.contest_id}/tasks/"
                            f"{log.problem_id}"
                        ),
                    )
                    for log in logs
                ],
            }],
            "empty_message": "未ACの問題はありません。",
            "remove_when_unbookmarked": False,
        }
        return context

@login_required
def toggle_do_later(request, problem_id):
    if request.method == "POST":
        problem = get_object_or_404(Problem, problem_id=problem_id)
        obj,created=DoLater.objects.get_or_create(
            user=request.user,problem=problem
        )
        if not created:
            obj.delete()
    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


@login_required
def goals_view(request):
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, "目標を作成しました。")
            return redirect("goals")
    else:
        form = GoalForm()

    goal_cards = [
        {"goal": goal, "progress": calculate_goal_progress(goal)}
        for goal in Goal.objects.filter(user=request.user)
    ]
    return render(
        request,
        "logs/goals.html",
        {"form": form, "goal_cards": goal_cards},
    )


@login_required
def delete_goal(request, goal_id):
    if request.method == "POST":
        goal = get_object_or_404(Goal, id=goal_id, user=request.user)
        goal.delete()
        messages.success(request, "目標を削除しました。")
    return redirect("goals")
