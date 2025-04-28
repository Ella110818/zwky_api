from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Status

# Create your views here.

@api_view(['POST'])
def get_student_status(request):
    student_id = request.data.get('student_id')
    course_time_id = request.data.get('course_time_id')
    
    if not student_id or not course_time_id:
        return Response(
            {'error': '需要提供 student_id 和 course_time_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        status_obj = Status.objects.get(
            student_id=student_id,
            course_time_id=course_time_id
        )
        
        data = {
            'concentrate': status_obj.concentrate,
            'sleepy': status_obj.sleepy,
            'low_head': status_obj.low_head,
            'half': status_obj.half,
            'puzzle': status_obj.puzzle,
            'if_come': status_obj.if_come,
        }
        
        return Response(data)
        
    except Status.DoesNotExist:
        return Response(
            {'error': '未找到相关状态数据'},
            status=status.HTTP_404_NOT_FOUND
        )
