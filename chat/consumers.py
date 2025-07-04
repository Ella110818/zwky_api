import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from course_management.models import Course
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)
User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connect attempt")
        self.course_id = self.scope['url_route']['kwargs']['course_id']
        self.user = None

        # 从 URL 参数中获取 token
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            # 尝试认证
            authenticated = await self.authenticate(token)
            if authenticated:
                logger.info("Authentication successful via URL parameter")
                await self.accept()
                await self.send(json.dumps({
                    'type': 'authentication_successful',
                    'message': '认证成功'
                }))
                return
            else:
                logger.error("Authentication failed via URL parameter")
                return  # 拒绝连接
        
        # 如果没有 token，接受连接但等待认证消息
        await self.accept()
        logger.info("WebSocket connection accepted, waiting for authentication")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            logger.info(f"Received message: {text_data}")
            data = json.loads(text_data)
            
            # 如果用户未认证，只接受认证消息
            if not self.user:
                if data.get('type') == 'authentication':
                    token = data.get('token', '').replace('Bearer ', '')
                    logger.info("Processing authentication")
                    authenticated = await self.authenticate(token)
                    
                    if authenticated:
                        logger.info("Authentication successful")
                        await self.send(json.dumps({
                            'type': 'authentication_successful',
                            'message': '认证成功'
                        }))
                    else:
                        logger.error("Authentication failed")
                        await self.send(json.dumps({
                            'type': 'authentication_failed',
                            'message': '认证失败'
                        }))
                        await self.close()
                else:
                    await self.send(json.dumps({
                        'type': 'error',
                        'message': '未认证'
                    }))
                    await self.close()
                return

            # 处理聊天消息
            if 'message' in data:
                message = data['message']
                chat_message = await self.save_message(message)
                
                # 直接发送消息给当前连接
                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': message,
                    'sender': chat_message.sender.username,
                    'timestamp': chat_message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                }))

        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': '无效的JSON格式'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def authenticate(self, token):
        try:
            # 验证token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            self.user = User.objects.get(id=user_id)
            self.scope["user"] = self.user
            return True
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    @database_sync_to_async
    def save_message(self, message):
        course = Course.objects.get(id=self.course_id)
        chat_message = ChatMessage.objects.create(
            sender=self.user,
            text=message,
            course=course
        )
        return chat_message 