from django.db import models

# Create your models here.

class Class(models.Model):
    class_id = models.AutoField(primary_key=True)
    class_name = models.CharField(max_length=45)
    class_system = models.CharField(max_length=45)
    
    class Meta:
        app_label = 'class_management'
        verbose_name = '班级'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.class_name} ({self.class_system})"

class TeacherClass(models.Model):
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='teacher_classes')
    teacher = models.ForeignKey('user_management.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_classes')
    
    class Meta:
        app_label = 'class_management'
        verbose_name = '教师班级关联'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        teacher_name = self.teacher.username if self.teacher else "未知教师"
        class_name = self.class_id.class_name if self.class_id else "未知班级"
        return f"{teacher_name} - {class_name}"
