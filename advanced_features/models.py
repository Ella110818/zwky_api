from django.db import models
from django.utils import timezone
from course_management.models import Course
from user_management.models import User, Student
from decimal import Decimal

class CourseAnnouncement(models.Model):
    """课程公告模型"""
    TYPE_CHOICES = [
        ('info', '普通'),
        ('warning', '重要'),
        ('danger', '紧急'),
    ]
    
    title = models.CharField(max_length=100, verbose_name='公告标题')
    content = models.TextField(verbose_name='公告内容')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info', verbose_name='公告类型')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements', verbose_name='所属课程')
    publisher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='published_announcements', verbose_name='发布者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '课程公告'
        verbose_name_plural = '课程公告'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Assignment(models.Model):
    """作业和考试模型"""
    TYPE_CHOICES = [
        ('homework', '作业'),
        ('exam', '考试'),
    ]
    
    title = models.CharField(max_length=100, verbose_name='标题')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='homework', verbose_name='类型')
    description = models.TextField(verbose_name='描述')
    start_time = models.DateTimeField(verbose_name='开始时间')
    deadline = models.DateTimeField(verbose_name='截止时间')
    full_score = models.PositiveIntegerField(default=100, verbose_name='满分')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments', verbose_name='所属课程')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '作业与考试'
        verbose_name_plural = '作业与考试'
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.course.title} - {self.title} ({self.get_type_display()})"
    
    @property
    def status(self):
        now = timezone.now()
        if now < self.start_time:
            return '未开始'
        elif now <= self.deadline:
            return '进行中'
        else:
            return '已截止'

class AssignmentSubmission(models.Model):
    """作业提交模型"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name='作业')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignment_submissions', verbose_name='学生')
    file = models.FileField(upload_to='assignment_submissions/%Y/%m/', null=True, blank=True, verbose_name='提交文件')
    content = models.TextField(null=True, blank=True, verbose_name='提交内容')
    score = models.PositiveIntegerField(null=True, blank=True, verbose_name='得分')
    feedback = models.TextField(null=True, blank=True, verbose_name='教师反馈')
    submitted_at = models.DateTimeField(default=timezone.now, verbose_name='提交时间')
    
    class Meta:
        verbose_name = '作业提交'
        verbose_name_plural = '作业提交'
        unique_together = ['assignment', 'student']
    
    def __str__(self):
        return f"{self.student.user.username} - {self.assignment.title}"

class CourseGroup(models.Model):
    """课程分组模型"""
    name = models.CharField(max_length=50, verbose_name='分组名称')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='groups', verbose_name='所属课程')
    students = models.ManyToManyField(Student, related_name='groups', verbose_name='学生')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '课程分组'
        verbose_name_plural = '课程分组'
        unique_together = ['name', 'course']
    
    def __str__(self):
        return f"{self.course.title} - {self.name}" 

class GradeRecord(models.Model):
    """成绩记录模型"""
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE,
        related_name='grade_records',
        verbose_name='学生'
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE,
        related_name='grade_records',
        verbose_name='课程'
    )
    
    # 各类成绩
    class_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='课堂成绩'
    )
    homework_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='作业成绩'
    )
    exam_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='考试成绩'
    )
    
    # 添加学期字段以区分不同学期的成绩
    SEMESTER_CHOICES = [
        ('2023-2024-1', '2023-2024学年第一学期'),
        ('2023-2024-2', '2023-2024学年第二学期'),
        ('2024-2025-1', '2024-2025学年第一学期'),
        ('2024-2025-2', '2024-2025学年第二学期'),
    ]
    
    semester = models.CharField(
        max_length=50,
        choices=SEMESTER_CHOICES,
        verbose_name='学期',
        help_text='选择学期'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '成绩记录'
        verbose_name_plural = '成绩记录'
        ordering = ['student', 'course']
        # 添加学期到唯一约束，允许同一学生在同一课程不同学期有记录
        unique_together = ('student', 'course', 'semester')
    
    def __str__(self):
        return f"{self.student.user.username} - {self.course.title} - {self.semester}"
    
    @property
    def total_score(self):
        """
        计算总成绩：课堂成绩30%，作业成绩20%，考试成绩50%
        如果某项成绩未录入，则按0分计算
        """
        class_score = self.class_score or Decimal('0')
        homework_score = self.homework_score or Decimal('0')
        exam_score = self.exam_score or Decimal('0')
        
        total = class_score * Decimal('0.3') + homework_score * Decimal('0.2') + exam_score * Decimal('0.5')
        return round(total, 2)   