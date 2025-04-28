from django.shortcuts import render
from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework import status
# from django.views.decorators.csrf import csrf_exempt  # 不再需要CSRF装饰器
# from django.utils.decorators import method_decorator  # 不再需要装饰器工具
from .serializers import UserRegisterSerializer, UserLoginSerializer, UserInfoSerializer, UserMessageSerializer
from .utils import api_response, ErrorCode
import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User

User = get_user_model()

# 获取日志记录器
logger = logging.getLogger('zwky_api')

# 自定义令牌刷新视图
class CustomTokenRefreshView(TokenRefreshView):
    """
    自定义令牌刷新视图，格式化响应格式
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = TokenRefreshSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return api_response(
                code=400,
                message="刷新令牌无效或已过期",
                data=None
            )
            
        return api_response(
            code=200,
            message="令牌刷新成功",
            data=serializer.validated_data
        )

class RegisterView(APIView):
    """
    用户注册视图
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserInfoSerializer(user).data
            return api_response(
                code=200,
                message="注册成功",
                data={
                    "userId": user_data['userId'],
                    "username": user_data['username']
                }
            )
        else:
            # 处理验证错误
            if 'username' in serializer.errors:
                return api_response(
                    code=ErrorCode.USERNAME_EXISTS,
                    message="用户名已存在",
                    data=None
                )
            elif 'email' in serializer.errors:
                return api_response(
                    code=ErrorCode.EMAIL_EXISTS,
                    message="邮箱已存在",
                    data=None
                )
            else:
                return api_response(
                    code=400,
                    message=str(serializer.errors),
                    data=None
                )


# 移除CSRF装饰器
class LoginView(APIView):
    """
    用户登录视图
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # 生成JWT令牌
                refresh = RefreshToken.for_user(user)
                user_data = UserInfoSerializer(user).data
                
                return api_response(
                    code=200,
                    message="登录成功",
                    data={
                        "token": str(refresh.access_token),  # 访问令牌
                        "refresh": str(refresh),             # 刷新令牌
                        "userId": user_data['userId'],
                        "username": user_data['username'],
                        "role": user_data['role'],
                        "avatar": user_data['avatar']
                    }
                )
            else:
                return api_response(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="用户名或密码错误",
                    data=None
                )
        else:
            return api_response(
                code=400,
                message=str(serializer.errors),
                data=None
            )

class LogoutView(APIView):
    """
    用户退出登录视图
    """
    permission_classes = [AllowAny]  # 修改为允许任何人访问
    
    def post(self, request):
        # JWT无状态，客户端只需删除token即可
        return api_response(
            code=200,
            message="退出成功",
            data=None
        )

class UserMessageView(APIView):
    """
    用户消息视图
    获取用户的所有消息，包括关联的课程和课时状态等信息
    """
    # 用户消息接口需要认证
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """获取当前登录用户的所有消息"""
        # 优先使用已验证的登录用户
        if request.user.is_authenticated:
            user = request.user
        else:
            # 向下兼容，仍然支持通过参数获取
            user_id = request.query_params.get('user_id')
            if not user_id:
                return api_response(
                    code=400,
                    message="用户ID不能为空",
                    data=None
                )
                
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return api_response(
                    code=404,
                    message="用户不存在",
                    data=None
                )
                
        serializer = UserMessageSerializer(user)
        
        return api_response(
            code=200,
            message="获取用户消息成功",
            data=serializer.data
        )
    
    def post(self, request):
        """根据用户ID获取指定用户的所有消息"""
        try:
            # 优先使用请求中的用户ID
            user_id = request.data.get('user_id')
            
            # 如果没有用户ID且用户已登录，使用当前用户
            if not user_id and request.user.is_authenticated:
                user = request.user
            else:
                if not user_id:
                    return api_response(
                        code=400,
                        message="用户ID不能为空",
                        data=None
                    )
                    
                user = User.objects.get(id=user_id)
                
            serializer = UserMessageSerializer(user)
            
            return api_response(
                code=200,
                message="获取用户消息成功",
                data=serializer.data
            )
        except User.DoesNotExist:
            return api_response(
                code=404,
                message="用户不存在",
                data=None
            )
        except Exception as e:
            return api_response(
                code=500,
                message=f"服务器错误: {str(e)}",
                data=None
            )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserInfoSerializer

    def create(self, request, *args, **kwargs):
        try:
            # 记录用户创建操作
            logger.info(f"开始创建新用户，请求数据: {request.data}")
            
            # 使用UserRegisterSerializer进行用户创建
            serializer = UserRegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # 使用UserInfoSerializer返回用户信息
            response_serializer = UserInfoSerializer(user)
            
            logger.info(f"用户创建成功 - ID: {user.id}, 用户名: {user.username}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"用户创建失败 - 错误信息: {str(e)}", exc_info=True)
            raise

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        user = self.get_object()
        try:
            # 记录密码修改尝试
            logger.info(f"用户 {user.username} 开始修改密码")
            
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            
            if not user.check_password(old_password):
                logger.warning(f"用户 {user.username} 密码修改失败：旧密码验证失败")
                return Response({"error": "旧密码不正确"}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(new_password)
            user.save()
            
            logger.info(f"用户 {user.username} 密码修改成功")
            return Response({"message": "密码修改成功"})
        except Exception as e:
            logger.error(f"用户 {user.username} 密码修改失败 - 错误信息: {str(e)}", exc_info=True)
            raise

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            # 记录用户删除操作
            logger.warning(f"准备删除用户 - ID: {user.id}, 用户名: {user.username}")
            
            user.delete()
            
            logger.info(f"用户删除成功 - ID: {user.id}, 用户名: {user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"用户删除失败 - ID: {user.id}, 错误信息: {str(e)}", exc_info=True)
            raise