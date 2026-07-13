from django.urls import path
from .views import DashboardView, LogListView,update_tags,create_tag,UntaggedLogListView
urlpatterns=[
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('logs/', LogListView.as_view(), name='log_list'),
    path('logs/<int:log_id>/tags/', update_tags, name='update_tags'),
    path('logs/creates/', create_tag, name='create_tag'),
    path('logs/untagged/', UntaggedLogListView.as_view(), name='untagged_log_list'),
    path('logs/untagged/', UntaggedLogListView.as_view(), name='untagged_log_list'),
]