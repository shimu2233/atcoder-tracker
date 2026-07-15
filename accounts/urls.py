from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import SignupView ,SettingsView
urlpatterns=[
    path('login/',LoginView.as_view(template_name="accounts/login.html"), name='login'),
    path('logout/',LogoutView.as_view(), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('settings/', SettingsView.as_view(), name='settings'),
]