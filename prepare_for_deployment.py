from django.core.management.base import BaseCommand
from user_management.models import User, Student, Teacher
from course_management.models import Course, CourseTime, StudentCourse, ClassCourse
from class_management.models import Class, TeacherClass
from status_management.models import Status

class Command(BaseCommand):
    help = '填充种子数据'

    def handle(self, *args, **kwargs):
        # 创建一些班级
        class1 = Class.objects.create(class_name='Math 101', class_system='Mathematics')
        class2 = Class.objects.create(class_name='Science 102', class_system='Science')

        # 创建一些教师
        teacher1 = Teacher.objects.create(teacher_title='Professor')
        teacher2 = Teacher.objects.create(teacher_title='Lecturer')

        # 创建一些学生
        student1 = Student.objects.create(class_id=class1)
        student2 = Student.objects.create(class_id=class2)

        # 创建一些课程
        course1 = Course.objects.create(title='Algebra', teacher=teacher1)
        course2 = Course.objects.create(title='Physics', teacher=teacher2)

        # 创建一些课程时间
        coursetime1 = CourseTime.objects.create(course=course1, teacher=teacher1)
        coursetime2 = CourseTime.objects.create(course=course2, teacher=teacher2)

        # 创建一些状态
        Status.objects.create(concentrate=1, sleepy=0, low_head=0, half='No', puzzle=0, if_come=True, student=student1, course_time=coursetime1)
        Status.objects.create(concentrate=0, sleepy=1, low_head=1, half='Yes', puzzle=1, if_come=False, student=student2, course_time=coursetime2)

        self.stdout.write(self.style.SUCCESS('成功填充种子数据')) 