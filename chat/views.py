from django.shortcuts import render
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q
from .models import ChatMessage
from .serializers import ChatMessageSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Create your views here.

class ChatMessageViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    """
    聊天消息视图集
    提供获取课程消息列表、创建新消息、获取未读消息和标记消息已读的功能
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'course_id',
                openapi.IN_QUERY,
                description='课程ID',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'since',
                openapi.IN_QUERY,
                description='获取此时间戳之后的消息（ISO格式）',
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: ChatMessageSerializer(many=True),
            404: 'No messages found for the specified course.'
        }
    )
    def list(self, request, *args, **kwargs):
        """获取指定课程的聊天消息列表"""
        course_id = request.query_params.get('course_id')
        since = request.query_params.get('since')
        
        if not course_id:
            return Response(
                {"detail": "course_id is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset()
        
        if since:
            try:
                since_dt = timezone.datetime.fromisoformat(since)
                queryset = queryset.filter(timestamp__gt=since_dt)
            except ValueError:
                return Response(
                    {"detail": "Invalid timestamp format. Use ISO format."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 移除404检查，直接序列化并返回结果（可能是空列表）
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=ChatMessageSerializer,
        responses={201: ChatMessageSerializer}
    )
    def create(self, request, *args, **kwargs):
        """创建新的聊天消息"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'course_id',
                openapi.IN_QUERY,
                description='课程ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """获取未读消息数量"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {"detail": "course_id is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        unread_count = ChatMessage.objects.filter(
            course_id=course_id,
            is_read=False
        ).exclude(sender=request.user).count()
        
        return Response({"unread_count": unread_count})

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER)
                )
            }
        )
    )
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """标记消息为已读"""
        message_ids = request.data.get('message_ids', [])
        if not message_ids:
            return Response(
                {"detail": "message_ids is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated = ChatMessage.objects.filter(
            id__in=message_ids,
            is_read=False
        ).exclude(sender=request.user).update(is_read=True)
        
        return Response({"marked_as_read": updated})

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        if not course_id:
            return ChatMessage.objects.none()
            
        return ChatMessage.objects.filter(course_id=course_id).select_related('sender')

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
