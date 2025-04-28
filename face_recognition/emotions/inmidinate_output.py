from PIL import Image, ImageDraw, ImageFont
from .dbmodule import *
import cv2
import numpy as np
import os
from datetime import datetime
import time
import json
from collections import defaultdict
from insightface.app import FaceAnalysis
from .emotions import *

# 检测人脸 (app 变量将在Django初始化时设置)
app = FaceAnalysis(name="buffalo_sc", providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# 创建全局变量用于Django集成
data_collector = DataCollector()
logger = StatusLogger()  # 使用新的 StatusLogger
face_detector = MultiFaceDetector()  # 创建MultiFaceDetector实例

class StatusAnalyzer:
    """状态分析器，用于分析日志文件并生成统计数据"""
    
    @staticmethod
    def analyze_log_file(log_file_path):
        """分析单个日志文件并生成统计数据"""
        stats = defaultdict(lambda: defaultdict(int))
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if not lines:
                print(f"警告：日志文件 {log_file_path} 为空")
                
            for line in lines:
                try:
                    # 先打印日志内容以便调试
                    print(f"解析日志行: {line.strip()}")
                    
                    # 检查行内容是否符合预期
                    if ' | ' not in line:
                        print(f"警告：日志行格式不正确: {line.strip()}")
                        continue
                    
                    parts = line.strip().split(' | ')
                    if len(parts) < 3:
                        print(f"警告：日志行部分数量不足: {line.strip()}")
                        continue
                    
                    # 尝试解析姓名和状态
                    name_part = parts[1]
                    status_part = parts[2]
                    
                    if ': ' not in name_part or ': ' not in status_part:
                        print(f"警告：姓名或状态格式不正确: {line.strip()}")
                        continue
                    
                    name = name_part.split(': ')[1]
                    status = status_part.split(': ')[1]
                    
                    # 忽略未知人脸的记录
                    if name == "unknown":
                        continue
                    
                    stats[name][status] += 1
                    stats[name]['Total'] += 1
                    
                except Exception as e:
                    print(f"解析行时出错: {line.strip()}, 错误: {str(e)}")
                    continue
            
            # 如果没有有效记录，添加一个默认记录
            if not stats:
                print("没有找到有效的状态记录，将添加默认记录")
                stats["未检测到人脸"]["No Face Detected"] = 1
                stats["未检测到人脸"]["Total"] = 1
        except Exception as e:
            print(f"分析日志文件时出错: {str(e)}")
            # 添加一个默认记录
            stats["错误"]["Error"] = 1
            stats["错误"]["Total"] = 1
        
        status_columns = ['Distracted', 'Focused', 'Confused', 'Head Down', 
                         'Turning LEFT', 'Turning RIGHT', 'No Face Detected', 'Error', 'Total']
        
        json_data = {
            'summary': {
                name: {
                    'total_records': stats[name]['Total'],
                    'status_counts': {
                        status: stats[name][status]
                        for status in status_columns if status != 'Total' and stats[name][status] > 0
                    },
                    'status_percentages': {
                        status: round(stats[name][status] / stats[name]['Total'] * 100, 2)
                        for status in status_columns if status != 'Total' and stats[name][status] > 0 and stats[name]['Total'] > 0
                    }
                }
                for name in stats
            }
        }
        
        return json_data

    @staticmethod
    def analyze_latest_log(log_dir=None):
        """只分析最新的日志文件"""
        # 显式导入必要的模块，确保在函数内部可以访问
        import os
        
        if log_dir is None:
            from django.conf import settings
            log_dir = os.path.join(settings.MEDIA_ROOT, 'emotion_analysis')
        
        if not os.path.exists(log_dir):
            print(f"错误：目录不存在: {log_dir}")
            return
        
        log_files = [f for f in os.listdir(log_dir) 
                    if f.startswith('face_status_') and f.endswith('.txt')]
        
        if not log_files:
            print("未找到日志文件")
            return
        
        # 按文件名排序（文件名包含时间戳，所以最后一个是最新的）
        latest_log = sorted(log_files)[-1]
        log_file_path = os.path.join(log_dir, latest_log)
        print(f"\n处理最新日志文件: {latest_log}")
        
        json_data = StatusAnalyzer.analyze_log_file(log_file_path)
        
        base_name = os.path.splitext(latest_log)[0]
        json_file = os.path.join(log_dir, f"{base_name}_statistics.json")
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"统计结果已保存到: {json_file}")
        return json_file

    @staticmethod
    def analyze_all_logs(log_dir="data/data_emotions"):
        """分析指定目录下的所有日志文件"""
        # 显式导入必要的模块，确保在函数内部可以访问
        import os
        
        if not os.path.exists(log_dir):
            print(f"错误：目录不存在: {log_dir}")
            return
        
        log_files = [f for f in os.listdir(log_dir) 
                    if f.startswith('face_status_') and f.endswith('.txt')]
        
        if not log_files:
            print("未找到日志文件")
            return
        
        for log_file in sorted(log_files):
            log_file_path = os.path.join(log_dir, log_file)
            print(f"\n处理文件: {log_file}")
            
            json_data = StatusAnalyzer.analyze_log_file(log_file_path)
            
            base_name = os.path.splitext(log_file)[0]
            json_file = os.path.join(log_dir, f"{base_name}_statistics.json")
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"统计结果已保存到: {json_file}")

