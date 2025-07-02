from django.shortcuts import render
import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from openai import OpenAI
import httpx
import inspect
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# 获取logger
logger = logging.getLogger('zwky_api')

# Create your views here.

class ChatWithAIView(APIView):
    # 允许未认证访问
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        try:
            # 直接设置环境变量
            os.environ["OPENAI_API_KEY"] = "sk-c72bcb4af3e74c7880c6e832e251caf8"
            os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            # 清除代理相关环境变量
            for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
                if proxy_var in os.environ:
                    del os.environ[proxy_var]
            
            # 更深入的修复：直接修改SyncHttpxClientWrapper类
            from openai._base_client import SyncHttpxClientWrapper
            
            # 保存原始方法
            original_init = SyncHttpxClientWrapper.__init__
            signature = inspect.signature(original_init)
            
            # 定义修复后的初始化方法
            def patched_init(self, *args, **kwargs):
                # 移除proxies参数，如果存在
                if 'proxies' in kwargs:
                    logger.info("移除proxies参数")
                    del kwargs['proxies']
                
                # 调用原始初始化方法的非代理参数版本
                reduced_kwargs = {k:v for k,v in kwargs.items() if k != 'proxies'}
                httpx.Client.__init__(self, **reduced_kwargs)
            
            # 应用patch
            SyncHttpxClientWrapper.__init__ = patched_init
            logger.info("已应用SyncHttpxClientWrapper类的补丁")
            
            # 尝试初始化客户端
            self.client = OpenAI()
            logger.info("OpenAI客户端初始化成功")
        except Exception as e:
            logger.error(f"OpenAI客户端初始化失败: {str(e)}", exc_info=True)
            raise

    @swagger_auto_schema(
        operation_description="与 AI 助手进行对话",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['message'],
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='用户发送的消息'),
                'deep_thinking': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否启用深度思考模式', default=False),
            }
        ),
        responses={
            200: openapi.Response(
                description="成功响应",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'content': openapi.Schema(type=openapi.TYPE_STRING, description='AI 助手的回复内容'),
                        'reasoning': openapi.Schema(type=openapi.TYPE_STRING, description='推理过程（如果有）'),
                        'has_reasoning': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否包含推理过程'),
                    }
                )
            ),
            400: 'Bad Request - 消息不能为空',
            500: 'Internal Server Error - 处理请求时出错'
        }
    )
    def post(self, request):
        try:
            user_message = request.data.get('message')
            logger.info(f"收到AI助手请求: {user_message[:50]}...")
            
            if not user_message:
                return Response({'error': '消息不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取深度思考模式参数，默认为 False
            deep_thinking = request.data.get('deep_thinking', False)
            logger.info(f"深度思考模式: {deep_thinking}")

            logger.info("正在向OpenAI发送请求...")
            
            # 准备请求参数
            options = {
                "model": "deepseek-r1",
                "messages": [
                    {'role': 'user', 'content': user_message}
                ]
            }
            
            # 如果需要深度思考，添加相应参数
            if deep_thinking:
                options["reasoning"] = True
            
            # 发送请求
            completion = self.client.chat.completions.create(**options)

            # 记录成功响应
            logger.info("AI助手请求成功处理")
            
            # 检查是否有推理内容
            has_reasoning = hasattr(completion.choices[0].message, 'reasoning_content')
            logger.info(f"响应是否包含推理过程: {has_reasoning}")
            
            response_data = {
                'content': completion.choices[0].message.content,
                'reasoning': completion.choices[0].message.reasoning_content if has_reasoning else None,
                'has_reasoning': has_reasoning
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            # 记录详细错误信息
            logger.error(f"AI助手请求处理错误: {str(e)}", exc_info=True)
            return Response({'error': f"处理请求时出错: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
