from django.contrib import admin
from .models import Status

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course_time', 'concentrate', 'sleepy', 'low_head', 'if_come')
    list_filter = ('student', 'course_time', 'if_come')
    search_fields = ('student__user__username', 'course_time__course__title')
