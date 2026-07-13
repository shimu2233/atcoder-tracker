from django.shortcuts import render
from django.views.generic import TemplateView,ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Log, Tag
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
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
class DashboardView(LoginRequiredMixin,TemplateView):
    template_name="logs/dashboard.html"
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
        return super().get_queryset().filter(tags__isnull=True)