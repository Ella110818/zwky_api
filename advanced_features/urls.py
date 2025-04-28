from django.urls import path
from .views import (
    CourseAnnouncementView,
    AssignmentView,
    CourseGroupView,
    AutoGroupView
)

urlpatterns = [
    # 课程公告相关接口
    path('courses/<int:course_id>/announcements/', CourseAnnouncementView.as_view(), name='course-announcements'),
    
    # 作业与考试相关接口
    path('courses/<int:course_id>/assignments/', AssignmentView.as_view(), name='course-assignments'),
    
    # 分组管理相关接口
    path('courses/<int:course_id>/groups/', CourseGroupView.as_view(), name='course-groups'),
    path('courses/<int:course_id>/groups/auto', AutoGroupView.as_view(), name='auto-group'),
] 