from django.urls import path
from .views import DashboardView,TopView,ContestProblemsView,DailyTrainingView,sync_view,UnsolvedListView,DoLaterListView,toggle_do_later,LearningContentsView,LearningContentDetailView,goals_view,delete_goal
urlpatterns=[
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', TopView.as_view(), name='top'),
    path('learning/', LearningContentsView.as_view(), name='learning_contents'),
    path('learning/<str:content_id>/', LearningContentDetailView.as_view(), name='learning_content_detail'),
    path('contest-problems/', ContestProblemsView.as_view(), name='contest_problems'),
    path('daily-training/', DailyTrainingView.as_view(), name='daily_training'),
    path('sync/', sync_view, name='sync'),
    path('unsolved/', UnsolvedListView.as_view(), name='unsolved'),
    path('do-later/', DoLaterListView.as_view(), name='do_later'),
    path('goals/', goals_view, name='goals'),
    path('goals/<int:goal_id>/delete/', delete_goal, name='delete_goal'),
    path('problems/<str:problem_id>/toggle-do-later/', toggle_do_later, name='toggle_do_later'),
]

