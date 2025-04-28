from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import os
import json
import tempfile
import re
import numpy as np
import cv2
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import datetime
from django.conf import settings
from .models import Face
from user_management.utils import api_response  # 导入api_response工具函数
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
import time
from collections import defaultdict, Counter
from .emotions.emotions import MultiFaceDetector, StatisticsGenerator
from .emotions.inmidinate_output import process_frame, StatusLogger, StatusAnalyzer

# Create your views here.

# 人脸分析器将在 apps.py 的 ready() 方法中初始化
app = None

# 检查是否是测试请求
def is_test_request(request):
    # 检查URL参数
    if request.GET.get('test_mode') == 'true' or request.GET.get('test') == '1' or request.GET.get('no_auth') == '1':
        return True
    
    # 检查表单数据
    if request.POST.get('test_mode') == 'true' or request.POST.get('skip_auth') == 'true':
        return True
    
    # 检查文件上传中的表单数据
    if request.data and isinstance(request.data, dict):
        if request.data.get('test_mode') == 'true' or request.data.get('skip_auth') == 'true':
            return True
    
    # 检查请求头
    if request.headers.get('X-Test-Mode') == 'true':
        return True
    
    return False

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # 测试模式下不使用认证
@permission_classes([])      # 测试模式下不需要权限
def insert_face(request):
    """插入单个人脸"""
    if request.method != 'POST':
        return api_response(
            code=400,
            message="只支持POST请求",
            data=None
        )
    
    if 'image' not in request.FILES:
        return api_response(
            code=400,
            message="未提供图像文件",
            data=None
        )
        
    image_file = request.FILES['image']
    filename = image_file.name
    
    # 解析文件名获取人名和ID
    name_id = os.path.splitext(filename)[0]  # 移除扩展名
    match = re.search(r'(.+)_(\d+)', name_id)
    if match:
        name = match.group(1)
        face_id = int(match.group(2))
    else:
        name = name_id
        face_id = 1

    # 测试模式或insightface未初始化
    if app is None:
        # 返回模拟成功响应
        return api_response(
            code=200, 
            message=f"测试模式：成功添加{name}的人脸", 
            data={
                "id": face_id,
                "name": name
            }
        )
    
    # 真实模式
    try:
        # 读取图像数据
        img_data = image_file.read()
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 检测人脸
        faces = app.get(img)
        
        if len(faces) == 0:
            return api_response(
                code=400,
                message="未检测到人脸",
                data=None
            )
        
        if len(faces) > 1:
            return api_response(
                code=400,
                message=f"检测到多个人脸({len(faces)}个)，请提供单人照片",
                data=None
            )
        
        # 获取人脸特征
        face = faces[0]
        feat = face.normed_embedding
        
        # 保存到数据库
        face_obj, created = Face.objects.update_or_create(
            id=face_id,
            defaults={
                'name': name,
                'feat': feat.tobytes()
            }
        )
        
        return api_response(
            code=200,
            message=f"成功{'添加' if created else '更新'}{name}的人脸",
            data={
                "id": face_id,
                "name": name,
                "created": created
            }
        )
        
    except Exception as e:
        return api_response(
            code=500,
            message=f"处理人脸失败: {str(e)}",
            data=None
        )

