from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, FileResponse
from urllib.parse import quote
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
import os
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
import mimetypes
import re

from .models import Course, StudentCourse, CourseResource, CourseTime
from .serializers import CourseListSerializer, CourseDetailSerializer, CourseResourceSerializer, CourseResourceDetailSerializer, CourseTimeSerializer, RecordingSerializer
from user_management.utils import api_response


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页器"""
    page_size = 10
    page_size_query_param = 'size'
    max_page_size = 100


class CourseListView(APIView):
    """
    课程列表视图
    获取当前用户相关的课程列表
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """获取当前用户可查看的课程列表"""
        user = request.user
        
        # 根据用户角色获取对应课程
        if user.role == 'teacher':
            # 教师只能查看自己教授的课程
            try:
                teacher = user.teacher_profile
                courses = Course.objects.filter(teacher=teacher)
            except:
                courses = Course.objects.none()
        elif user.role == 'student':
            # 学生只能查看自己选择的课程
            try:
                student = user.student_profile
                student_courses = StudentCourse.objects.filter(student=student)
                course_ids = [sc.course_id for sc in student_courses]
                courses = Course.objects.filter(course_id__in=course_ids)
            except:
                courses = Course.objects.none()
        else:
            # 未知角色，暂时不返回任何课程
            courses = Course.objects.none()
        
        # 使用分页器
        paginator = self.pagination_class()
        paginated_courses = paginator.paginate_queryset(courses, request)
        
        serializer = CourseListSerializer(paginated_courses, many=True)
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "total": paginator.page.paginator.count,
                "items": serializer.data
            }
        )


class CourseDetailView(APIView):
    """
    课程详情视图
    获取特定课程的详细信息
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """获取特定课程的详细信息"""
        user = request.user
        
        # 获取课程对象
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户权限
        has_permission = False
        
        if user.role == 'teacher':
            # 教师只能查看自己教授的课程
            try:
                teacher = user.teacher_profile
                has_permission = (course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            # 学生只能查看自己选择的课程
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
        
        serializer = CourseDetailSerializer(course)
        
        return api_response(
            code=200,
            message="获取成功",
            data=serializer.data
        )


class CourseResourceListView(APIView):
    """
    课程资源列表视图
    获取和上传课程资源
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request, course_id):
        """获取课程的资源列表"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户权限（必须是课程的教师或学生）
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
                message="您没有权限访问此课程资源",
                data=None
            )
        
        # 过滤条件
        resource_type = request.query_params.get('type')
        search_query = request.query_params.get('search')
        
        # 查询资源
        resources = CourseResource.objects.filter(course=course)
        
        # 应用过滤条件
        if resource_type:
            resources = resources.filter(type=resource_type)
        
        if search_query:
            resources = resources.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # 分页
        paginator = self.pagination_class()
        paginated_resources = paginator.paginate_queryset(resources, request)
        
        serializer = CourseResourceSerializer(
            paginated_resources, 
            many=True,
            context={'request': request}
        )
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "total": paginator.page.paginator.count,
                "items": serializer.data
            }
        )
    
    def post(self, request, course_id):
        """上传课程资源"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户权限（必须是课程的教师）
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (course.teacher == teacher)
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限上传资源到此课程",
                data=None
            )
        
        # 获取上传的文件
        file_obj = request.FILES.get('file')
        if not file_obj:
            return api_response(
                code=400,
                message="未提供文件",
                data=None
            )
        
        # 准备资源数据
        resource_data = {
            'name': request.data.get('name', file_obj.name),
            'type': request.data.get('type', 'document'),  # 默认为文档类型
            'description': request.data.get('description', ''),
            'file': file_obj,
            'size': f"{file_obj.size / 1024:.1f}KB" if file_obj.size < 1024 * 1024 else f"{file_obj.size / (1024 * 1024):.1f}MB",
            'course': course,
            'uploader': user
        }
        
        # 创建资源
        resource = CourseResource.objects.create(**resource_data)
        
        # 序列化返回
        serializer = CourseResourceSerializer(
            resource,
            context={'request': request}
        )
        
        return api_response(
            code=200,
            message="上传成功",
            data=serializer.data
        )


