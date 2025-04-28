from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.CourseListView.as_view(), name='course-list'),
    path('courses/<str:course_id>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/<str:course_id>/resources/', views.CourseResourceListView.as_view(), name='course-resources'),
    path('resources/<int:resource_id>/', views.ResourceDetailView.as_view(), name='resource-detail'),
    path('resources/<int:resource_id>/download/', views.ResourceDownloadView.as_view(), name='resource-download'),
    path('courses/<int:course_id>/students/info/', views.CourseStudentInfoView.as_view(), name='course-student-info'),
    path('courses/<int:course_id>/start/', views.StartClassView.as_view(), name='start-class'),
    path('course-times/<int:course_time_id>/end/', views.EndClassView.as_view(), name='end-class'),
    path('course-times/<int:course_time_id>/upload-recording/', views.UploadCourseRecordingView.as_view(), name='upload-course-recording'),
    
    # 新增路由
    path('courses/<int:course_id>/course-times/', views.CourseTimesListView.as_view(), name='course-times-list'),
    path('course-times/<int:course_time_id>/recording/', views.RecordingDetailView.as_view(), name='recording-detail'),
    path('course-times/<int:course_time_id>/stream/', views.StreamRecordingView.as_view(), name='stream-recording'),
] 