@csrf_exempt
@api_view(['POST'])
def batch_insert_faces(request):
    """批量插入人脸"""
    if request.method != 'POST':
        return api_response(
            code=400,
            message="只支持POST请求",
            data=None
        )
    
    # 测试模式或insightface未初始化
    if app is None:
        # 返回模拟成功响应
        return api_response(
            code=200,
            message="测试模式：批量插入人脸功能暂未实现",
            data={
                "success": [],
                "failed": []
            }
        )
    
    # 真实模式实现批量插入（可根据实际需求扩展）
    # ...

    return api_response(
        code=501,
        message="批量插入人脸功能尚未实现",
        data=None
    )

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # 测试模式下不使用认证
@permission_classes([])      # 测试模式下不需要权限
def check_attendance(request):
    """检查考勤"""
    if request.method != 'POST':
        return api_response(
            code=400,
            message="只支持POST请求",
            data=None
        )
    
    if 'image' not in request.FILES:
        return api_response(
            code=400,
            message="未提供图像文件",
            data=None
        )
    
    # 获取图片文件名
    image_file = request.FILES['image']
    file_name = os.path.splitext(image_file.name)[0]
    
    # 测试模式或insightface未初始化
    if app is None:
        # 创建模拟考勤记录
        attendance_records = [
            {'id': 1, 'name': '张三', 'present': 1, 'confidence': 0.85},
            {'id': 2, 'name': '李四', 'present': 0, 'confidence': 0.45},
            {'id': 3, 'name': '王五', 'present': 1, 'confidence': 0.92}
        ]
        
        # 使用当前时间作为考勤文件名
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"attendance_{current_time}.txt"
        
        # 创建文件内容
        file_content = ""
        for record in attendance_records:
            file_content += f"{record['id']} {record['name']} {record['present']}\n"
        
        # 确保目录存在
        attendance_dir = os.path.join(settings.MEDIA_ROOT, 'attendance_records')
        os.makedirs(attendance_dir, exist_ok=True)
        
        # 将文件存储到默认存储位置
        path = default_storage.save(f'attendance_records/{filename}', ContentFile(file_content.encode('utf-8')))
        
        # 统计出席和缺席人数
        present_count = sum(1 for record in attendance_records if record['present'] == 1)
        absent_count = len(attendance_records) - present_count
        
        return api_response(
            code=200,
            message=f"测试模式：已生成考勤记录，出席人数：{present_count}，缺席人数：{absent_count}",
            data={
                "file_path": path,
                "attendance_records": attendance_records,
                "stats": {
                    "total": len(attendance_records),
                    "present": present_count,
                    "absent": absent_count
                }
            }
        )
    
    # 真实模式
    try:
        # 读取图像数据
        img_data = image_file.read()
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 检测人脸
        faces = app.get(img)
        
        if len(faces) == 0:
            return api_response(
                code=400,
                message="未检测到人脸",
                data=None
            )
        
        # 获取所有已知人脸
        known_faces = Face.objects.all()
        if not known_faces:
            return api_response(
                code=404,
                message="数据库中没有已知人脸数据",
                data=None
            )
        
        # 构建人脸特征矩阵
        known_feats = []
        for face_obj in known_faces:
            feat = np.frombuffer(face_obj.feat, dtype=np.float32)
            known_feats.append(feat)
        
        known_feats = np.array(known_feats)
        
        # 创建考勤记录
        attendance_records = []
        recognized_faces = []
        
        for face in faces:
            feat = face.normed_embedding
            
            # 计算相似度
            sim = np.dot(known_feats, feat)
            best_idx = np.argmax(sim)
            best_sim = sim[best_idx]
            
            # 阈值判断
            threshold = 0.5  # 可根据需要调整
            if best_sim > threshold:
                # 识别成功
                face_obj = known_faces[int(best_idx)]  # 将numpy的int64转换为Python的int
                attendance_records.append({
                    'id': face_obj.id,
                    'name': face_obj.name,
                    'present': 1,
                    'confidence': float(best_sim)
                })
                recognized_faces.append(face_obj)
            else:
                # 未能识别的人脸
                attendance_records.append({
                    'id': -1,
                    'name': "未知",
                    'present': 0,
                    'confidence': float(best_sim)
                })
        
        # 使用当前时间作为考勤文件名
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"attendance_{current_time}.txt"
        
        # 创建文件内容
        file_content = ""
        for record in attendance_records:
            file_content += f"{record['id']} {record['name']} {record['present']}\n"
        
        # 确保目录存在
        attendance_dir = os.path.join(settings.MEDIA_ROOT, 'attendance_records')
        os.makedirs(attendance_dir, exist_ok=True)
        
        # 将文件存储到默认存储位置
        path = default_storage.save(f'attendance_records/{filename}', ContentFile(file_content.encode('utf-8')))
        
        # 统计出席和缺席人数
        present_count = sum(1 for record in attendance_records if record['present'] == 1)
        absent_count = len(attendance_records) - present_count
        
        return api_response(
            code=200,
            message=f"已生成考勤记录，检测到{len(faces)}个人脸，识别出{present_count}人",
            data={
                "file_path": path,
                "attendance_records": attendance_records,
                "stats": {
                    "total": len(attendance_records),
                    "present": present_count,
                    "absent": absent_count
                }
            }
        )
        
    except Exception as e:
        return api_response(
            code=500,
            message=f"处理失败: {str(e)}",
            data=None
        )

