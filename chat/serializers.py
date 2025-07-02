from rest_framework import serializers
from .models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    timestamp = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender_name', 'text', 'timestamp', 'course']
        read_only_fields = ['sender_name', 'timestamp'] 