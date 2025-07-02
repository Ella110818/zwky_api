from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey('course_management.Course', on_delete=models.CASCADE, related_name='chat_messages')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.sender.username}: {self.text[:50]}'