@csrf_exempt
@api_view(['GET'])
def download_attendance_file(request):
    """下载考勤记录文件"""
    if request.method != 'GET':
        return api_response(
            code=400,
            message="只支持GET请求",
            data=None
        )
    
    # 获取指定文件名
    filename = request.GET.get('filename', '')
    
    if not filename:
        return api_response(
            code=400,
            message="未指定文件名",
            data=None
        )
    
    file_path = f'attendance_records/{filename}'
    
    try:
        # 检查文件是否存在
        if default_storage.exists(file_path):
            # 读取文件内容
            file_content = default_storage.open(file_path).read()
            
            # 创建响应
            response = HttpResponse(file_content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return api_response(
                code=404,
                message="文件不存在",
                data=None
            )
    except Exception as e:
        return api_response(
            code=500,
            message=f"下载失败: {str(e)}",
            data=None
        )

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # 测试模式下不使用认证
@permission_classes([])      # 测试模式下不需要权限
def process_video_emotions(request):
    """处理视频文件并生成情绪分析结果"""
    if request.method != 'POST':
        return api_response(
            code=400,
            message="只支持POST请求",
            data=None
        )
    
    if 'video' not in request.FILES:
        return api_response(
            code=400,
            message="未提供视频文件",
            data=None
        )
    
    # 获取视频文件
    video_file = request.FILES['video']
    
    # 获取学生姓名参数（可选）
    student_name = request.POST.get('name', '未知学生')
    
    # 获取学生ID（可选）
    student_id = request.POST.get('id', '000')
    
    # 创建临时文件保存上传的视频
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
        for chunk in video_file.chunks():
            temp_video.write(chunk)
        temp_video_path = temp_video.name
    
    try:
        # 确保输出目录存在
        output_dir = os.path.join(settings.MEDIA_ROOT, 'emotion_analysis')
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名（基于时间戳）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_video_name = f"video_analysis_{timestamp}.webm"
        output_video_path = os.path.join(output_dir, output_video_name)
        
        stats_file_name = f"face_status_{timestamp}_statistics.json"
        stats_file_path = os.path.join(output_dir, stats_file_name)
        
        log_file_name = f"face_status_{timestamp}.txt"
        log_file_path = os.path.join(output_dir, log_file_name)
        
        # 初始化视频捕获
        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")
        
        # 获取视频属性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 初始化视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'VP90')  # 使用VP9编码器，适用于webm格式
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        
        # 初始化情绪检测器
        detector = MultiFaceDetector()
        
        # 初始化统计生成器
        stats_generator = StatisticsGenerator(log_dir=output_dir)
        
        # 初始化日志文件
        with open(log_file_path, "w") as log_file:
            # 处理每一帧
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 处理当前帧
                processed_frame, status_data = detector.process_frame(frame)
                
                # 如果检测到人脸，更新统计信息
                if status_data and 'main_status' in status_data:
                    # 设置学生信息
                    status_data['id'] = student_id
                    status_data['name'] = student_name
                    
                    # 记录日志
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    log_entry = (f"{timestamp} - "
                                f"ID: {student_id} | "
                                f"Name: {student_name} | "
                                f"Status: {status_data['main_status']}\n")
                    log_file.write(log_entry)
                    
                    # 更新统计信息
                    stats_generator.update_status(student_name, status_data['main_status'])
                
                # 在帧上添加学生姓名
                cv2.putText(processed_frame, f"Student: {student_name}", 
                            (20, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.7, (255, 255, 255), 2)
                
                # 写入输出视频
                out.write(processed_frame)
        
        # 释放资源
        cap.release()
        out.release()
        
        # 生成统计数据
        statistics, _ = stats_generator.generate_statistics(stats_file_path)
        
        # 创建相对URL路径
        video_url = f'/media/emotion_analysis/{output_video_name}'
        stats_url = f'/media/emotion_analysis/{stats_file_name}'
        log_url = f'/media/emotion_analysis/{log_file_name}'
        
        return api_response(
            code=200,
            message="视频情绪分析完成",
            data={
                "video_url": video_url,
                "statistics_url": stats_url,
                "log_url": log_url,
                "summary": statistics
            }
        )
        
    except Exception as e:
        return api_response(
            code=500,
            message=f"处理视频失败: {str(e)}",
            data=None
        )
    finally:
        # 清理临时文件
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # 测试模式下不使用认证
@permission_classes([])      # 测试模式下不需要权限
def process_emotion_recognition(request):
    """处理视频文件，使用数据库中的人脸特征进行情绪识别，并输出带有人脸识别框的视频"""
    if request.method != 'POST':
        return api_response(
            code=400,
            message="只支持POST请求",
            data=None
        )
    
    if 'video' not in request.FILES:
        return api_response(
            code=400,
            message="未提供视频文件",
            data=None
        )
    
    # 获取视频文件
    video_file = request.FILES['video']
    
    # 获取课程时间ID（如果提供）
    course_time_id = request.POST.get('course_time_id')
    print(f"接收到的course_time_id: {course_time_id}, 类型: {type(course_time_id)}")
    course_time = None
    if course_time_id:
        try:
            # 尝试将course_time_id转换为整数
            course_time_id = int(course_time_id)
            # 导入CourseTime模型
            from course_management.models import CourseTime
            course_time = CourseTime.objects.filter(id=course_time_id).first()
            print(f"查询结果: {course_time}")
            
            if not course_time:
                print(f"未找到ID为{course_time_id}的课程时间记录")
                return api_response(
                    code=404,
                    message=f"未找到ID为{course_time_id}的课程时间记录",
                    data=None
                )
        except ValueError:
            print(f"course_time_id格式不正确: {course_time_id}")
        except Exception as e:
            print(f"获取课程时间记录时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 创建临时文件保存上传的视频
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
        for chunk in video_file.chunks():
            temp_video.write(chunk)
        temp_video_path = temp_video.name
    
    try:
        # 确保输出目录存在
        output_dir = os.path.join(settings.MEDIA_ROOT, 'emotion_analysis')
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名（基于时间戳）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_video_name = f"emotion_recognition_{timestamp}.webm"
        output_video_path = os.path.join(output_dir, output_video_name)
        
        # 创建日志文件路径
        log_file_name = f"face_status_{timestamp}.txt"
        stats_file_name = f"face_status_{timestamp}_statistics.json"
        log_file_path = os.path.join(output_dir, log_file_name)
        stats_file_path = os.path.join(output_dir, stats_file_name)
        
        # 初始化状态记录器 - 使用全局logger而不是创建新实例
        # 先关闭全局logger打开的旧文件
        from .emotions.inmidinate_output import logger
        if hasattr(logger, 'log_file') and logger.log_file:
            logger.log_file.close()
        
        # 给全局logger分配新的日志文件
        logger.log_file = open(log_file_path, "a", encoding='utf-8')
        logger.last_log_time = {}
        print(f"日志文件将保存到: {log_file_path}")
        
        # 初始化数据收集器
        data_collector = defaultdict(lambda: {'status_count': defaultdict(int), 'total': 0})
        
        # 从数据库获取人脸特征
        from .emotions.dbmodule import load_target_feats_from_db
        
        # 获取数据库路径
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        
        # 获取人脸特征向量
        target_feats, target_names = load_target_feats_from_db(db_path)
        print(f"从数据库获取到 {len(target_feats)} 个人脸特征")
        if len(target_feats) == 0:
            print("警告：数据库中没有人脸特征！")
        else:
            print(f"人脸姓名列表: {target_names}")
        
        # 初始化视频捕获
        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")
        
        # 获取视频属性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 初始化视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'VP90')  # 使用VP9编码器，适用于webm格式
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        
        # 记录检测到的学生集合
        student_names = set()
        frame_count = 0
        
        # 处理每一帧
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 每2帧处理一次（之前是5帧，降低跳帧率，提高检测机会）
            if frame_count % 2 == 0:
                # 处理当前帧，进行人脸识别和情绪检测
                processed_frame = process_frame(frame, target_feats, target_names, student_names)
                
                # 写入处理后的帧
                out.write(processed_frame)
                
                # 打印进度
                if frame_count % 50 == 0:
                    progress = (frame_count / total_frames) * 100
                    print(f"处理进度: {progress:.2f}%")
            else:
                # 非处理帧也需要写入到输出视频
                out.write(frame)
            
            frame_count += 1
        
        # 如果没有检测到任何学生，添加一个模拟记录以便生成统计数据
        if not student_names and os.path.exists(log_file_path) and os.path.getsize(log_file_path) == 0:
            print("未检测到任何学生，添加模拟记录...")
            with open(log_file_path, 'w', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"{timestamp} - ID: 0 | Name: 未识别 | Status: No Face Detected\n")
                student_names.add("未识别")
        
        # 释放资源
        cap.release()
        out.release()
        
        # 确保日志文件被关闭并刷新缓冲区
        logger.close()
        
        # 手动添加默认记录以防万一
        if os.path.exists(log_file_path) and os.path.getsize(log_file_path) == 0:
            print(f"警告：日志文件 {log_file_path} 为空，添加模拟记录...")
            with open(log_file_path, 'w', encoding='utf-8') as f:
                timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for student in student_names:
                    f.write(f"{timestamp_str} - ID: 0 | Name: {student} | Status: Detected\n")
                
                # 如果没有检测到任何学生，添加一个默认学生
                if not student_names:
                    f.write(f"{timestamp_str} - ID: 0 | Name: 未识别 | Status: No Face Detected\n")
                    student_names.add("未识别")
        
        # 直接分析指定的日志文件，而不是查找最新的
        json_data = StatusAnalyzer.analyze_log_file(log_file_path)
        
        # 保存统计数据到文件
        with open(stats_file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        print(f"统计结果已保存到: {stats_file_path}")
        
        # 读取分析结果
        statistics = json_data
        
        # 创建相对URL路径
        video_url = f'/media/emotion_analysis/{output_video_name}'
        stats_url = f'/media/emotion_analysis/{stats_file_name}'
        log_url = f'/media/emotion_analysis/{log_file_name}'
        
        # 如果存在有效的课程时间记录，保存处理后的记录
        if course_time:
            try:
                # 将处理后的视频保存到课程时间记录
                from django.core.files.base import File
                
                # 打开处理后的视频文件
                with open(output_video_path, 'rb') as f:
                    # 保存到processed_recording_path字段
                    course_time.processed_recording_path.save(
                        os.path.basename(output_video_path), 
                        File(f),
                        save=True
                    )
                
                # 保存JSON数据到emotion_analysis_json字段
                course_time.emotion_analysis_json = json_data
                course_time.save()
                
                print(f"成功将处理后的视频和JSON数据保存到课程时间记录 {course_time_id}, 记录ID: {course_time.id}, 处理后的视频路径: {course_time.processed_recording_path.path if course_time.processed_recording_path else '未设置'}")
            except Exception as e:
                print(f"保存到课程时间记录时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("没有有效的课程时间记录，无法保存处理结果")
        
        # 检查是否识别到了学生
        if not student_names:
            message = "视频处理完成，但未识别到任何学生"
        else:
            message = f"视频情绪识别分析完成，识别到 {len(student_names)} 名学生"
            
        # 如果更新了课程时间记录，添加到消息中
        if course_time:
            message += f"，并已更新课程时间记录 #{course_time_id}"
        
        return api_response(
            code=200,
            message=message,
            data={
                "video_url": video_url,
                "statistics_url": stats_url,
                "log_url": log_url,
                "identified_students": list(student_names),
                "summary": statistics,
                "course_time_id": course_time_id if course_time else None
            }
        )
        
    except Exception as e:
        return api_response(
            code=500,
            message=f"处理视频失败: {str(e)}",
            data=None
        )
    finally:
        # 清理临时文件
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