class ResourceDetailView(APIView):
    """
    资源详情视图
    获取和删除资源
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resource_id):
        """获取资源详情"""
        resource = get_object_or_404(CourseResource, id=resource_id)
        
        # 检查用户权限
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (resource.course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=resource.course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限访问此资源",
                data=None
            )
        
        serializer = CourseResourceDetailSerializer(
            resource,
            context={'request': request}
        )
        
        return api_response(
            code=200,
            message="获取成功",
            data=serializer.data
        )
    
    def delete(self, request, resource_id):
        """删除资源"""
        resource = get_object_or_404(CourseResource, id=resource_id)
        
        # 检查用户权限（必须是资源的上传者或课程教师）
        user = request.user
        has_permission = (resource.uploader == user)
        
        if not has_permission and user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (resource.course.teacher == teacher)
            except:
                pass
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限删除此资源",
                data=None
            )
        
        # 删除文件
        if resource.file and os.path.exists(resource.file.path):
            try:
                os.remove(resource.file.path)
            except:
                pass
        
        # 删除数据库记录
        resource.delete()
        
        return api_response(
            code=200,
            message="删除成功",
            data=None
        )


class ResourceDownloadView(APIView):
    """
    资源下载视图
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resource_id):
        """下载资源"""
        resource = get_object_or_404(CourseResource, id=resource_id)
        
        # 检查用户权限
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (resource.course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=resource.course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限下载此资源",
                data=None
            )
        
        # 检查文件是否存在
        if not resource.file or not os.path.exists(resource.file.path):
            return api_response(
                code=404,
                message="文件不存在",
                data=None
            )
        
        # 增加下载计数
        resource.download_count += 1
        resource.save()
        
        # 获取文件类型
        file_path = resource.file.path
        
        try:
            # 尝试直接返回文件
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = f'attachment; filename="{quote(resource.name)}"'
            return response
        except Exception as e:
            # 如果直接返回失败，返回下载链接
            return api_response(
                code=200,
                message="下载链接生成成功",
                data={
                    "downloadUrl": request.build_absolute_uri(resource.file.url)
                }
            )


class CourseStudentInfoView(APIView):
    """
    获取课程学生信息视图
    根据课程ID获取学生的详细信息
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """获取课程学生的详细信息"""
        user = request.user
        
        # 检查用户权限（只有教师可以查看）
        if user.role != 'teacher':
            response = api_response(
                code=403,
                message="您没有权限查看此信息",
                data=None
            )
            response.status_code = status.HTTP_403_FORBIDDEN
            return response
        
        # 获取课程对象
        course = get_object_or_404(Course, course_id=course_id)
            
        try:
            teacher = user.teacher_profile
            if not teacher or course.teacher != teacher:
                response = api_response(
                    code=403,
                    message="您没有权限查看此信息",
                    data=None
                )
                response.status_code = status.HTTP_403_FORBIDDEN
                return response
        except Exception:
            response = api_response(
                code=403,
                message="您没有权限查看此信息",
                data=None
            )
            response.status_code = status.HTTP_403_FORBIDDEN
            return response
        
        # 获取选修该课程的所有学生信息
        student_courses = StudentCourse.objects.filter(course=course).select_related(
            'student',
            'student__user',
            'student__class_id',
            'student__user__user_avatar',
            'student__user__user_background'  # 添加背景图关联
        )
        
        # 整理学生信息
        students_info = []
        for sc in student_courses:
            student = sc.student
            user = student.user
            class_info = student.class_id
            
            # 安全获取头像URL
            image_url = None
            try:
                if hasattr(user, 'user_avatar') and user.user_avatar and user.user_avatar.image:
                    image_url = request.build_absolute_uri(user.user_avatar.image.url)
            except Exception:
                image_url = None
                
            # 安全获取背景图URL
            background_url = None
            try:
                if hasattr(user, 'user_background') and user.user_background and user.user_background.image:
                    background_url = request.build_absolute_uri(user.user_background.image.url)
            except Exception:
                background_url = None
            
            student_info = {
                'student_id': f'S{student.student_id:06d}',  # 格式化为S开头的6位数字
                'username': user.username,  # 用户名字段
                'email': user.email,
                'phone': user.phone,
                'staff_id': user.staff_id,
                'avatar': image_url,  # 改名为avatar以便更清晰
                'background': background_url,  # 添加背景图字段
                'class_name': class_info.class_name if class_info else None,
                'class_system': class_info.class_system if class_info else None
            }
            students_info.append(student_info)
        
        response = api_response(
            code=200,
            message="获取成功",
            data={
                "total": len(students_info),
                "items": students_info
            }
        )
        response.status_code = status.HTTP_200_OK
        return response


class StartClassView(APIView):
    """
    开始上课API
    创建新的CourseTime记录，记录开始上课时间
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id):
        """创建新的课程时间记录，标记开始上课"""
        user = request.user
        
        # 检查用户是否为教师
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以开始上课",
                data=None
            )
        
        # 获取课程
        try:
            course = Course.objects.get(course_id=course_id)
        except Course.DoesNotExist:
            return api_response(
                code=404,
                message="课程不存在",
                data=None
            )
        
        # 检查是否为该课程的教师
        try:
            teacher = user.teacher_profile
            if course.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是该课程的授课教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息获取失败",
                data=None
            )
        
        # 检查是否有未结束的课程时间记录
        active_course_time = CourseTime.objects.filter(
            course=course,
            teacher=teacher,
            begin_time__isnull=False,
            end_time__isnull=True
        ).first()
        
        if active_course_time:
            # 如果有未结束的课程，返回该记录
            return api_response(
                code=200,
                message="您已有正在进行的课程",
                data={
                    "course_time_id": active_course_time.id,
                    "begin_time": active_course_time.begin_time,
                    "course_id": course.course_id,
                    "course_title": course.title
                }
            )
        
        # 创建新的课程时间记录
        now = timezone.now()
        course_time = CourseTime.objects.create(
            begin_time=now,
            course=course,
            teacher=teacher
        )
        
        return api_response(
            code=200,
            message="课程已成功开始",
            data={
                "course_time_id": course_time.id,
                "begin_time": course_time.begin_time,
                "course_id": course.course_id,
                "course_title": course.title
            }
        )


