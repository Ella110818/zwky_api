from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Student, Teacher

User = get_user_model()

# 由于在User.save()方法中已经添加了创建相关角色实例的逻辑
# 以下信号处理函数仅作为备份，确保系统兼容性
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """
    确保用户有对应的角色模型
    注意：这个函数是User.save方法的补充，以确保系统健壮性
    """
    # 大部分逻辑已经移动到User.save方法中
    # 这里只做最基本的检查
    if instance.role == 'student' and not hasattr(instance, 'student_profile'):
        Student.objects.get_or_create(user=instance)
    elif instance.role == 'teacher' and not hasattr(instance, 'teacher_profile'):
        Teacher.objects.get_or_create(user=instance, defaults={'teacher_title': "未设置"})

# 添加删除信号处理，当删除Student或Teacher时，不要级联删除用户
@receiver(pre_delete, sender=Student)
def handle_student_delete(sender, instance, **kwargs):
    """当删除学生实例时，清除关联用户的staff_id"""
    if instance.user:
        user = instance.user
        user.staff_id = None  # 清除职工号
        user.save(update_fields=['staff_id'])

@receiver(pre_delete, sender=Teacher)
def handle_teacher_delete(sender, instance, **kwargs):
    """当删除教师实例时，清除关联用户的staff_id"""
    if instance.user:
        user = instance.user
        user.staff_id = None  # 清除职工号
        user.save(update_fields=['staff_id']) 