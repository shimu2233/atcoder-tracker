from django.shortcuts import render
from django.views.generic import CreateView,UpdateView
from django.urls import reverse_lazy
from .forms import SignupForm
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import CustomUser

class SignupView(CreateView):
    form_class=SignupForm
    template_name="accounts/signup.html"
    success_url=reverse_lazy('login')
class SettingsView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    fields = ["atcoder_username"]
    template_name = "accounts/settings.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        return self.request.user