# 自定义 StatusLogger 类，确保 UTF-8 编码
class StatusLogger:
    def __init__(self, log_dir=None):
        # 显式导入必要的模块，确保在函数内部可以访问
        import os
        
        if log_dir is None:
            from django.conf import settings
            log_dir = os.path.join(settings.MEDIA_ROOT, 'emotion_analysis')
            
        os.makedirs(log_dir, exist_ok=True)
        start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = open(os.path.join(log_dir, f"face_status_{start_time}.txt"), "a", encoding='utf-8')
        self.last_log_time = {}

    def log_status(self, status_data):
        """记录状态到日志文件，按人脸ID区分"""
        try:
            # 验证状态数据是否有效
            if not status_data:
                print("警告：状态数据为空，不记录日志")
                return
                
            if 'main_status' not in status_data or not status_data['main_status']:
                print("警告：状态数据缺少main_status字段，不记录日志")
                return
                
            if 'name' not in status_data:
                print("警告：状态数据缺少name字段，不记录日志")
                status_data['name'] = 'unknown'
                
            # 确保日志文件已打开
            if not hasattr(self, 'log_file') or self.log_file is None or self.log_file.closed:
                print("警告：日志文件未打开或已关闭")
                # 尝试创建默认日志文件
                try:
                    import os
                    from django.conf import settings
                    log_dir = os.path.join(settings.MEDIA_ROOT, 'emotion_analysis')
                    os.makedirs(log_dir, exist_ok=True)
                    start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.log_file = open(os.path.join(log_dir, f"face_status_{start_time}.txt"), "a", encoding='utf-8')
                    print(f"已创建新的日志文件: {self.log_file.name}")
                except Exception as e:
                    print(f"无法创建日志文件: {str(e)}")
                    return
            
            # 清理名称，确保没有特殊字符
            status_data['name'] = status_data['name'].replace('|', '_').strip()
                
            current_time = time.time()
            face_id = status_data.get('id', 'unknown')

            # 检查该人脸是否需要记录（每秒记录一次）
            # 移除时间限制，确保每次调用都记录
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            log_entry = (f"{timestamp} - "
                         f"ID: {face_id} | "
                         f"Name: {status_data['name']} | "
                         f"Status: {status_data['main_status']}\n")

            print(f"记录日志: {log_entry.strip()}")  # 调试输出
            self.log_file.write(log_entry)
            self.log_file.flush()  # 立即写入文件
            self.last_log_time[face_id] = current_time
        except Exception as e:
            print(f"记录状态日志时出错: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印详细的堆栈跟踪

    def close(self):
        """关闭日志文件"""
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()

def process_frame(frame, target_feats, target_names, student_name, similarity_threshold=0.40):
    """
    处理视频帧，检测人脸并实时输出匹配结果。

    参数:
        frame (np.ndarray): 视频帧（单张图像）。
        target_feats (list): 目标人脸特征向量列表。
        target_names (list): 目标人脸名字列表。
        student_name (set): 用于收集识别到的学生名称的集合。
        similarity_threshold (float): 相似度阈值，默认 0.40 (降低阈值以提高匹配概率)。

    返回:
        frame (np.ndarray): 绘制了人脸框和标签的视频帧。
    """

    # 如果 frame 为 None，直接返回原帧
    if frame is None:
        print("警告：frame 为 None")
        return frame

    # 检测人脸
    try:
        # 检查帧的大小和质量
        if frame.size == 0:
            print("警告：空的视频帧")
            return frame

        # 先尝试调整帧大小以提高检测率
        h, w = frame.shape[:2]
        if max(w, h) > 1200:
            scale = 1200 / max(w, h)
            frame_for_detection = cv2.resize(frame, (int(w * scale), int(h * scale)))
        else:
            frame_for_detection = frame.copy()

        # 检测人脸
        faces = app.get(frame_for_detection)
        
        # 在原始帧上绘制标记
        if not faces:
            print("未检测到人脸")
            # 在帧上添加提示文字
            cv2.putText(frame, "No Face Detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # 在日志中添加一个默认记录，确保有统计数据
            status_data = {
                'id': 0,
                'name': '未识别',
                'main_status': 'No Face Detected'
            }
            logger.log_status(status_data)
            
            return frame  # 如果没有检测到人脸，直接返回原帧

        # 输出检测到的人脸数量
        num_faces = len(faces)
        print(f"检测到 {num_faces} 张人脸")

        # 检查目标特征是否为空
        if len(target_feats) == 0 or len(target_names) == 0:
            print("警告：目标特征为空，无法进行匹配")
            # 在帧上添加提示文字
            cv2.putText(frame, "No target features", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # 强制添加默认人脸，确保有日志
            status_data = {
                'id': 0,
                'name': '数据库为空',  # 这个名称会被记录
                'main_status': 'No Target Features'
            }
            logger.log_status(status_data)
            student_name.add('数据库为空')
            
            # 仍然继续处理，但不进行匹配
            target_feats = []
            target_names = []
        
        # 提取检测到的人脸特征向量
        feats = np.array([face.normed_embedding for face in faces], dtype=np.float32)

        # 初始化匹配标志
        matched = False

        # 将 OpenCV 图像转换为 PIL 图像
        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(frame_pil)

        # 加载中文字体
        font_path = os.path.join(os.path.dirname(__file__), "simsun.ttc")  # 替换为你的中文字体文件路径
        # 如果字体文件不存在，使用默认字体
        if not os.path.exists(font_path):
            # 尝试使用系统字体
            try:
                font = ImageFont.truetype("simhei.ttf", 12)  # 尝试使用黑体
            except:
                try:
                    font = ImageFont.truetype("kaiti.ttf", 12)  # 尝试使用楷体
                except:
                    font = ImageFont.load_default()  # 最后使用默认字体
        else:
            font = ImageFont.truetype(font_path, 12)  # 字体大小

        # 遍历所有检测到的人脸
        for i, face in enumerate(faces):
            try:
                # 获取人脸框坐标
                bbox = face.bbox.astype(np.int64)  # 人脸框坐标
                
                # 确保边界在图像范围内
                h, w = frame.shape[:2]
                x1 = max(0, int(bbox[0]))
                y1 = max(0, int(bbox[1]))
                x2 = min(w, int(bbox[2]))
                y2 = min(h, int(bbox[3]))
                
                # 如果裁剪区域无效，跳过此人脸
                if x1 >= x2 or y1 >= y2 or x2 <= 0 or y2 <= 0:
                    print(f"警告：人脸{i}裁剪区域无效: [{x1}, {y1}, {x2}, {y2}]")
                    continue
                
                # 从bbox裁剪人脸区域
                try:
                    aframe = frame[y1:y2, x1:x2].copy()
                    if aframe.size == 0:
                        print(f"警告：人脸{i}裁剪区域为空")
                        continue
                    
                    # 使用MultiFaceDetector处理人脸区域
                    _, status_emotions = face_detector.process_frame(aframe)
                    
                    if not status_emotions or 'main_status' not in status_emotions:
                        print(f"警告：人脸{i}情绪状态无效")
                        status_emotions = {'main_status': 'Unknown'}
                except Exception as e:
                    print(f"处理人脸{i}区域时出错: {str(e)}")
                    status_emotions = {'main_status': 'Error'}
                
                # 初始化匹配信息
                match_found = False
                target_name = "unknown"
                max_similarity = 0.40  # 降低初始阈值
                
                # 如果有目标特征，进行对比
                if len(target_feats) > 0:
                    # 对比当前人脸与目标人脸特征向量
                    for j, target_feat in enumerate(target_feats):
                        sim = np.dot(feats[i], target_feat)  # 计算相似度
                        print(f"人脸{i}与目标{j}({target_names[j]})的相似度: {sim:.4f}")
                        if sim > max_similarity:
                            max_similarity = sim
                            if max_similarity > similarity_threshold:
                                match_found = True
                                target_name = target_names[j]
                                matched = True  # 标记为找到匹配项
                
                # 检测到存在于数据库中的人脸，即阈值大于similarity_threshold的人脸
                if match_found:
                    student_name.add(target_name)
                    print(f"匹配到学生: {target_name}, 相似度: {max_similarity:.4f}")
                    
                # 设置标签
                label = f"{target_name} ({max_similarity:.2f}) {status_emotions['main_status']}" if match_found else f"unknown {status_emotions['main_status']}"
                status_data = {
                    'id': i,
                    'name': target_name,
                    'main_status': status_emotions['main_status']
                }
                
                # 更新数据收集器
                data_collector.update_status(status_data)
                
                # 强制记录日志 - 即使是未知人脸也记录
                if status_data['name'] == 'unknown':
                    # 使用特殊名称记录未知人脸，确保生成统计数据
                    status_data['name'] = '未知人脸'
                    student_name.add('未知人脸')
                
                # 强制将每个处理过的人脸写入日志，不管之前是否记录过
                print(f"强制记录人脸{i}的日志 - 名称:{status_data['name']}, 状态:{status_data['main_status']}")
                try:
                    logger.log_status(status_data)
                except Exception as e:
                    print(f"记录人脸{i}日志失败: {str(e)}")
                    # 尝试直接写入日志
                    try:
                        if hasattr(logger, 'log_file') and logger.log_file and not logger.log_file.closed:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            log_entry = (f"{timestamp} - "
                                        f"ID: {i} | "
                                        f"Name: {status_data['name']} | "
                                        f"Status: {status_data['main_status']}\n")
                            logger.log_file.write(log_entry)
                            logger.log_file.flush()
                            print(f"直接写入日志成功: {log_entry.strip()}")
                    except Exception as nested_e:
                        print(f"直接写入日志也失败: {str(nested_e)}")
                    
                # 绘制人脸框
                frame = app.draw_on(frame, [face])
        
                # 在人脸框上方添加名字和相似度
                draw.text(
                    (bbox[0], bbox[1] - 40),  # 文字位置
                    label,  # 名字和相似度
                    font=font,  # 字体
                    fill=(0, 255, 0) if match_found else (255, 0, 0)  # 颜色 (绿色匹配，红色未知)
                )
            except Exception as e:
                print(f"处理人脸{i}时出错: {str(e)}")
                continue

        # 将 PIL 图像转换回 OpenCV 图像
        frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

    except Exception as e:
        print(f"处理视频帧时出错: {str(e)}")
        # 在帧上添加错误信息
        cv2.putText(frame, f"Error: {str(e)}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    return frame

def showFace(frame):
    # 检测人脸
    faces = app.get(frame)
    
    # 使用从参数传入的方式，避免直接调用
    # 在实际使用时，应该从调用者那里获取target_feats和target_names
    from django.conf import settings
    import os
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    target_feats, target_names = load_target_feats_from_db(db_path)
    
    aset = set()
    frame = process_frame(frame, target_feats, target_names, aset)
    
    # 绘制人脸框
    for i, face in enumerate(faces):
        # 获取人脸框坐标
        bbox = face.bbox.astype(np.int64)  # 人脸框坐标
        frame = app.draw_on(frame, [face])

    return frame

# 示例：实时处理视频流
if __name__ == '__main__':
    # 加载目标人脸特征向量
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'db.sqlite3')
    target_feats, target_names = load_target_feats_from_db(db_path)

    # 打开摄像头
    cap = cv2.VideoCapture(0)  # 0 表示默认摄像头
    if not cap.isOpened():
        print("无法打开摄像头")
        exit()

    try:
        while True:
            # 读取视频帧
            ret, frame = cap.read()
            if not ret:
                print("无法读取视频帧")
                break

            # 处理视频帧
            result_frame = showFace(frame)

            # 显示结果
            if result_frame is None or not isinstance(result_frame, np.ndarray):
                print("Error: result_frame is not a valid image.")
            else:
                cv2.imshow("Face Recognition", result_frame)

            # 按下 'q' 键退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        logger.close()  # 确保日志文件被正确关闭
        
        # 只分析最新的日志文件
        print("\n开始分析最新日志文件...")
        StatusAnalyzer.analyze_latest_log()