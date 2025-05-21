from rest_framework import serializers
from user_management.models import Student
from user_management.serializers import UserInfoSerializer
from .models import CourseAnnouncement, Assignment, AssignmentSubmission, CourseGroup, GradeRecord

class CourseAnnouncementSerializer(serializers.ModelSerializer):
    """课程公告序列化器"""
    publisher_info = UserInfoSerializer(source='publisher', read_only=True)
    
    class Meta:
        model = CourseAnnouncement
        fields = ['id', 'title', 'content', 'type', 'publisher_info', 'created_at', 'updated_at']
        read_only_fields = ['id', 'publisher_info', 'created_at', 'updated_at']

class AssignmentSerializer(serializers.ModelSerializer):
    """作业和考试序列化器"""
    status = serializers.CharField(read_only=True)
    submitted = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = ['id', 'title', 'type', 'description', 'start_time', 'deadline', 
                 'status', 'full_score', 'submitted', 'total']
        read_only_fields = ['id', 'status', 'submitted', 'total']
    
    def get_submitted(self, obj):
        """获取已提交学生数"""
        return obj.submissions.count()
    
    def get_total(self, obj):
        """获取总学生数"""
        return obj.course.studentcourse_set.count()

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """作业提交序列化器"""
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    student_id = serializers.CharField(source='student.user.staff_id', read_only=True)
    
    class Meta:
        model = AssignmentSubmission
        fields = ['id', 'student_name', 'student_id', 'file', 'content', 
                 'score', 'feedback', 'submitted_at']
        read_only_fields = ['id', 'student_name', 'student_id', 'submitted_at']

class StudentInfoSerializer(serializers.ModelSerializer):
    """学生信息序列化器（用于分组）"""
    name = serializers.CharField(source='user.username')
    studentId = serializers.CharField(source='user.staff_id')
    avatar = serializers.CharField(source='user.avatar', allow_null=True)
    
    class Meta:
        model = Student
        fields = ['id', 'name', 'studentId', 'avatar']

class CourseGroupSerializer(serializers.ModelSerializer):
    """课程分组序列化器"""
    students = StudentInfoSerializer(many=True, read_only=True)
    
    class Meta:
        model = CourseGroup
        fields = ['id', 'name', 'students', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """自定义输出格式"""
        ret = super().to_representation(instance)
        # 只保留必要字段
        return {
            'id': ret['id'],
            'name': ret['name'],
            'students': ret['students']
        }

class GradeRecordSerializer(serializers.ModelSerializer):
    """成绩记录序列化器"""
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    student_id = serializers.CharField(source='student.user.staff_id', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_code = serializers.CharField(source='course.course_id', read_only=True)
    semester_display = serializers.CharField(source='get_semester_display', read_only=True)
    total_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = GradeRecord
        fields = ['id', 'student', 'student_name', 'student_id', 'course', 'course_title', 
                 'course_code', 'class_score', 'homework_score', 'exam_score', 
                 'semester', 'semester_display', 'total_score', 'created_at', 'updated_at']
        read_only_fields = ['id', 'student_name', 'student_id', 'course_title', 
                           'course_code', 'semester_display', 'total_score', 
                           'created_at', 'updated_at'] 