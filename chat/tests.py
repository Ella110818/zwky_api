from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from course_management.models import Course
from .models import ChatMessage
from datetime import datetime

User = get_user_model()

class ChatMessageModelTests(TestCase):
    def setUp(self):
        """测试前创建基础数据"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Course Description'
        )

    def test_create_message(self):
        """测试创建聊天消息"""
        message = ChatMessage.objects.create(
            sender=self.user,
            text='Test message',
            course=self.course
        )
        self.assertEqual(message.text, 'Test message')
        self.assertEqual(message.sender, self.user)
        self.assertEqual(message.course, self.course)
        self.assertIsInstance(message.timestamp, datetime)

    def test_message_str_method(self):
        """测试消息的字符串表示"""
        message = ChatMessage.objects.create(
            sender=self.user,
            text='Test message',
            course=self.course
        )
        expected_str = f'{self.user.username}: Test message'
        self.assertTrue(str(message).startswith(expected_str))

class ChatMessageAPITests(APITestCase):
    def setUp(self):
        """测试前创建基础数据"""
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )
        
        # 创建测试课程
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Course Description'
        )
        
        # 创建一些测试消息
        self.message = ChatMessage.objects.create(
            sender=self.user,
            text='Test message 1',
            course=self.course
        )

    def test_get_messages_authenticated(self):
        """测试已认证用户获取消息列表"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/chat/messages/?course_id={self.course.course_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], 'Test message 1')

    def test_get_messages_unauthenticated(self):
        """测试未认证用户获取消息列表"""
        response = self.client.get(f'/api/chat/messages/?course_id={self.course.course_id}')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_message_authenticated(self):
        """测试已认证用户创建消息"""
        self.client.force_authenticate(user=self.user)
        data = {
            'text': 'New test message',
            'course': self.course.course_id
        }
        response = self.client.post('/api/chat/messages/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatMessage.objects.count(), 2)
        self.assertEqual(response.data['text'], 'New test message')
        self.assertEqual(response.data['sender_name'], self.user.username)

    def test_create_message_unauthenticated(self):
        """测试未认证用户创建消息"""
        data = {
            'text': 'New test message',
            'course': self.course.course_id
        }
        response = self.client.post('/api/chat/messages/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_messages_by_course(self):
        """测试按课程筛选消息"""
        # 创建另一个课程和消息
        other_course = Course.objects.create(
            title='Other Course',
            description='Other Course Description'
        )
        ChatMessage.objects.create(
            sender=self.user,
            text='Message in other course',
            course=other_course
        )

        self.client.force_authenticate(user=self.user)
        
        # 测试第一个课程的消息
        response = self.client.get(f'/api/chat/messages/?course_id={self.course.course_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], 'Test message 1')

        # 测试第二个课程的消息
        response = self.client.get(f'/api/chat/messages/?course_id={other_course.course_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], 'Message in other course')

    def test_message_timestamp_format(self):
        """测试消息时间戳格式"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/chat/messages/?course_id={self.course.course_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 验证时间戳格式是否正确 (YYYY-MM-DD HH:MM:SS)
        timestamp = response.data[0]['timestamp']
        try:
            datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            is_valid_format = True
        except ValueError:
            is_valid_format = False
        self.assertTrue(is_valid_format)
