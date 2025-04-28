from django.contrib import admin
from .models import Face

# Register your models here.
@admin.register(Face)
class FaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
