from django.contrib import admin
from .models import CourseAnnouncement, Assignment, AssignmentSubmission, GradeRecord,CourseGroup

@admin.register(CourseAnnouncement)
class CourseAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'type', 'publisher', 'created_at')
    list_filter = ('type', 'course')
    search_fields = ('title', 'content')
    date_hierarchy = 'created_at'

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'type', 'start_time', 'deadline', 'status')
    list_filter = ('type', 'course')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_time'

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'score', 'submitted_at')
    list_filter = ('assignment',)
    search_fields = ('student__user__username', 'feedback')
    date_hierarchy = 'submitted_at'

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'student_count', 'created_at')
    list_filter = ('course',)
    search_fields = ('name',)
    date_hierarchy = 'created_at'
    
    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = '学生数量' 

@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'semester', 'class_score', 'homework_score', 'exam_score', 'total_score')
    list_filter = ('course', 'semester')
    search_fields = ('student__user__username', 'course__title', 'semester')
    date_hierarchy = 'created_at'