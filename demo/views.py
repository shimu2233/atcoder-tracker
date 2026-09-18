from django.shortcuts import render,get_object_or_404
from django.views.generic import TemplateView
from accounts.models import CustomUser
from logs.views import difficulty_stats_for_user

DEMO_USERNAME = "demo" 

class DemoDashboardView(TemplateView):
    template_name = "demo/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(CustomUser, username=DEMO_USERNAME)
        difficulty_stats = difficulty_stats_for_user(user)

        context["difficulty_stats"] = difficulty_stats
        context["difficulty_labels"] = [s["band"] for s in difficulty_stats]
        context["difficulty_ac_rates"] = [s["ac_rate"] for s in difficulty_stats]
        context["difficulty_totals"] = [s["total"] for s in difficulty_stats]
        return context
