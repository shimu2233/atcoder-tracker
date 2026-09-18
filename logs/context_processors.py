from django.utils import timezone

from .goal_progress import JST, calculate_goal_progress
from .models import Goal


def goal_header(request):
    if (
        not request.user.is_authenticated
        or request.resolver_match is None
        or request.resolver_match.url_name == "top"
    ):
        return {"header_goal_cards": []}

    today = timezone.localdate(timezone=JST)
    goals = list(
        Goal.objects.filter(user=request.user, end_date__gte=today)
        .order_by("end_date", "created_at")[:3]
    )
    return {
        "header_goal_cards": [
            {"goal": goal, "progress": calculate_goal_progress(goal)}
            for goal in goals
        ]
    }
