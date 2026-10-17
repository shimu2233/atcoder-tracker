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
    def form_valid(self, form):
        from django.http import HttpResponseRedirect
        from logs.services import change_atcoder_username

        result = change_atcoder_username(
            self.request.user, form.cleaned_data['atcoder_username'],
        )
        if 'error' in result:
            form.add_error('atcoder_username', result['error'])
            return self.form_invalid(form)
        self.object.refresh_from_db()
        return HttpResponseRedirect(self.get_success_url())