class EndClassView(APIView):
    """
    结束上课API
    更新CourseTime记录的结束时间
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_time_id):
        """更新课程时间记录，标记结束上课"""
        user = request.user
        
        # 检查用户是否为教师
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以结束上课",
                data=None
            )
        
        # 获取课程时间记录
        try:
            course_time = CourseTime.objects.get(id=course_time_id)
        except CourseTime.DoesNotExist:
            return api_response(
                code=404,
                message="课程时间记录不存在",
                data=None
            )
        
        # 检查是否为该课程的教师
        try:
            teacher = user.teacher_profile
            if course_time.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是该课程的授课教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息获取失败",
                data=None
            )
        
        # 检查课程是否已经结束
        if course_time.end_time is not None:
            return api_response(
                code=400,
                message="该课程已经结束",
                data=None
            )
        
        # 更新结束时间
        course_time.end_time = timezone.now()
        course_time.save()
        
        return api_response(
            code=200,
            message="课程已成功结束",
            data={
                "course_time_id": course_time.id,
                "begin_time": course_time.begin_time,
                "end_time": course_time.end_time,
                "duration": (course_time.end_time - course_time.begin_time).total_seconds() // 60,  # 以分钟为单位
                "course_id": course_time.course.course_id,
                "course_title": course_time.course.title
            }
        )


class UploadCourseRecordingView(APIView):
    """
    上传课程录像API
    将录像文件上传并关联到指定的CourseTime记录
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, course_time_id):
        """上传课程录像"""
        user = request.user
        
        # 检查用户是否为教师
        if user.role != 'teacher':
            return api_response(
                code=403,
                message="只有教师可以上传课程录像",
                data=None
            )
        
        # 获取课程时间记录
        try:
            course_time = CourseTime.objects.get(id=course_time_id)
        except CourseTime.DoesNotExist:
            return api_response(
                code=404,
                message="课程时间记录不存在",
                data=None
            )
        
        # 检查是否为该课程的教师
        try:
            teacher = user.teacher_profile
            if course_time.teacher != teacher:
                return api_response(
                    code=403,
                    message="您不是该课程的授课教师",
                    data=None
                )
        except:
            return api_response(
                code=403,
                message="教师信息获取失败",
                data=None
            )
        
        # 获取上传的文件
        recording_file = request.FILES.get('recording')
        if not recording_file:
            return api_response(
                code=400,
                message="未提供录像文件",
                data=None
            )
        
        # 保存录像文件
        course_time.recording_path = recording_file
        course_time.save()
        
        return api_response(
            code=200,
            message="课程录像上传成功",
            data={
                "course_time_id": course_time.id,
                "recording_path": course_time.recording_path.url if course_time.recording_path else None,
                "course_id": course_time.course.course_id,
                "course_title": course_time.course.title
            }
        )


