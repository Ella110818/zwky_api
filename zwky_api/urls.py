"""
URL configuration for zwky_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse

# Swagger文档配置
schema_view = get_schema_view(
    openapi.Info(
        title="智慧课堂 API",
        default_version='v1',
        description="智慧课堂系统的API文档",
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# 添加CSRF视图函数
@ensure_csrf_cookie
def csrf_view(request):
    return HttpResponse("CSRF cookie set")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('user/', include('user_management.urls')),
        path('course/', include('course_management.urls')),  # 启用课程管理URLs
        path('class/', include('class_management.urls')),
        path('status/', include('status_management.urls')),
        path('advanced/', include('advanced_features.urls')),  # 添加高级功能URLs
        path('ai/', include('ai_assistant.urls')),
        path('chat/', include('chat.urls')),
    ])),
    # 添加人脸识别应用的URL
    path('face_recognition/', include('face_recognition.urls')),
    
    # 添加CSRF视图URL
    path('csrf/', csrf_view, name='csrf'),
    
    # Swagger文档URL
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# 添加媒体文件URL配置（仅在开发环境中使用）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
