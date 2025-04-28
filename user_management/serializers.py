from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Student, Teacher
from course_management.models import CourseTime, Course, StudentCourse
from class_management.models import Class
from status_management.models import Status

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    name = serializers.CharField(source='first_name', required=True)
    
    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'role', 'name', 'phone')
        extra_kwargs = {
            'email': {'required': True},
            'role': {'required': True},
            'phone': {'required': False}
        }
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("邮箱已存在")
        return value
    
    def create(self, validated_data):
        first_name = validated_data.pop('first_name', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=first_name,
            role=validated_data['role'],
            phone=validated_data.get('phone', None)
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class UserInfoSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    name = serializers.CharField(source='first_name')
    userId = serializers.CharField(source='id')
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M:%S')
    
    class Meta:
        model = User
        fields = ('userId', 'username', 'name', 'email', 'phone', 'role', 'avatar', 'createTime')
        read_only_fields = ('userId', 'username', 'createTime')

# 新增序列化器
class CourseTimeSerializer(serializers.ModelSerializer):
    """课程时间序列化器"""
    course_name = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = CourseTime
        fields = ('id', 'begin_time', 'end_time', 'course', 'course_name')

class StatusSerializer(serializers.ModelSerializer):
    """状态序列化器"""
    course_time_detail = CourseTimeSerializer(source='course_time', read_only=True)
    
    class Meta:
        model = Status
        fields = ('id', 'concentrate', 'sleepy', 'low_head', 'half', 'puzzle', 'if_come', 'course_time', 'course_time_detail')

class ClassSerializer(serializers.ModelSerializer):
    """班级序列化器"""
    class Meta:
        model = Class
        fields = ('class_id', 'class_name', 'class_system')

class StudentCourseSerializer(serializers.ModelSerializer):
    """学生课程序列化器"""
    course_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentCourse
        fields = ('id', 'course', 'course_detail')
    
    def get_course_detail(self, obj):
        course = obj.course
        return {
            'course_id': course.course_id,
            'title': course.title,
            'description': course.description,
            'location': course.location,
            'system': course.system,
            'schedule': course.schedule,
            'semester': course.semester
        }

class StudentDetailSerializer(serializers.ModelSerializer):
    """学生详细信息序列化器"""
    class_detail = ClassSerializer(source='class_id', read_only=True)
    statuses = StatusSerializer(many=True, read_only=True)
    courses = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = ('student_id', 'class_id', 'class_detail', 'statuses', 'courses')
    
    def get_courses(self, obj):
        student_courses = obj.student_courses.all()
        return StudentCourseSerializer(student_courses, many=True).data

class TeacherCourseSerializer(serializers.ModelSerializer):
    """教师课程序列化器"""
    class Meta:
        model = Course
        fields = ('course_id', 'title', 'description', 'location', 'system', 'schedule', 'semester')

class TeacherDetailSerializer(serializers.ModelSerializer):
    """教师详细信息序列化器"""
    courses = TeacherCourseSerializer(many=True, read_only=True)
    course_times = CourseTimeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Teacher
        fields = ('teacher_id', 'teacher_title', 'courses', 'course_times')

class UserMessageSerializer(serializers.ModelSerializer):
    """用户消息序列化器"""
    name = serializers.CharField(source='first_name')
    userId = serializers.CharField(source='id')
    student_detail = serializers.SerializerMethodField()
    teacher_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('userId', 'username', 'name', 'email', 'phone', 'role', 'avatar', 'student_detail', 'teacher_detail')
    
    def get_student_detail(self, obj):
        if obj.role != 'student':
            return None
        try:
            student = Student.objects.get(student_id=obj.id)
            return StudentDetailSerializer(student).data
        except Student.DoesNotExist:
            return None
    
    def get_teacher_detail(self, obj):
        if obj.role != 'teacher':
            return None
        try:
            teacher = Teacher.objects.get(teacher_id=obj.id)
            return TeacherDetailSerializer(teacher).data
        except Teacher.DoesNotExist:
            return None