class CourseTimesListView(APIView):
    """
    课程时间列表视图
    获取特定课程的所有课程时间记录
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, course_id):
        """获取课程的时间记录列表"""
        # 检查课程是否存在
        course = get_object_or_404(Course, course_id=course_id)
        
        # 检查用户权限（必须是课程的教师或学生）
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
                message="您没有权限访问此课程的时间记录",
                data=None
            )
        
        # 查询课程时间记录
        course_times = CourseTime.objects.filter(course=course).order_by('-begin_time')
        
        # 过滤条件：只显示有录像的记录
        only_with_recording = request.query_params.get('with_recording') == 'true'
        if only_with_recording:
            course_times = course_times.filter(
                Q(recording_path__isnull=False) & ~Q(recording_path='')
            )
        
        # 过滤条件：只显示有情绪分析的记录
        only_with_analysis = request.query_params.get('with_analysis') == 'true'
        if only_with_analysis:
            course_times = course_times.filter(
                Q(emotion_analysis_json__isnull=False) & ~Q(emotion_analysis_json={})
            )
        
        # 分页
        paginator = self.pagination_class()
        paginated_course_times = paginator.paginate_queryset(course_times, request)
        
        serializer = CourseTimeSerializer(
            paginated_course_times, 
            many=True,
            context={'request': request}
        )
        
        return api_response(
            code=200,
            message="获取成功",
            data={
                "total": paginator.page.paginator.count,
                "items": serializer.data
            }
        )


class RecordingDetailView(APIView):
    """
    录像详情视图
    获取特定课程时间的录像和情绪分析数据
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_time_id):
        """获取课程时间记录的录像和情绪分析数据"""
        # 查找课程时间记录
        course_time = get_object_or_404(CourseTime, id=course_time_id)
        
        # 检查用户权限（必须是课程的教师或学生）
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (course_time.teacher == teacher or course_time.course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=course_time.course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限访问此录像",
                data=None
            )
        
        # 检查是否有录像
        if not course_time.recording_path and not course_time.processed_recording_path:
            return api_response(
                code=404,
                message="此课程时间记录没有录像",
                data=None
            )
        
        serializer = RecordingSerializer(
            course_time,
            context={'request': request}
        )
        
        return api_response(
            code=200,
            message="获取成功",
            data=serializer.data
        )


class StreamRecordingView(APIView):
    """
    流式播放录像视图
    直接播放录像文件
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_time_id):
        """流式播放录像文件"""
        # 查找课程时间记录
        course_time = get_object_or_404(CourseTime, id=course_time_id)
        
        # 检查用户权限（必须是课程的教师或学生）
        user = request.user
        has_permission = False
        
        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                has_permission = (course_time.teacher == teacher or course_time.course.teacher == teacher)
            except:
                has_permission = False
        elif user.role == 'student':
            try:
                student = user.student_profile
                has_permission = StudentCourse.objects.filter(
                    student=student, course=course_time.course
                ).exists()
            except:
                has_permission = False
        
        if not has_permission:
            return api_response(
                code=403,
                message="您没有权限播放此录像",
                data=None
            )
        
        # 确定使用哪个录像文件
        recording_type = request.query_params.get('type', 'processed')
        
        if recording_type == 'processed' and course_time.processed_recording_path:
            recording_path = course_time.processed_recording_path.path
        elif course_time.recording_path:
            recording_path = course_time.recording_path.path
        else:
            return api_response(
                code=404,
                message="未找到录像文件",
                data=None
            )
        
        # 检查文件是否存在
        if not os.path.exists(recording_path):
            return api_response(
                code=404,
                message="录像文件不存在",
                data=None
            )
        
        # 获取文件大小
        file_size = os.path.getsize(recording_path)
        
        # 获取文件类型
        content_type, _ = mimetypes.guess_type(recording_path)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # 支持范围请求（用于视频播放）
        range_header = request.META.get('HTTP_RANGE', '').strip()
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        
        if range_match:
            start_byte = int(range_match.group(1))
            end_byte = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            end_byte = min(end_byte, file_size - 1)
            length = end_byte - start_byte + 1
            
            response = FileResponse(
                open(recording_path, 'rb'),
                status=206,
                content_type=content_type
            )
            
            response['Content-Length'] = str(length)
            response['Content-Range'] = f'bytes {start_byte}-{end_byte}/{file_size}'
            response.stream = True
            response.start_byte = start_byte
            
        else:
            # 完整文件请求
            response = FileResponse(
                open(recording_path, 'rb'),
                content_type=content_type
            )
            response['Content-Length'] = str(file_size)
            response.stream = True
        
        # 设置Content-Disposition为inline以便在浏览器中直接播放
        response['Content-Disposition'] = 'inline; filename="{}"'.format(
            os.path.basename(recording_path)
        )
        
        # 设置Accept-Ranges头，表示支持范围请求
        response['Accept-Ranges'] = 'bytes'
        
        return response
