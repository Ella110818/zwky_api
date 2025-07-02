from django.shortcuts import render
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
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
    只提供获取课程消息列表和创建新消息的功能
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
            )
        ],
        responses={
            200: ChatMessageSerializer(many=True),
            404: 'No messages found for the specified course.'
        }
    )
    def list(self, request, *args, **kwargs):
        """获取指定课程的所有聊天消息列表"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {"detail": "course_id is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"detail": "No messages found for the specified course."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=ChatMessageSerializer,
        responses={201: ChatMessageSerializer}
    )
    def create(self, request, *args, **kwargs):
        """创建新的聊天消息"""
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        if not course_id:
            return ChatMessage.objects.none()
            
        return ChatMessage.objects.filter(course_id=course_id).select_related('sender')

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
