from django.db import models
from django.utils import timezone

# Create your models here.

class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=45)
    description = models.CharField(max_length=45, blank=True, null=True)
    location = models.CharField(max_length=45, blank=True, null=True)
    system = models.CharField(max_length=45, blank=True, null=True)
    schedule = models.CharField(max_length=45, blank=True, null=True)
    semester = models.CharField(max_length=45, blank=True, null=True)
    teacher = models.ForeignKey('user_management.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    
    class Meta:
        app_label = 'course_management'

class CourseTime(models.Model):
    begin_time = models.DateTimeField(verbose_name='开始时间', blank=True, null=True)
    end_time = models.DateTimeField(verbose_name='结束时间', blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_times')
    teacher = models.ForeignKey('user_management.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='course_times')
    recording_path = models.FileField(upload_to='course_recordings/%Y/%m/%d/', verbose_name='课程录像', blank=True, null=True)
    processed_recording_path = models.FileField(upload_to='processed_recordings/%Y/%m/%d/', verbose_name='处理后的录像', blank=True, null=True)
    emotion_analysis_json = models.JSONField(verbose_name='情绪分析数据', blank=True, null=True)
    
    class Meta:
        app_label = 'course_management'
        verbose_name = '课程时间'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        course_title = self.course.title if self.course else "未知课程"
        begin = self.begin_time.strftime('%Y-%m-%d %H:%M') if self.begin_time else "未设置"
        end = self.end_time.strftime('%Y-%m-%d %H:%M') if self.end_time else "未设置"
        return f"{course_title}: {begin} - {end}"

class StudentCourse(models.Model):
    student = models.ForeignKey('user_management.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='student_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_courses')
    
    class Meta:
        app_label = 'course_management'

class ClassCourse(models.Model):
    class_id = models.ForeignKey('class_management.Class', on_delete=models.CASCADE, related_name='class_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='class_courses')
    
    class Meta:
        app_label = 'course_management'

class CourseResource(models.Model):
    name = models.CharField(max_length=255, verbose_name='资源名称')
    type = models.CharField(max_length=50, verbose_name='资源类型')
    description = models.TextField(blank=True, null=True, verbose_name='资源描述')
    file = models.FileField(upload_to='course_resources/', verbose_name='资源文件')
    size = models.CharField(max_length=20, verbose_name='文件大小')
    upload_time = models.DateTimeField(default=timezone.now, verbose_name='上传时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    download_count = models.IntegerField(default=0, verbose_name='下载次数')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources', verbose_name='所属课程')
    uploader = models.ForeignKey('user_management.User', on_delete=models.SET_NULL, null=True, related_name='uploaded_resources', verbose_name='上传者')

    class Meta:
        app_label = 'course_management'
        verbose_name = '课程资源'
        verbose_name_plural = verbose_name
        ordering = ['-upload_time']

    def __str__(self):
        return f"{self.name} ({self.type})"

class UserAvatar(models.Model):
    """用户头像模型"""
    user = models.OneToOneField('user_management.User', on_delete=models.CASCADE, related_name='user_avatar', verbose_name='用户')
    image = models.ImageField(upload_to='avatars/%Y/%m/', verbose_name='头像图片')
    upload_time = models.DateTimeField(default=timezone.now, verbose_name='上传时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        app_label = 'course_management'
        verbose_name = '用户头像'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username}的头像"

class UserBackground(models.Model):
    """用户背景图模型"""
    user = models.OneToOneField('user_management.User', on_delete=models.CASCADE, related_name='user_background', verbose_name='用户')
    image = models.ImageField(upload_to='backgrounds/%Y/%m/', verbose_name='背景图片')
    upload_time = models.DateTimeField(default=timezone.now, verbose_name='上传时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        app_label = 'course_management'
        verbose_name = '用户背景图'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username}的背景图"
