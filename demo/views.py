from django.shortcuts import render,get_object_or_404
from django.views.generic import TemplateView
from django.db.models import Count, Q
from accounts.models import CustomUser
from logs.models import Log, Problem

DEMO_USERNAME = "demo" 

class DemoDashboardView(TemplateView):
    template_name = "demo/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(CustomUser, username=DEMO_USERNAME)
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
        logs = Log.objects.filter(user=user, problem__category="").select_related("problem")
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
