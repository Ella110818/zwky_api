from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.db.models import Q, Avg, Min, Max, Count
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
import random

from course_management.models import Course, StudentCourse
from user_management.models import Student
from user_management.utils import api_response
from .models import CourseAnnouncement, Assignment, AssignmentSubmission, CourseGroup, GradeRecord
from .serializers import (
    CourseAnnouncementSerializer, 
    AssignmentSerializer, 
    AssignmentSubmissionSerializer,
    StudentInfoSerializer,
    CourseGroupSerializer,
    GradeRecordSerializer
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


class StudentGradeView(APIView):
    """学生成绩视图"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """获取当前学生的所有成绩记录，按成绩类型分组汇总"""
        user = request.user
        
        # 验证是否为学生
        if user.role != 'student':
            return api_response(
                code=403,
                message="只有学生可以查看自己的成绩",
                data=None
            )
        
        try:
            student = user.student_profile
        except:
            return api_response(
                code=404,
                message="学生信息不存在",
                data=None
            )
        
        # 获取查询参数
        semester = request.query_params.get('semester')
        course_id = request.query_params.get('course_id')
        
        # 查询成绩记录
        records = GradeRecord.objects.filter(student=student)
        
        # 应用过滤条件
        if semester:
            records = records.filter(semester=semester)
        
        if course_id:
            records = records.filter(course__course_id=course_id)
        
        # 按学期和课程分组整理数据
        result = {}
        
        # 分学期
        semesters = {}
        for record in records:
            sem = record.get_semester_display()
            if sem not in semesters:
                semesters[sem] = []
            semesters[sem].append(record)
        
        # 每个学期下按课程分组
        for sem, sem_records in semesters.items():
            courses = {}
            for record in sem_records:
                course_title = f"{record.course.course_id} {record.course.title}"
                if course_title not in courses:
                    courses[course_title] = {
                        "class_score": record.class_score,
                        "homework_score": record.homework_score,
                        "exam_score": record.exam_score,
                        "total_score": record.total_score,
                        "record_id": record.id
                    }
            
            result[sem] = {
                "courses": courses,
                "avg_score": sum(record.total_score for record in sem_records) / len(sem_records) if sem_records else 0
            }
        
        return api_response(
            code=200,
            message="获取成功",
            data=result
        )


class CourseGradeView(APIView):
    """课程成绩视图"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, course_id):
        """获取课程的所有学生成绩记录"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查是否为教师
        user = request.user
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以查看课程成绩",
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
        
        # 获取查询参数
        semester = request.query_params.get('semester')
        sort_by = request.query_params.get('sort_by', 'total_score')  # 默认按总分排序
        sort_order = request.query_params.get('sort_order', 'desc')  # 默认降序
        
        # 查询成绩记录
        records = GradeRecord.objects.filter(course=course)
        
        # 应用过滤条件
        if semester:
            records = records.filter(semester=semester)
        
        # 计算统计数据
        stats = {
            "count": records.count(),
            "avg_class_score": records.aggregate(Avg('class_score'))['class_score__avg'] or 0,
            "avg_homework_score": records.aggregate(Avg('homework_score'))['homework_score__avg'] or 0,
            "avg_exam_score": records.aggregate(Avg('exam_score'))['exam_score__avg'] or 0,
            "max_total_score": 0,
            "min_total_score": 0
        }
        
        # 处理排序
        records_list = list(records)
        
        # 按总分计算最高分和最低分
        if records_list:
            total_scores = [record.total_score for record in records_list]
            stats["max_total_score"] = max(total_scores)
            stats["min_total_score"] = min(total_scores)
            
            # 按照字段排序
            if sort_by in ['class_score', 'homework_score', 'exam_score']:
                records_list.sort(
                    key=lambda x: getattr(x, sort_by) or 0,
                    reverse=(sort_order.lower() == 'desc')
                )
            elif sort_by == 'total_score':
                records_list.sort(
                    key=lambda x: x.total_score,
                    reverse=(sort_order.lower() == 'desc')
                )
            elif sort_by == 'student_id':
                records_list.sort(
                    key=lambda x: x.student.user.staff_id,
                    reverse=(sort_order.lower() == 'desc')
                )
            elif sort_by == 'student_name':
                records_list.sort(
                    key=lambda x: x.student.user.username,
                    reverse=(sort_order.lower() == 'desc')
                )
        
        # 分页
        paginator = self.pagination_class()
        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', paginator.page_size))
        
        start = (page - 1) * size
        end = start + size
        
        serializer = GradeRecordSerializer(records_list[start:end], many=True)
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "total": len(records_list),
                "items": serializer.data,
                "stats": stats
            }
        )
    
    def post(self, request, course_id):
        """批量添加或更新成绩记录"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查是否为教师
        user = request.user
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以修改成绩",
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
        
        # 获取提交的数据
        records_data = request.data.get('records', [])
        semester = request.data.get('semester')
        
        if not semester:
            return api_response(
                code=400,
                message="学期信息不能为空",
                data=None
            )
        
        updated_records = []
        
        with transaction.atomic():
            for record_data in records_data:
                student_id = record_data.get('student_id')
                
                try:
                    student = Student.objects.get(user__staff_id=student_id)
                except Student.DoesNotExist:
                    continue
                
                # 尝试找到现有记录
                try:
                    record = GradeRecord.objects.get(
                        student=student,
                        course=course,
                        semester=semester
                    )
                except GradeRecord.DoesNotExist:
                    record = GradeRecord(
                        student=student,
                        course=course,
                        semester=semester
                    )
                
                # 更新成绩
                if 'class_score' in record_data:
                    record.class_score = record_data['class_score']
                if 'homework_score' in record_data:
                    record.homework_score = record_data['homework_score']
                if 'exam_score' in record_data:
                    record.exam_score = record_data['exam_score']
                
                record.save()
                updated_records.append(record)
        
        serializer = GradeRecordSerializer(updated_records, many=True)
        
        return api_response(
            code=200,
            message="成绩保存成功",
            data=serializer.data
        ) 