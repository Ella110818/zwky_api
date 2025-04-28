import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque
from scipy.spatial import distance

class EyeAnalyzer:
    def __init__(self):
        # 初始化MediaPipe面部网格
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 关键点索引
        self.LEFT_IRIS = [468, 469, 470, 471, 472]  # 左眼球关键点
        self.RIGHT_IRIS = [473, 474, 475, 476, 477]  # 右眼球关键点
        self.LEFT_EYE_INNER = 468  # 左眼内角
        self.RIGHT_EYE_INNER = 473  # 右眼内角

        # 初始化变量
        self.prev_left_pos = None
        self.prev_right_pos = None
        self.prev_time = None
        self.speed_history = deque(maxlen=10)  # 用于平滑速度值

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)

        # 定义关键点索引
        self.LEFT_EYE_UPPER_LID = [386, 385, 384, 398, 387, 388, 466]  # 左上眼睑
        self.LEFT_EYE_LOWER_LID = [374, 373, 390, 249, 380, 381, 382]  # 左下眼睑
        self.RIGHT_EYE_UPPER_LID = [159, 158, 157, 173, 160, 161, 246]  # 右上眼睑
        self.RIGHT_EYE_LOWER_LID = [145, 144, 153, 7, 163, 154, 155]  # 右下眼睑

        # 初始化变量
        self.baseline_values_yanlian = deque(maxlen=30)  # 存储基准值的队列
        self.baseline_established_yanlian = False
        self.calibration_frames_yanlian = 30  # 校准帧数改为30帧
        self.frame_count_yanlian = 0  # 帧计数器
        self.baseline_yanlian = 0

        # 定义关键点索引
        self.LEFT_EYE_TOP = 386  # 左眼上眼睑中点
        self.LEFT_EYE_BOTTOM = 374  # 左眼下眼睑中点
        self.RIGHT_EYE_TOP = 159  # 右眼上眼睑中点
        self.RIGHT_EYE_BOTTOM = 145  # 右眼下眼睑中点

        # 初始化变量
        self.baseline_values_yankuang = deque(maxlen=30)  # 存储基准值的队列
        self.baseline_established_yankuang = False
        self.calibration_frames_yankuang = 30  # 30帧校准
        self.frame_count_yankuang = 0  # 帧计数器
        self.baseline_ratio = 0  # 基准比例
        self.eye_state_history = deque(maxlen=5)  # 状态历史用于消抖

        # 状态常量
        self.STATE_OPEN = 0
        self.STATE_SQUINT = 1
        self.STATE_BLINK = 2

        # 眼睛关键点索引（MediaPipe的468点模型）
        self.LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
        self.EAR_THRESHOLD = 0.21  # 需要根据实际情况调整
        self.blink_count = 0
        self.blink_flag = False

        # 用于计算每分钟眨眼频率的变量
        self.start_time = time.time()
        self.blinks_per_minute = 0

    def calculate_ear(self,eye_points):
        """
        计算眼睛纵横比(Eye Aspect Ratio, EAR)
        :param eye_points: 眼睛的6个关键点坐标
        :return: EAR值
        """
        # 计算垂直距离
        A = distance.euclidean(eye_points[1], eye_points[5])
        B = distance.euclidean(eye_points[2], eye_points[4])

        # 计算水平距离
        C = distance.euclidean(eye_points[0], eye_points[3])

        # 计算EAR
        ear = (A + B) / (2.0 * C)
        return ear

    def analyze_frame(self, frame):
        """分析嘴部行为（基于基准值的比例）"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        output = {
            "Eye Speed": 0,
            "shangyanlian Ratio": 0,
            "yankuang Ratio": 0,
            "Blinks/min": 0,
            "landmarks": None
        }

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            h, w = frame.shape[:2]
            output["landmarks"] = landmarks

            # 获取眼睛关键点坐标
            left_eye_points = [(landmarks.landmark[i].x, landmarks.landmark[i].y) for i in self.LEFT_EYE_INDICES]
            right_eye_points = [(landmarks.landmark[i].x, landmarks.landmark[i].y) for i in self.RIGHT_EYE_INDICES]

            # 计算EAR
            left_ear = self.calculate_ear(left_eye_points)
            right_ear = self.calculate_ear(right_eye_points)
            avg_ear = (left_ear + right_ear) / 2.0

            # 检测眨眼

            if avg_ear < self.EAR_THRESHOLD and not self.blink_flag:
                self.blink_count += 1
                self.blink_flag = True
            elif avg_ear >= self.EAR_THRESHOLD and self.blink_flag:
                self.blink_flag = False
            # 计算当前时间
            current_time = time.time()
            elapsed_time = current_time - self.start_time

            # 计算每分钟眨眼次数
            if elapsed_time > 0:
                self.blinks_per_minute = (self.blink_count / elapsed_time) * 60
            else:
                self.blinks_per_minute = 0
            output['Blinks/min']=self.blinks_per_minute

            for face_landmarks in results.multi_face_landmarks:
                # 获取关键点坐标
                landmarks = []
                h, w, _ = frame.shape
                for landmark in face_landmarks.landmark:
                    landmarks.append((int(landmark.x * w), int(landmark.y * h)))

                # 计算归一化基准距离(两眼内角距离)
                ref_distance = np.linalg.norm(
                    np.array(landmarks[self.LEFT_EYE_INNER]) -
                    np.array(landmarks[self.RIGHT_EYE_INNER])
                )

                # 计算当前时间
                current_time = time.time()

                # 计算左眼球中心(使用多个关键点平均位置)
                left_iris_center = np.mean([landmarks[i] for i in self.LEFT_IRIS], axis=0)
                right_iris_center = np.mean([landmarks[i] for i in self.RIGHT_IRIS], axis=0)

                # 计算眼球移动速度(如果是第一帧则跳过)
                if self.prev_left_pos is not None and self.prev_time is not None:
                    time_diff = current_time - self.prev_time

                    if time_diff > 0:
                        # 计算像素位移
                        left_displacement = np.linalg.norm(left_iris_center - self.prev_left_pos)
                        right_displacement = np.linalg.norm(right_iris_center - self.prev_right_pos)

                        # 计算归一化速度(单位: 基准距离/秒)
                        left_speed = (left_displacement / ref_distance) / time_diff
                        right_speed = (right_displacement / ref_distance) / time_diff

                        # 平均两眼速度
                        avg_speed = (left_speed + right_speed) / 2

                        # 添加到历史记录用于平滑
                        self.speed_history.append(avg_speed)

                        # 计算平滑后的速度(移动平均)
                        smooth_speed = np.mean(self.speed_history) if self.speed_history else 0
                        output['Eye Speed']=smooth_speed
                # 更新前一帧信息
                self.prev_left_pos = left_iris_center
                self.prev_right_pos = right_iris_center
                self.prev_time = current_time

                # 计算眼睑高度
                def calculate_eye_height(upper_indices, lower_indices):
                    upper = np.mean([landmarks[i] for i in upper_indices], axis=0)
                    lower = np.mean([landmarks[i] for i in lower_indices], axis=0)
                    return np.linalg.norm(upper - lower) / ref_distance

                left_height = calculate_eye_height(self.LEFT_EYE_UPPER_LID, self.LEFT_EYE_LOWER_LID)
                right_height = calculate_eye_height(self.RIGHT_EYE_UPPER_LID, self.RIGHT_EYE_LOWER_LID)
                avg_height = (left_height + right_height) / 2
                # 基准值校准阶段(基于帧数而非时间)
                if not self.baseline_established_yanlian:
                    self.frame_count_yanlian += 1  # 增加帧计数器

                    if self.frame_count_yanlian <= self.calibration_frames_yanlian:
                        self.baseline_values_yanlian.append(avg_height)
                    else:
                        self.baseline_established_yanlian = True
                        self.baseline_yanlian = np.mean(self.baseline_values_yanlian) if self.baseline_values_yanlian else 0.15

                # 正常检测阶段
                if self.baseline_established_yanlian:
                    # 计算相对于基准值的比例
                    ratio = avg_height / self.baseline_yanlian
                    output["shangyanlian Ratio"] = ratio

                # 计算双眼高度并归一化
                def get_eye_height(top_idx, bottom_idx):
                    return np.linalg.norm(
                        np.array(landmarks[top_idx]) -
                        np.array(landmarks[bottom_idx])
                    ) / ref_distance

                left_eye_height = get_eye_height(self.LEFT_EYE_TOP, self.LEFT_EYE_BOTTOM)
                right_eye_height = get_eye_height(self.RIGHT_EYE_TOP, self.RIGHT_EYE_BOTTOM)
                avg_eye_height = (left_eye_height + right_eye_height) / 2

                # 基准值校准阶段(30帧)
                if not self.baseline_established_yankuang:
                    self.frame_count_yankuang += 1

                    if self.frame_count_yankuang <= self.calibration_frames_yankuang:
                        self.baseline_values_yankuang.append(avg_eye_height)
                    else:
                        self.baseline_established_yankuang = True
                        self.baseline_ratio = np.mean(self.baseline_values_yankuang) if self.baseline_values_yankuang else 0.2
                # 正常检测阶段
                if self.baseline_established_yankuang:
                    # 计算当前高度与基准值的比例
                    current_ratio = avg_eye_height / self.baseline_ratio
                    output["yankuang Ratio"]=current_ratio
        return output

    def visualize(self, frame, results):
        """可视化结果"""
        if results["landmarks"]:
            h, w = frame.shape[:2]
            landmarks = results["landmarks"]

            # 显示数据
            y_pos = 30
            info = [
                f"Eye Speed: {results['Eye Speed']:.2f}",
                f"shangyanlian Ratio: {results['shangyanlian Ratio']:.2f}",
                f"yankuang Ratio: {results['yankuang Ratio']}°",
                f"Blinks/min: {results['Blinks/min']:.1f}"
            ]

            for text in info:
                cv2.putText(frame, text, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255,0), 1)
                y_pos += 25
        return frame

    def run_realtime(self, frame =None,bbox=None):
        """实时检测"""
        if bbox is not None:
            # 从bbox裁剪人脸区域
            x1, y1, x2, y2 = map(int, bbox)
            aframe = frame[y1:y2, x1:x2]
            if aframe.size == 0:
                return "Error: Invalid bbox"
                # 转换为RGB并运行MediaPipe
            rgb_frame = cv2.cvtColor(aframe, cv2.COLOR_BGR2RGB)

            results = self.process_frame(rgb_frame)
            return results
        else:
            cap = cv2.VideoCapture(0)
            try:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break

                    results = self.analyze_frame(frame)
                    frame = self.visualize(frame, results)

                    cv2.imshow("Mouth Analysis (Eye Distance Normalized)", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            finally:
                cap.release()
                cv2.destroyAllWindows()
if __name__ == "__main__":
    analyzer = EyeAnalyzer()
    analyzer.run_realtime()
