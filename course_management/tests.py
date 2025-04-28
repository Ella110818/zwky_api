from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from user_management.models import Teacher, Student
from class_management.models import Class
from .models import Course, StudentCourse

class CourseStudentInfoViewTests(APITestCase):
    def setUp(self):
        """测试数据初始化"""
        # 创建用户模型
        User = get_user_model()
        
        # 创建教师用户
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            email='teacher1@test.com',
            phone='13800138001',
            role='teacher',
            staff_id='T2023001'
        )
        # 获取自动创建的Teacher对象
        self.teacher = Teacher.objects.get(user=self.teacher_user)
        # 更新教师职称
        self.teacher.teacher_title = '教授'
        self.teacher.save()
        
        # 创建班级
        self.class_obj = Class.objects.create(
            class_name='测试班级1',
            class_system='本科'
        )
        
        # 创建学生用户
        self.student_user1 = User.objects.create_user(
            username='student1',
            password='testpass123',
            email='student1@test.com',
            phone='13800138002',
            role='student',
            staff_id='ST2023001'
        )
        self.student_user2 = User.objects.create_user(
            username='student2',
            password='testpass123',
            email='student2@test.com',
            phone='13800138003',
            role='student',
            staff_id='ST2023002'
        )
        
        # 获取自动创建的Student对象
        self.student1 = Student.objects.get(user=self.student_user1)
        self.student2 = Student.objects.get(user=self.student_user2)
        
        # 更新学生班级
        self.student1.class_id = self.class_obj
        self.student2.class_id = self.class_obj
        self.student1.save()
        self.student2.save()
        
        # 创建课程
        self.course = Course.objects.create(
            title='测试课程',
            description='测试课程描述',
            teacher=self.teacher
        )
        
        # 创建选课记录
        StudentCourse.objects.create(student=self.student1, course=self.course)
        StudentCourse.objects.create(student=self.student2, course=self.course)
        
        # 创建测试客户端
        self.client = APIClient()
    
    def test_get_course_students_info_as_teacher(self):
        """测试教师获取课程学生信息"""
        # 教师登录
        self.client.force_authenticate(user=self.teacher_user)
        
        # 构建 URL
        url = reverse('course-student-info', kwargs={'course_id': self.course.course_id})
        
        # 发送请求
        response = self.client.get(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], '获取成功')
        self.assertEqual(response.data['data']['total'], 2)
        
        # 验证返回的学生信息
        students = response.data['data']['items']
        self.assertEqual(len(students), 2)
        
        # 获取第一个学生的信息（通过email匹配）
        student1_info = next(s for s in students if s['email'] == 'student1@test.com')
        self.assertEqual(student1_info['phone'], '13800138002')
        self.assertEqual(student1_info['staff_id'], '2')  # 使用实际的staff_id
        self.assertEqual(student1_info['class_name'], '测试班级1')
        self.assertEqual(student1_info['class_system'], '本科')
    
    def test_get_course_students_info_as_student(self):
        """测试学生无权限获取课程学生信息"""
        # 学生登录
        self.client.force_authenticate(user=self.student_user1)
        
        # 构建 URL
        url = reverse('course-student-info', kwargs={'course_id': self.course.course_id})
        
        # 发送请求
        response = self.client.get(url)
        
        # 验证响应（应该被拒绝）
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['code'], 403)
        self.assertEqual(response.data['message'], '您没有权限查看此信息')
    
    def test_get_course_students_info_unauthorized(self):
        """测试未登录用户无权限获取课程学生信息"""
        # 构建 URL
        url = reverse('course-student-info', kwargs={'course_id': self.course.course_id})
        
        # 发送请求（未登录）
        response = self.client.get(url)
        
        # 验证响应（应该要求认证）
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_course_students_info_nonexistent_course(self):
        """测试获取不存在的课程学生信息"""
        # 教师登录
        self.client.force_authenticate(user=self.teacher_user)
        
        # 构建 URL（使用不存在的课程ID）
        url = reverse('course-student-info', kwargs={'course_id': 9999})
        
        # 发送请求
        response = self.client.get(url)
        
        # 验证响应（应该返回404）
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
