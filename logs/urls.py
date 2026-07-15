from django.urls import path
from .views import DashboardView,TopView,TessokuView,ContestProblemsView,DailyTrainingView,sync_view
urlpatterns=[
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', TopView.as_view(), name='top'),
    path('tessoku/', TessokuView.as_view(), name='tessoku'),
    path('contest-problems/', ContestProblemsView.as_view(), name='contest_problems'),
    path('daily-training/', DailyTrainingView.as_view(), name='daily_training'),
    path('sync/', sync_view, name='sync'),
]
