from django.shortcuts import render
from django.views.generic import TemplateView,ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Log, Tag, Problem
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q,Count
@login_required
def create_tag(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            Tag.objects.get_or_create(
                name=name,
                defaults={
                    "is_default": False,
                    "created_by": request.user,
                },
            )
    return redirect("log_list")
@login_required
def update_tags(request, log_id):
    log = get_object_or_404(Log, id=log_id, user=request.user)
    
    if request.method == "POST":
        tag_ids = request.POST.getlist("tags")  
        log.tags.set(tag_ids)
    
    return redirect("log_list")
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
class LogListView(LoginRequiredMixin,ListView):
    model=Log
    template_name="logs/log_list.html"
    context_object_name="logs"
    def get_queryset(self):
        return Log.objects.filter(user=self.request.user).select_related("problem").prefetch_related("tags")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_tags"] = Tag.objects.filter(
            Q(is_default=True) | Q(created_by=self.request.user)
        )
        context["untagged_count"] = Log.objects.filter(
        user=self.request.user, tags__isnull=True
        ).count()
        return context
class UntaggedLogListView(LogListView):
    def get_queryset(self):
        return super().get_queryset().filter(tags__isnull=True)
class UntaggedLogListView(LogListView):
    def get_queryset(self):
        return super().get_queryset().filter(tags__isnull=True, problem__category="")