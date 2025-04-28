from django.urls import path
from . import views

app_name = 'status_management'

urlpatterns = [
    # 在这里添加 status_management 的 URL 配置
    path('get_student_status/', views.get_student_status, name='get_student_status'),
] 