from django.contrib import admin
from .models import Class, TeacherClass

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('class_id', 'class_name', 'class_system')
    list_filter = ('class_system',)
    search_fields = ('class_name', 'class_system')

@admin.register(TeacherClass)
class TeacherClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'class_id', 'teacher')
    list_filter = ('class_id', 'teacher')
    search_fields = ('class_id__class_name', 'teacher__user__username')
