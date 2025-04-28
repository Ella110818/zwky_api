import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List
from collections import deque


class MouthAnalyzer:
    def __init__(self):
        """初始化 Face Mesh 并配置嘴部关键点索引"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 关键点索引
        self.LIPS_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409,
                           291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
        self.TONGUE_INDICES = [152, 148, 176, 149, 150, 136, 172, 58, 132]

        # 基准点索引（用于局部坐标系）
        self.REFERENCE_POINTS = {
            'nose_tip': 4,
            'forehead': 10,
            'left_eye': 468,
            'right_eye': 473
        }

        # 基准系统
        self.baseline_eye_distance = None  # 基准两眼距离
        self.calibration_frames = 30  # 校准帧数
        self.calibration_counter = 0  # 已校准帧数
        self.calibration_values = []  # 校准值存储

        # 阈值配置（基于基准值的比例）
        self.YAWN_THRESHOLD = 0.2  # 嘴唇间距/两眼距离
        self.TONGUE_PRESS_THRESHOLD = 0.1  # 舌尖接触阈值
        self.MOUTH_ANGLE_THRESHOLD = 10  # 嘴角角度阈值（度）

        # 状态跟踪
        self.yawn_frames = 0
        self.required_yawn_frames = 5  # 连续5帧判定为哈欠

        # 平滑处理
        self.smoothing_window = 5
        self.eye_distance_history = deque(maxlen=self.smoothing_window)
        self.lip_distance_history = deque(maxlen=self.smoothing_window)

    def _update_baseline(self, eye_distance):
        """更新基准值"""
        self.calibration_values.append(eye_distance)
        self.calibration_counter += 1

        if self.calibration_counter >= self.calibration_frames:
            self.baseline_eye_distance = np.median(self.calibration_values)
            print(f"基准值校准完成 - 两眼距离: {self.baseline_eye_distance:.4f}")

    def _get_eye_distance(self, landmarks, frame_shape):
        """计算两眼距离（归一化坐标）"""
        left_eye = np.array([landmarks.landmark[234].x, landmarks.landmark[234].y])
        right_eye = np.array([landmarks.landmark[454].x, landmarks.landmark[454].y])
        return np.linalg.norm(left_eye - right_eye)

    def _get_local_mouth_angle(self, landmarks, frame_shape) :
        """计算抗旋转的嘴角角度（基于局部坐标系）"""
        # 获取基准点像素坐标
        ref = {name: self._normalized_to_pixel(landmarks.landmark[idx], frame_shape)
               for name, idx in self.REFERENCE_POINTS.items()}

        # 构建局部坐标系
        x_axis = np.array(ref['right_eye']) - np.array(ref['left_eye'])
        y_axis = np.array(ref['forehead']) - np.array(ref['nose_tip'])
        y_axis = y_axis - np.dot(y_axis, x_axis) * x_axis / np.linalg.norm(x_axis) ** 2

        # 转换嘴角坐标
        def to_local(point):
            vec = np.array(point) - np.array(ref['nose_tip'])
            x = np.dot(vec, x_axis) / np.linalg.norm(x_axis)
            y = np.dot(vec, y_axis) / np.linalg.norm(y_axis)
            return (x, y)

        left_local = to_local(self._normalized_to_pixel(landmarks.landmark[61], frame_shape))
        right_local = to_local(self._normalized_to_pixel(landmarks.landmark[291], frame_shape))

        # 计算局部角度
        dx = right_local[0] - left_local[0]
        dy = right_local[1] - left_local[1]
        return np.degrees(np.arctan2(dy, dx))

    def _normalized_to_pixel(self, landmark, frame_shape):
        """归一化坐标转像素坐标"""
        return int(landmark.x * frame_shape[1]), int(landmark.y * frame_shape[0])

    def analyze_frame(self, frame,bbox=None):
        """分析嘴部行为（基于基准值的比例）"""
        if(bbox is not None):
            # 从bbox裁剪人脸区域
            x1, y1, x2, y2 = map(int, bbox)
            aframe = frame[y1:y2, x1:x2]
            if aframe.size == 0:
                return "Error: Invalid bbox"
                # 转换为RGB并运行MediaPipe
            rgb_frame = cv2.cvtColor(aframe, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        output = {
            "lip_distance_ratio": 0,
            "mouth_angle": 0,
            "is_yawning": False,
            "is_lip_tucked": False,
            #"is_tongue_pressing": False,
            "landmarks": None,
            "calibrated": self.baseline_eye_distance is not None
        }

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            h, w = frame.shape[:2]
            output["landmarks"] = landmarks

            # 计算两眼距离（归一化坐标）
            current_eye_distance = self._get_eye_distance(landmarks, (h, w))
            self.eye_distance_history.append(current_eye_distance)
            smoothed_eye_distance = np.mean(self.eye_distance_history)

            # 校准阶段
            if not output["calibrated"]:
                self._update_baseline(smoothed_eye_distance)
                return output

            # 计算关键点像素坐标
            mouth_pts = {idx: self._normalized_to_pixel(landmarks.landmark[idx], (h, w))
                         for idx in self.LIPS_OUTER + self.TONGUE_INDICES + [13, 14, 152]}

            # 1. 嘴唇间距（基于基准值的比例）
            upper_lip = mouth_pts[13]
            lower_lip = mouth_pts[14]
            lip_distance_px = abs(upper_lip[1] - lower_lip[1])
            self.lip_distance_history.append(lip_distance_px)
            smoothed_lip_distance = np.mean(self.lip_distance_history)

            # 转换为相对于两眼距离的比例
            output["lip_distance_ratio"] = smoothed_lip_distance / (self.baseline_eye_distance * w)

            # 2. 抗旋转嘴角角度
            output["mouth_angle"] = self._get_local_mouth_angle(landmarks, (h, w))

            # 3. 打哈欠检测（需同时满足间距和角度条件）
            if (output["lip_distance_ratio"] > self.YAWN_THRESHOLD and
                    abs(output["mouth_angle"]) < self.MOUTH_ANGLE_THRESHOLD):
                self.yawn_frames += 1
                output["is_yawning"] = self.yawn_frames >= self.required_yawn_frames
            else:
                self.yawn_frames = 0
                output["is_yawning"] = False

            # 4. 下唇微收
            chin = mouth_pts[152]
            output["is_lip_tucked"] = lower_lip[1] < chin[1]

            # 5. 舌尖接触检测（基于比例）
            #tongue_tip = mouth_pts[152]
            #palate = mouth_pts[13]
            #tongue_press_distance = abs(tongue_tip[1] - palate[1]) / (self.baseline_eye_distance * w)
            #output["is_tongue_pressing"] = tongue_press_distance < self.TONGUE_PRESS_THRESHOLD

        return output

    def visualize(self, frame, results) :
        """可视化结果"""
        if results["landmarks"]:
            h, w = frame.shape[:2]
            landmarks = results["landmarks"]

            # 绘制嘴部关键点
            for idx in self.LIPS_OUTER:
                pt = self._normalized_to_pixel(landmarks.landmark[idx], (h, w))
                cv2.circle(frame, pt, 2, (0, 255, 0), -1)

            # 显示数据
            y_pos = 30
            info = [
                f"Eye Dist: {self.baseline_eye_distance:.4f}" if results['calibrated'] else "Calibrating...",
                f"Lip Ratio: {results['lip_distance_ratio']:.2f}",
                f"Mouth Angle: {results['mouth_angle']:.1f}°",
                f"Yawning: {'YES' if results['is_yawning'] else f'{self.yawn_frames}/{self.required_yawn_frames}'}",
                #f"Tongue: {'PRESS' if results['is_tongue_pressing'] else 'NO'}"
            ]

            for text in info:
                cv2.putText(frame, text, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)
                y_pos += 25

            # 行为高亮
            if results["is_yawning"]:
                cv2.putText(frame, "YAWNING!", (w // 3, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            #if results["is_tongue_pressing"]:
                #cv2.putText(frame, "TONGUE PRESS", (w // 3, 80),
                            #cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        return frame

    def run_realtime(self, frame=None,bbox=None):#(self, video_source=0)
         """实时检测"""
         if (bbox is not None):
             # 从bbox裁剪人脸区域
             x1, y1, x2, y2 = map(int, bbox)
             aframe = frame[y1:y2, x1:x2]
             if aframe.size == 0:
                 return "Error: Invalid bbox"
                 # 转换为RGB并运行MediaPipe
             rgb_frame = cv2.cvtColor(aframe, cv2.COLOR_BGR2RGB)
             results = self.analyze_frame(rgb_frame)
             return results
         else:
             #rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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
    analyzer = MouthAnalyzer()
    analyzer.run_realtime()