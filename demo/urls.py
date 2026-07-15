from django.urls import path
from .views import DemoDashboardView

urlpatterns = [
    path('', DemoDashboardView.as_view(), name='demo_dashboard'),
]