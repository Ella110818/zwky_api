from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
import random

from course_management.models import Course, StudentCourse
from user_management.models import Student
from user_management.utils import api_response
from .models import CourseAnnouncement, Assignment, AssignmentSubmission, CourseGroup
from .serializers import (
    CourseAnnouncementSerializer, 
    AssignmentSerializer, 
    AssignmentSubmissionSerializer,
    StudentInfoSerializer,
    CourseGroupSerializer
)

class StandardResultsSetPagination(PageNumberPagination):
    """标准分页器"""
    page_size = 10
    page_size_query_param = 'size'
    max_page_size = 100


# 课程公告相关视图
class CourseAnnouncementView(APIView):
    """课程公告视图"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, course_id):
        """获取课程公告列表"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户是否有权限访问该课程
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限访问此课程",
                data=None
            )
        
        # 过滤条件
        announcement_type = request.query_params.get('type')
        
        # 查询公告
        announcements = CourseAnnouncement.objects.filter(course=course)
        
        # 应用过滤条件
        if announcement_type:
            announcements = announcements.filter(type=announcement_type)
        
        # 分页
        paginator = self.pagination_class()
        paginated_announcements = paginator.paginate_queryset(announcements, request)
        
        serializer = CourseAnnouncementSerializer(paginated_announcements, many=True)
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "total": paginator.page.paginator.count,
                "items": serializer.data
            }
        )
    
    def post(self, request, course_id):
        """发布课程公告"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查是否为教师
        user = request.user
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以发布公告",
                data=None
            )
        
        # 检查教师是否是该课程的教师
        try:
            teacher = user.teacher_profile
            if course.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是此课程的教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息不存在",
                data=None
            )
        
        # 创建公告
        serializer = CourseAnnouncementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course, publisher=user)
            
            return api_response(
                code=200,
                message="发布成功",
                data=serializer.data
            )
        else:
            return api_response(
                code=400,
                message="数据验证失败",
                data=serializer.errors
            )


# 作业与考试相关视图
class AssignmentView(APIView):
    """作业和考试视图"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, course_id):
        """获取作业和考试列表"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户是否有权限访问该课程
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限访问此课程",
                data=None
            )
        
        # 过滤条件
        assignment_type = request.query_params.get('type')
        status = request.query_params.get('status')
        
        # 查询作业和考试
        assignments = Assignment.objects.filter(course=course)
        
        # 应用过滤条件
        if assignment_type:
            assignments = assignments.filter(type=assignment_type)
        
        if status:
            # 由于status是属性不是字段，需要在Python中进行过滤
            filtered_assignments = []
            for assignment in assignments:
                if assignment.status == status:
                    filtered_assignments.append(assignment)
            assignments = filtered_assignments
        
        # 分页
        paginator = self.pagination_class()
        if isinstance(assignments, list):
            # 如果是Python过滤后的列表，手动分页
            page = int(request.query_params.get('page', 1))
            size = int(request.query_params.get('size', paginator.page_size))
            start = (page - 1) * size
            end = start + size
            total = len(assignments)
            paginated_assignments = assignments[start:end]
        else:
            # 如果是QuerySet，使用分页器
            paginated_assignments = paginator.paginate_queryset(assignments, request)
            total = paginator.page.paginator.count
        
        serializer = AssignmentSerializer(paginated_assignments, many=True)
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "total": total,
                "items": serializer.data
            }
        )
    
    def post(self, request, course_id):
        """发布作业或考试"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查是否为教师
        user = request.user
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以发布作业或考试",
                data=None
            )
        
        # 检查教师是否是该课程的教师
        try:
            teacher = user.teacher_profile
            if course.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是此课程的教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息不存在",
                data=None
            )
        
        # 创建作业或考试
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course)
            
            return api_response(
                code=200,
                message="发布成功",
                data=serializer.data
            )
        else:
            return api_response(
                code=400,
                message="数据验证失败",
                data=serializer.errors
            )


