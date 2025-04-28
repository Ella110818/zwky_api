from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.contrib import messages
from .models import Student, Teacher

User = get_user_model()

class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name = '学生信息'
    verbose_name_plural = '学生信息'
    fk_name = 'user'

class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    verbose_name = '教师信息'
    verbose_name_plural = '教师信息'
    fk_name = 'user'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'role', 'staff_id', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('first_name', 'last_name', 'email', 'phone', 'role', 'avatar', 'staff_id')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined', 'create_time', 'update_time')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role'),
        }),
        ('个人信息', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('权限', {'fields': ('is_active', 'is_staff')}),
    )
    readonly_fields = ('create_time', 'update_time')
    search_fields = ('username', 'email', 'first_name', 'staff_id')
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.role == 'student':
                return [StudentInline]
            elif obj.role == 'teacher':
                return [TeacherInline]
        return []
    
    def save_model(self, request, obj, form, change):
        """保存用户时确保staff_id与角色关联"""
        # 如果是创建新用户，不要设置staff_id，让模型自动关联
        if not change:  # 这是新创建的用户
            obj.staff_id = None  # 确保staff_id为空
        
        # 调用父类方法保存用户
        super().save_model(request, obj, form, change)
        
        # 如果是新用户，创建对应的角色实例
        if not change:
            # 角色实例将在模型的save方法中自动创建
            pass

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'username_display', 'class_id', 'user')
    list_filter = ('class_id',)
    search_fields = ('user__username', 'user__staff_id', 'student_id')
    raw_id_fields = ('user', 'class_id')
    actions = ['safe_delete_students']
    
    def username_display(self, obj):
        return obj.username
    username_display.short_description = '用户名'
    
    def safe_delete_students(self, request, queryset):
        """安全删除学生，先处理外键关联"""
        try:
            with transaction.atomic():
                for student in queryset:
                    # 获取学生ID用于记录
                    student_id = student.student_id
                    student_name = student.username

                    # 设置关联记录的student为NULL
                    self.handle_related_records(student)

                    # 如果学生有关联用户，清除用户中的关联
                    if student.user:
                        user = student.user
                        user.staff_id = None
                        user.save(update_fields=['staff_id'])
                        # 解除用户和学生的关联
                        student.user = None
                        student.save()

                    # 然后删除学生
                    student.delete()
                    
                    # 添加操作成功消息
                    messages.success(request, f'成功删除学生: {student_name} (ID: {student_id})')
            
            messages.success(request, f'成功删除 {queryset.count()} 名学生')
        except Exception as e:
            messages.error(request, f'删除学生时出错: {str(e)}')
            
    safe_delete_students.short_description = "安全删除所选学生"
    
    def handle_related_records(self, student):
        """处理学生关联的所有记录"""
        try:
            # 导入相关模型
            from django.apps import apps
            
            # 获取所有相关模型
            StudentCourse = apps.get_model('course_management', 'StudentCourse')
            Status = apps.get_model('status_management', 'Status')
            try:
                # 直接清除该学生关联的数据，以避免外键约束错误
                StudentCourse.objects.filter(student=student).delete()
                Status.objects.filter(student=student).delete()
            except Exception as e:
                raise Exception(f"删除关联记录时出错: {str(e)}")
            
            # 查找并处理可能的其他关联
            for related_object in student._meta.related_objects:
                related_name = related_object.get_accessor_name()
                if hasattr(student, related_name):
                    related_manager = getattr(student, related_name)
                    # 如果是一对多关系
                    if hasattr(related_manager, 'all'):
                        for related_instance in related_manager.all():
                            try:
                                # 尝试删除关联实例
                                related_instance.delete()
                            except Exception:
                                # 如果删除失败，尝试设置为NULL
                                if hasattr(related_instance, 'student'):
                                    setattr(related_instance, 'student', None)
                                    related_instance.save()
        except Exception as e:
            raise Exception(f"处理关联记录时出错: {str(e)}")

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'username_display', 'teacher_title', 'user')
    search_fields = ('teacher_title', 'user__username', 'user__staff_id', 'teacher_id')
    raw_id_fields = ('user',)
    actions = ['safe_delete_teachers']
    
    def username_display(self, obj):
        return obj.username
    username_display.short_description = '用户名'
    
    def safe_delete_teachers(self, request, queryset):
        """安全删除教师，先处理外键关联"""
        try:
            with transaction.atomic():
                for teacher in queryset:
                    # 获取教师ID用于记录
                    teacher_id = teacher.teacher_id
                    teacher_name = teacher.username

                    # 导入相关模型
                    from django.apps import apps
                    TeacherClass = apps.get_model('class_management', 'TeacherClass')
                    CourseTime = apps.get_model('course_management', 'CourseTime')
                    Course = apps.get_model('course_management', 'Course')
                    
                    try:
                        # 处理TeacherClass关联 - 直接删除相关记录
                        TeacherClass.objects.filter(teacher=teacher).delete()
                        
                        # 处理CourseTime关联 - 直接删除相关记录
                        CourseTime.objects.filter(teacher=teacher).delete()
                        
                        # 处理Course关联 - 设置为NULL
                        Course.objects.filter(teacher=teacher).update(teacher=None)
                    except Exception as e:
                        messages.error(request, f'处理教师关联记录时出错: {str(e)}')
                        # 继续尝试其他操作，不要中断

                    # 如果教师有关联用户，清除用户中的关联
                    if teacher.user:
                        user = teacher.user
                        user.staff_id = None
                        user.save(update_fields=['staff_id'])
                        # 解除用户和教师的关联
                        teacher.user = None
                        teacher.save()

                    # 处理其他可能的关联
                    for related_object in teacher._meta.related_objects:
                        related_name = related_object.get_accessor_name()
                        if hasattr(teacher, related_name):
                            related_manager = getattr(teacher, related_name)
                            # 如果是一对多关系
                            if hasattr(related_manager, 'all'):
                                for related_instance in related_manager.all():
                                    try:
                                        # 尝试删除关联实例
                                        related_instance.delete()
                                    except Exception:
                                        # 如果删除失败，尝试设置为NULL
                                        if hasattr(related_instance, 'teacher'):
                                            setattr(related_instance, 'teacher', None)
                                            related_instance.save()

                    # 然后删除教师
                    teacher.delete()
                    
                    # 添加操作成功消息
                    messages.success(request, f'成功删除教师: {teacher_name} (ID: {teacher_id})')
            
            messages.success(request, f'成功删除 {queryset.count()} 名教师')
        except Exception as e:
            messages.error(request, f'删除教师时出错: {str(e)}')
            
    safe_delete_teachers.short_description = "安全删除所选教师"
