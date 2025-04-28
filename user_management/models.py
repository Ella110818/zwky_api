from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """
    自定义用户模型
    """
    ROLE_CHOICES = (
        ('teacher', '教师'),
        ('student', '学生'),
    )
    
    email = models.EmailField(verbose_name='邮箱', blank=True, null=True, unique=False)
    phone = models.CharField(verbose_name='电话号码', max_length=20, blank=True, null=True)
    role = models.CharField(verbose_name='角色', max_length=10, choices=ROLE_CHOICES, default='student')
    avatar = models.URLField(verbose_name='头像URL', blank=True, null=True)
    create_time = models.DateTimeField(verbose_name='创建时间', default=timezone.now)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    staff_id = models.CharField(verbose_name='职工号', max_length=30, blank=True, null=True, unique=True)
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-date_joined']
        app_label = 'user_management'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def get_related_profile(self):
        """
        根据用户角色获取关联的学生或教师信息
        """
        if self.role == 'student':
            try:
                return self.student_profile
            except:
                return None
        elif self.role == 'teacher':
            try:
                return self.teacher_profile
            except:
                return None
        return None
    
    def save(self, *args, **kwargs):
        """
        保存用户时，确保职工号与角色一致
        """
        # 处理可能为空字符串的staff_id（在表单提交时可能发生）
        if self.staff_id == '':
            self.staff_id = None
            
        # 先保存用户获取ID
        super().save(*args, **kwargs)
        
        # 确保用户有对应的角色实例
        if self.role == 'student':
            try:
                student = self.student_profile
            except Student.DoesNotExist:
                # 创建新学生实例，使用用户ID作为学生ID
                student = Student(user=self)
                # 直接设置学生ID与用户ID相同
                student.student_id = self.id
                student.save()
                
                # 将学生ID同步回用户的staff_id
                if not self.staff_id:
                    self.staff_id = str(self.id)
                    # 使用update而不是save避免递归
                    User.objects.filter(pk=self.pk).update(staff_id=self.staff_id)
                    
        elif self.role == 'teacher':
            try:
                teacher = self.teacher_profile
            except Teacher.DoesNotExist:
                # 创建新教师实例，使用用户ID作为教师ID
                teacher = Teacher(user=self, teacher_title="未设置")
                # 直接设置教师ID与用户ID相同
                teacher.teacher_id = self.id
                teacher.save()
                
                # 将教师ID同步回用户的staff_id
                if not self.staff_id:
                    self.staff_id = str(self.id)
                    # 使用update而不是save避免递归
                    User.objects.filter(pk=self.pk).update(staff_id=self.staff_id)

class Student(models.Model):
    student_id = models.IntegerField(primary_key=True)  # 从AutoField更改为IntegerField
    class_id = models.ForeignKey('class_management.Class', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='student_profile', null=True, blank=True)
    
    class Meta:
        app_label = 'user_management'
        verbose_name = '学生'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - 学生ID: {self.student_id}"
        return f"学生ID: {self.student_id}"
    
    @property
    def username(self):
        """获取关联用户的用户名"""
        return self.user.username if self.user else "未关联用户"
    
    @property
    def staff_number(self):
        """获取关联用户的职工号"""
        return self.user.staff_id if self.user else None
    
    def save(self, *args, **kwargs):
        """保存学生信息时，确保ID设置正确"""
        # 如果是新创建的学生且有关联用户，使用用户ID
        if self.pk is None and self.user:
            self.student_id = self.user.id
        # 否则如果没有设置主键，自动生成
        elif self.pk is None:
            # 查找最大ID值并加1
            max_id = Student.objects.all().order_by('-student_id').first()
            self.student_id = (max_id.student_id + 1) if max_id else 1
            
        super().save(*args, **kwargs)
        
        # 如果有关联用户，同步staff_id
        if self.user and self.user.staff_id != str(self.student_id):
            User.objects.filter(pk=self.user.pk).update(staff_id=str(self.student_id))

class Teacher(models.Model):
    teacher_id = models.IntegerField(primary_key=True)  # 从AutoField更改为IntegerField
    teacher_title = models.CharField(max_length=45, verbose_name='职称')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='teacher_profile', null=True, blank=True)
    
    class Meta:
        app_label = 'user_management'
        verbose_name = '教师'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - 教师ID: {self.teacher_id}"
        return f"教师ID: {self.teacher_id}"
    
    @property
    def username(self):
        """获取关联用户的用户名"""
        return self.user.username if self.user else "未关联用户"
    
    @property
    def staff_number(self):
        """获取关联用户的职工号"""
        return self.user.staff_id if self.user else None
        
    def save(self, *args, **kwargs):
        """保存教师信息时，确保ID设置正确"""
        # 如果是新创建的教师且有关联用户，使用用户ID
        if self.pk is None and self.user:
            self.teacher_id = self.user.id
        # 否则如果没有设置主键，自动生成
        elif self.pk is None:
            # 查找最大ID值并加1
            max_id = Teacher.objects.all().order_by('-teacher_id').first()
            self.teacher_id = (max_id.teacher_id + 1) if max_id else 1
            
        super().save(*args, **kwargs)
        
        # 如果有关联用户，同步staff_id
        if self.user and self.user.staff_id != str(self.teacher_id):
            User.objects.filter(pk=self.user.pk).update(staff_id=str(self.teacher_id))
