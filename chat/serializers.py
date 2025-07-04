from rest_framework import serializers
from .models import ChatMessage
from course_management.models import StudentCourse

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    timestamp = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'sender_name', 'course', 'text', 'timestamp', 'is_read']
        read_only_fields = ['sender', 'sender_name', 'timestamp', 'is_read']

    def validate_course(self, value):
        request = self.context.get('request')
        if request and request.user:
            # 只验证用户是否登录，不再验证课程权限
            return value
        raise serializers.ValidationError("请先登录后再发送消息") 