# 分组管理相关视图
class CourseGroupView(APIView):
    """课程分组视图"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """获取课程分组列表"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户是否有权限访问该课程
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限访问此课程",
                data=None
            )
        
        # 获取课程的所有学生
        course_students = StudentCourse.objects.filter(course=course).select_related('student')
        students = [cs.student for cs in course_students]
        
        # 获取课程的所有分组
        groups = CourseGroup.objects.filter(course=course).prefetch_related('students')
        
        # 找出未分组的学生
        grouped_student_ids = set()
        for group in groups:
            for student in group.students.all():
                grouped_student_ids.add(student.id)
        
        unassigned_students = [s for s in students if s.id not in grouped_student_ids]
        
        # 序列化数据
        group_serializer = CourseGroupSerializer(groups, many=True)
        student_serializer = StudentInfoSerializer(unassigned_students, many=True)
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "unassignedStudents": student_serializer.data,
                "groups": group_serializer.data
            }
        )
    
    def post(self, request, course_id):
        """创建或更新分组"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查是否为教师
        user = request.user
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以管理分组",
                data=None
            )
        
        # 检查教师是否是该课程的教师
        try:
            teacher = user.teacher_profile
            if course.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是此课程的教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息不存在",
                data=None
            )
        
        # 获取请求数据
        name = request.data.get('name')
        student_ids = request.data.get('studentIds', [])
        
        if not name:
            return api_response(
                code=400,
                message="分组名称不能为空",
                data=None
            )
        
        # 创建或更新分组
        with transaction.atomic():
            group, created = CourseGroup.objects.get_or_create(
                name=name,
                course=course,
                defaults={'name': name, 'course': course}
            )
            
            # 清除原有学生
            group.students.clear()
            
            # 添加新学生
            if student_ids:
                students = Student.objects.filter(id__in=student_ids)
                group.students.add(*students)
        
        serializer = CourseGroupSerializer(group)
        
        return api_response(
            code=200,
            message="创建成功" if created else "更新成功",
            data=serializer.data
        )


class AutoGroupView(APIView):
    """自动分组视图"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id):
        """自动分组"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查是否为教师
        user = request.user
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以管理分组",
                data=None
            )
        
        # 检查教师是否是该课程的教师
        try:
            teacher = user.teacher_profile
            if course.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是此课程的教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息不存在",
                data=None
            )
        
        # 获取请求数据
        group_count = request.data.get('groupCount')
        method = request.data.get('method', 'random')
        
        if not group_count or group_count <= 0:
            return api_response(
                code=400,
                message="分组数量必须大于0",
                data=None
            )
        
        # 获取课程的所有学生
        course_students = StudentCourse.objects.filter(course=course).select_related('student')
        students = [cs.student for cs in course_students]
        
        if not students:
            return api_response(
                code=400,
                message="课程没有学生",
                data=None
            )
        
        # 自动分组
        with transaction.atomic():
            # 清除原有分组
            CourseGroup.objects.filter(course=course).delete()
            
            # 创建新分组
            groups = []
            if method == 'random':
                # 随机分组
                random.shuffle(students)
            # 将来可以添加其他分组方法，如'average'
            
            # 分配学生
            students_per_group = len(students) // group_count
            remainder = len(students) % group_count
            
            start = 0
            for i in range(group_count):
                group_size = students_per_group + (1 if i < remainder else 0)
                group_students = students[start:start + group_size]
                start += group_size
                
                group = CourseGroup.objects.create(
                    name=f"第{i+1}组",
                    course=course
                )
                
                if group_students:
                    group.students.add(*group_students)
                
                groups.append(group)
        
        # 序列化数据
        serializer = CourseGroupSerializer(groups, many=True)
        
        return api_response(
            code=200,
            message="自动分组成功",
            data={
                "groups": serializer.data
            }
        ) 