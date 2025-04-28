from rest_framework import serializers
from .models import Course, CourseResource, CourseTime

class CourseListSerializer(serializers.ModelSerializer):
    """
    课程列表序列化器
    用于课程列表展示，只包含课程的基本信息
    """
    class Meta:
        model = Course
        fields = ['course_id', 'title', 'teacher', 'description', 'location', 'system', 'schedule', 'semester']

class CourseDetailSerializer(serializers.ModelSerializer):
    """
    课程详情序列化器
    用于课程详细信息展示，包含课程的所有字段
    """
    class Meta:
        model = Course
        fields = '__all__'

class CourseResourceSerializer(serializers.ModelSerializer):
    """
    课程资源序列化器
    用于课程资源列表展示，包含资源的基本信息
    """
    class Meta:
        model = CourseResource
        fields = ['id', 'name', 'type', 'description', 'upload_time']

class CourseResourceDetailSerializer(serializers.ModelSerializer):
    """
    课程资源详情序列化器
    用于课程资源详细信息展示，包含资源的所有字段
    """
    class Meta:
        model = CourseResource
        fields = '__all__'

class CourseTimeSerializer(serializers.ModelSerializer):
    """
    课程时间序列化器
    用于课程时间信息展示，包括课程时间、相关课程信息和录制状态
    """
    # 从关联的课程模型中获取课程标题
    course_title = serializers.CharField(source='course.title', read_only=True)
    # 从关联的教师模型中获取教师用户名
    teacher_name = serializers.CharField(source='teacher.user.username', read_only=True)
    # 检查是否有录制文件的计算字段
    has_recording = serializers.SerializerMethodField()
    # 检查是否有处理过的录制文件的计算字段
    has_processed_recording = serializers.SerializerMethodField()
    # 检查是否有情感分析数据的计算字段
    has_emotion_analysis = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseTime
        fields = ['id', 'begin_time', 'end_time', 'course_id', 'course_title', 
                  'teacher_name', 'has_recording', 'has_processed_recording', 
                  'has_emotion_analysis']
    
    def get_has_recording(self, obj):
        """判断是否存在录制文件"""
        return bool(obj.recording_path)
    
    def get_has_processed_recording(self, obj):
        """判断是否存在处理过的录制文件"""
        return bool(obj.processed_recording_path)
    
    def get_has_emotion_analysis(self, obj):
        """判断是否存在情感分析数据"""
        return bool(obj.emotion_analysis_json)

class RecordingSerializer(serializers.ModelSerializer):
    """
    录制视频序列化器
    用于视频录制详情展示，包括视频URL和相关课程信息
    """
    # 从关联的课程模型中获取课程标题
    course_title = serializers.CharField(source='course.title', read_only=True)
    # 从关联的教师模型中获取教师用户名
    teacher_name = serializers.CharField(source='teacher.user.username', read_only=True)
    # 原始录制视频URL的计算字段
    recording_url = serializers.SerializerMethodField()
    # 处理后录制视频URL的计算字段
    processed_recording_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseTime
        fields = ['id', 'begin_time', 'end_time', 'course_id', 'course_title', 
                  'teacher_name', 'recording_url', 'processed_recording_url', 
                  'emotion_analysis_json']
    
    def get_recording_url(self, obj):
        """
        获取原始录制视频的完整URL
        如果存在请求上下文，则构建绝对URL
        """
        if obj.recording_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.recording_path.url)
            return obj.recording_path.url
        return None
    
    def get_processed_recording_url(self, obj):
        """
        获取处理后录制视频的完整URL
        如果存在请求上下文，则构建绝对URL
        """
        if obj.processed_recording_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.processed_recording_path.url)
            return obj.processed_recording_path.url
        return None 