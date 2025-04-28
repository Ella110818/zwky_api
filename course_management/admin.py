from django.contrib import admin
from .models import Course, CourseTime, StudentCourse, ClassCourse, CourseResource, UserAvatar, UserBackground

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_id', 'title', 'teacher', 'location', 'system', 'semester']
    search_fields = ['title', 'description']
    list_filter = ['semester', 'system']

@admin.register(CourseTime)
class CourseTimeAdmin(admin.ModelAdmin):
    list_display = ['course', 'begin_time', 'end_time', 'teacher']
    list_filter = ['begin_time', 'end_time']
    search_fields = ['course__title']

@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ['student', 'course']
    search_fields = ['student__user__username', 'course__title']

@admin.register(ClassCourse)
class ClassCourseAdmin(admin.ModelAdmin):
    list_display = ['class_id', 'course']
    search_fields = ['class_id__name', 'course__title']

@admin.register(CourseResource)
class CourseResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'course', 'uploader', 'upload_time', 'download_count']
    list_filter = ['type', 'upload_time']
    search_fields = ['name', 'description', 'course__title']
    readonly_fields = ['download_count', 'upload_time']

@admin.register(UserAvatar)
class UserAvatarAdmin(admin.ModelAdmin):
    list_display = ['user', 'upload_time', 'update_time']
    search_fields = ['user__username']
    readonly_fields = ['upload_time', 'update_time']

@admin.register(UserBackground)
class UserBackgroundAdmin(admin.ModelAdmin):
    list_display = ['user', 'upload_time', 'update_time']
    search_fields = ['user__username']
    readonly_fields = ['upload_time', 'update_time']
