import cv2
import mediapipe as mp
import numpy as np
import time
import os
import json
from datetime import datetime
from collections import deque, defaultdict

# 初始化MediaPipe解决方案
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


class DataCollector:
    """负责收集和存储检测数据的类"""

    def __init__(self):
        self.status_history = deque(maxlen=100)  # 保存最近100条状态记录
        self.current_status = {
            'timestamp': None,
            'id':'000',
            'name': None,
            'main_status': None
        }

    def update_status(self, status_data):
        """更新当前状态并保存到历史记录"""
        self.current_status = status_data
        self.current_status['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.status_history.append(self.current_status.copy())

    def get_current_status(self):
        """获取当前状态"""
        return self.current_status

    def get_status_history(self, n=10):
        """获取最近n条状态历史"""
        return list(self.status_history)[-n:]


class StatusLogger:
    def __init__(self, log_dir="data/data_emotions"):
        os.makedirs(log_dir, exist_ok=True)
        start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = open(os.path.join(log_dir, f"face_status_{start_time}.txt"), "a")
        self.last_log_time = {}

    def log_status(self, status_data):
        """记录状态到日志文件，按人脸ID区分"""
        current_time = time.time()
        face_id = status_data.get('id', 'unknown')

        # 检查该人脸是否需要记录（每秒记录一次）
        if face_id not in self.last_log_time or \
                current_time - self.last_log_time[face_id] >= 1.0:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            log_entry = (f"{timestamp} - "
                         f"ID: {face_id} | "
                         f"Name: {status_data['name']} | "
                         f"Status: {status_data['main_status']}\n")

            self.log_file.write(log_entry)
            self.log_file.flush()
            self.last_log_time[face_id] = current_time

    def close(self):
        """关闭日志文件"""
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()


class Visualizer:
    """负责可视化显示的类"""

    def __init__(self):
        # 状态颜色映射
        self.status_colors = {
            "Head Down": (0, 0, 255),  # 红色
            "Turning LEFT": (255, 0, 0),  # 蓝色
            "Turning RIGHT": (255, 0, 0),  # 蓝色
            "Distracted": (0, 165, 255),  # 橙色
            "Confused": (255, 0, 255),  # 紫色
            "Focused": (0, 255, 0),  # 绿色
            "CALIBRATING": (255, 255, 0)  # 黄色
        }

    def draw_results(self, frame, status_data, turn_color, pose_color):
        """在帧上绘制检测结果"""
        h, w = frame.shape[:2]

        # 创建半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 180), (50, 50, 50), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # 获取状态颜色
        status_color = self.status_colors.get(status_data['main_status'], (0, 255, 0))

        # 显示当前状态
        cv2.putText(frame, f"Status: {status_data['main_status']}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

        # 显示详细检测信息
        cv2.putText(frame, f"Head Pose: {status_data['head_pose']}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, pose_color, 1)
        cv2.putText(frame, f"Head Turn: {status_data['head_turn']}", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, turn_color, 1)

        # 显示指标数据
        cv2.putText(frame, f"EAR: {status_data['metrics']['ear']:.3f}", (20, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Turn Ratio: {status_data['metrics']['head_turn_ratio']:.3f}", (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Vertical Ratio: {status_data['metrics']['vertical_ratio']:.3f}", (20, 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame


class MultiFaceDetector:
    def __init__(self):
        # 初始化模型
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 初始化各模块
        #self.data_collector = DataCollector()
        #self.logger = StatusLogger()
        self.visualizer = Visualizer()

        # 检测参数
        self.SMOOTHING_FACTOR = 0.2
        self.head_turn_ratio = 0
        self.turn_threshold = 0.30

        # 注意力检测参数
        self.LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
        self.DISTRACTION_THRESHOLD = 0.2
        self.DISTRACTION_TIME_THRESHOLD = 1
        self.distraction_timer = None
        self.distraction_state = False

        # 困惑检测参数
        self.CONFUSION_EYEBROW_THRESHOLD = 0.20
        self.CONFUSION_MOUTH_THRESHOLD = 0.05
        self.confusion_state = False

        # 头部姿势检测
        self.calibration_frames = 30
        self.frame_count = 0
        self.vertical_ratios = []
        self.baseline_ratio = 0
        self.calibrated = False

        # 关键点索引
        self.NOSE_TIP = 4
        self.FOREHEAD = 10
        self.CHIN = 152
        self.LEFT_EAR = 234
        self.RIGHT_EAR = 454
        self.LEFT_EYE = 33
        self.RIGHT_EYE = 263
        self.LEFT_EYEBROW = 65
        self.RIGHT_EYEBROW = 295
        self.UPPER_LIP = 13
        self.LOWER_LIP = 14

        # 初始化摄像头
        self.cap = cv2.VideoCapture(0)

    # def __del__(self):
    #     self.cleanup()

    def cleanup(self):
        """清理资源"""
        self.cap.release()
        cv2.destroyAllWindows()
        #self.logger.close()

    def calculate_ear(self, landmarks, eye_indices):
        """计算眼睛纵横比(EAR)"""
        vertical_dist1 = landmarks[eye_indices[1]].y - landmarks[eye_indices[5]].y
        vertical_dist2 = landmarks[eye_indices[2]].y - landmarks[eye_indices[4]].y
        horizontal_dist = landmarks[eye_indices[0]].x - landmarks[eye_indices[3]].x
        return (vertical_dist1 + vertical_dist2) / (2.0 * abs(horizontal_dist))

    def detect_head_turn(self, landmarks):
        """检测头部转向"""
        nose = landmarks[self.NOSE_TIP]
        left_ear = landmarks[self.LEFT_EAR]
        right_ear = landmarks[self.RIGHT_EAR]

        nose_to_left = abs(nose.x - left_ear.x)
        nose_to_right = abs(nose.x - right_ear.x)
        current_ratio = (nose_to_right - nose_to_left) / (nose_to_right + nose_to_left)

        # 平滑处理
        self.head_turn_ratio = (self.SMOOTHING_FACTOR * current_ratio +
                                (1 - self.SMOOTHING_FACTOR) * self.head_turn_ratio)

        # 判断转向状态
        if self.head_turn_ratio > self.turn_threshold:
            return "Turning LEFT", (0, 0, 255)
        elif self.head_turn_ratio < -self.turn_threshold:
            return "Turning RIGHT", (255, 0, 0)
        else:
            return "Forward", (0, 255, 0)

    def detect_distraction(self, landmarks):
        """检测注意力分散"""
        left_ear = self.calculate_ear(landmarks, self.LEFT_EYE_INDICES)
        right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE_INDICES)
        avg_ear = (left_ear + right_ear) / 2

        if avg_ear < self.DISTRACTION_THRESHOLD:
            if self.distraction_timer is None:
                self.distraction_timer = time.time()
            elif time.time() - self.distraction_timer >= self.DISTRACTION_TIME_THRESHOLD:
                self.distraction_state = True
        else:
            self.distraction_timer = None
            self.distraction_state = False

        return self.distraction_state, avg_ear

    def detect_confusion(self, landmarks, frame_shape):
        """检测困惑表情"""
        h, w = frame_shape[:2]

        # 计算相对距离
        def relative_distance(p1, p2):
            return np.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) / w

        left_eyebrow_eye = relative_distance(landmarks[self.LEFT_EYEBROW], landmarks[self.LEFT_EYE])
        right_eyebrow_eye = relative_distance(landmarks[self.RIGHT_EYEBROW], landmarks[self.RIGHT_EYE])
        mouth_open = relative_distance(landmarks[self.UPPER_LIP], landmarks[self.LOWER_LIP])

        self.confusion_state = (
                (left_eyebrow_eye > self.CONFUSION_EYEBROW_THRESHOLD or
                 right_eyebrow_eye > self.CONFUSION_EYEBROW_THRESHOLD) and
                mouth_open > self.CONFUSION_MOUTH_THRESHOLD
        )

        return self.confusion_state

    def detect_head_pose(self, landmarks, frame_shape):
        """检测头部姿势(低头/抬头)"""
        h, w = frame_shape[:2]

        chin_to_nose = abs(landmarks[self.CHIN].y - landmarks[self.NOSE_TIP].y) * h
        nose_to_forehead = abs(landmarks[self.NOSE_TIP].y - landmarks[self.FOREHEAD].y) * h

        if chin_to_nose > 0:
            vertical_ratio = nose_to_forehead / chin_to_nose

            # 校准阶段
            if not self.calibrated:
                self.frame_count += 1
                if self.frame_count <= self.calibration_frames:
                    self.vertical_ratios.append(vertical_ratio)
                    return "CALIBRATING", (255, 255, 0), vertical_ratio
                else:
                    self.baseline_ratio = np.mean(self.vertical_ratios)
                    self.calibrated = True
                    return "HEAD UP", (0, 255, 0), vertical_ratio
            else:
                # 检测阶段
                if vertical_ratio > self.baseline_ratio * 1.3:
                    return "HEAD DOWN", (0, 0, 255), vertical_ratio
                else:
                    return "HEAD UP", (0, 255, 0), vertical_ratio

        return "CALIBRATING", (255, 255, 0), 0

    def get_priority_status(self, pose_status, turn_status, distracted, confused):
        """确定最高优先级状态"""
        if pose_status == "HEAD DOWN":
            return "Head Down"
        elif "Turning" in turn_status:
            return turn_status
        elif distracted:
            return "Distracted"
        elif confused:
            return "Confused"
        else:
            return "Focused"

    def process_frame(self, frame):
        """处理单帧，返回处理后的帧和检测结果"""
        # 创建帧的副本用于绘制
        display_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # 准备检测变量
        pose_status = "Unknown"
        turn_status = "Forward"
        distracted = False
        confused = False
        metrics = {
            'ear': 0.0,
            'head_turn_ratio': 0.0,
            'vertical_ratio': 0.0
        }
        pose_color = (255, 255, 255)
        turn_color = (0, 255, 0)
        
        # 将BGR图像转换为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 运行人脸网格检测
        face_results = self.face_mesh.process(rgb_frame)
        
        # 初始化状态数据
        status_data = {
            'id': '000',
            'name': 'Unknown',
            'main_status': 'No Face Detected',
            'head_pose': 'Unknown',
            'head_turn': 'Forward',
            'metrics': metrics
        }
        
        # 如果检测到人脸
        if face_results.multi_face_landmarks:
            # 获取第一个人脸的关键点
            face_landmarks = face_results.multi_face_landmarks[0]
            landmarks = face_landmarks.landmark
            
            # 绘制人脸网格
            mp_drawing.draw_landmarks(
                display_frame,
                face_landmarks,
                mp_face_mesh.FACEMESH_CONTOURS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1),
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1)
            )
            
            # 头部转向检测
            turn_status, turn_color = self.detect_head_turn(landmarks)
            metrics['head_turn_ratio'] = self.head_turn_ratio
            
            # 头部姿势检测
            pose_status, pose_color, vertical_ratio = self.detect_head_pose(landmarks, frame.shape)
            metrics['vertical_ratio'] = vertical_ratio
            
            # 注意力检测
            distracted, ear_value = self.detect_distraction(landmarks)
            metrics['ear'] = ear_value
            
            # 困惑检测
            confused = self.detect_confusion(landmarks, frame.shape)
            
            # 获取优先级状态
            main_status = self.get_priority_status(pose_status, turn_status, distracted, confused)
            
            # 更新状态数据
            status_data.update({
                'main_status': main_status,
                'head_pose': pose_status,
                'head_turn': turn_status,
                'metrics': metrics
            })
        
        # 使用Visualizer绘制结果
        display_frame = self.visualizer.draw_results(display_frame, status_data, turn_color, pose_color)
        
        return display_frame, status_data

    def run(self):
        """主运行循环"""
        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    continue

                # 处理帧并获取状态
                frame, status_data = self.process_frame(frame)

                # 显示结果
                cv2.imshow('Face Status Detection', frame)

                # 按ESC退出
                if cv2.waitKey(5) & 0xFF == 27:
                    break
        finally:
            self.cleanup()


class StatisticsGenerator:
    """负责生成情绪分析统计数据的类"""
    
    def __init__(self, log_dir="data/data_emotions"):
        """初始化统计生成器"""
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
        self.status_records = defaultdict(lambda: defaultdict(int))
        self.student_data = defaultdict(int)
        
    def update_status(self, student_name, status):
        """更新指定学生的状态统计数据"""
        if status:
            self.status_records[student_name][status] += 1
            self.student_data[student_name] += 1
    
    def generate_statistics(self, output_file=None):
        """生成统计JSON文件"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.log_dir, f"face_status_{timestamp}_statistics.json")
        
        statistics = {"summary": {}}
        
        for student_name, status_counts in self.status_records.items():
            total_records = self.student_data[student_name]
            
            # 计算每种状态的百分比
            status_percentages = {}
            for status, count in status_counts.items():
                percentage = 0.0
                if total_records > 0:
                    percentage = round(count / total_records * 100, 2)
                status_percentages[status] = percentage
            
            # 添加学生的总结
            statistics["summary"][student_name] = {
                "total_records": total_records,
                "status_counts": dict(status_counts),
                "status_percentages": status_percentages
            }
        
        # 写入JSON文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False)
        
        return statistics, output_file


if __name__ == "__main__":
    detector = MultiFaceDetector()
    detector.run()