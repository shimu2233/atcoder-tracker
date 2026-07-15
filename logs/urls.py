from django.urls import path
from .views import DashboardView, LogListView,update_tags,create_tag,UntaggedLogListView,TopView,TessokuView,ContestProblemsView,DailyTrainingView
urlpatterns=[
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('logs/', LogListView.as_view(), name='log_list'),
    path('logs/<int:log_id>/tags/', update_tags, name='update_tags'),
    path('logs/creates/', create_tag, name='create_tag'),
    path('logs/untagged/', UntaggedLogListView.as_view(), name='untagged_log_list'),
    path('logs/untagged/', UntaggedLogListView.as_view(), name='untagged_log_list'),
    path('', TopView.as_view(), name='top'),
    path('tessoku/', TessokuView.as_view(), name='tessoku'),
    path('contest-problems/', ContestProblemsView.as_view(), name='contest_problems'),
    path('daily-training/', DailyTrainingView.as_view(), name='daily_training'),
]