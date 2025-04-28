from django.db import models

# Create your models here.

class Status(models.Model):
    concentrate = models.IntegerField(default=0)
    sleepy = models.IntegerField(default=0)
    low_head = models.IntegerField(default=0)
    half = models.IntegerField(default=0)
    puzzle = models.IntegerField(default=0)
    if_come = models.BooleanField(default=False)
    student = models.ForeignKey('user_management.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='statuses')
    course_time = models.ForeignKey('course_management.CourseTime', on_delete=models.SET_NULL, null=True, blank=True, related_name='statuses')
    
    class Meta:
        app_label = 'status_management'
        verbose_name = '课堂状态'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        student_name = self.student.username if self.student else "未知学生"
        course_name = self.course_time.course.title if self.course_time and self.course_time.course else "未知课程"
        return f"{student_name} - {course_name} 状态"
