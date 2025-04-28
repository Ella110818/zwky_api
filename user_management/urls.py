from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RegisterView, LoginView, LogoutView, CustomTokenRefreshView
from .views import UserMessageView

urlpatterns = [
    # 认证相关
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    # 用户消息相关
    path('user/messages/', UserMessageView.as_view(), name='user_messages'),
]