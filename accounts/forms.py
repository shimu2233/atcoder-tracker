from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser
class SignupForm(UserCreationForm):
    class Meta:
        model=CustomUser
        fields=['username', 'email', 'atcoder_username']
