from django.shortcuts import render
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import SignupForm
class SignupView(CreateView):
    form_class=SignupForm
    template_name="accounts/signup.html"
    success_url=reverse_lazy('login')