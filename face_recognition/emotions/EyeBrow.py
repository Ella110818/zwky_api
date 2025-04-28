import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time


class AdvancedFrownDetector:
    def __init__(self):
        """初始化高级皱眉检测器"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 关键点索引
        self.LEFT_EYEBROW_INNER = 107  # 左眉头内侧
        self.RIGHT_EYEBROW_INNER = 336  # 右眉头内侧
        self.GLABELLA_POINTS = [9, 55, 285, 168, 8]  # 眉间区域关键点
        self.NOSE_TIP = 4  # 鼻尖参考点
        self.LEFT_EYE = 468
        self.RIGHT_EYE = 473
        self.NOSE_ROOT = 168
        self.left_eyebrow_middle=105  #左侧眉中
        self.right_eyebrow_middle=334 #右侧眉中

        # 动态基准系统
        self.baseline_distance = None  # 基准眉头间距
        self.baseline_glabella_height = None  # 基准眉间高度
        self.baseline_asymmetry = None  # 基准不对称度
        self.calibration_frames = 30  # 校准帧数
        self.calibration_counter = 0  # 校准计数器
        self.calibration_values = []  # 校准值存储

        # 检测参数
        self.DISTANCE_THRESHOLD = 0.97  # 眉头间距阈值
        self.GLABELLA_THRESHOLD = 0.95  # 眉间隆起阈值
        self.ASYMMETRY_THRESHOLD = 1.5  # 不对称度阈值(相对于基准的比例)
        self.SMOOTHING_WINDOW = 5  # 平滑窗口大小
        self.distance_history = deque(maxlen=self.SMOOTHING_WINDOW)
        self.glabella_history = deque(maxlen=self.SMOOTHING_WINDOW)
        self.asymmetry_history = deque(maxlen=self.SMOOTHING_WINDOW)

        # 时间检测机制
        self.FROWN_TIME_THRESHOLD = 0.3  # 秒（需持续0.3秒才判定为有效皱眉）
        self.frown_start_time = None
        self.frown_detected = False
        self.fps = 30
        self.frame_count = 0
        self.start_time = time.time()

    def _calculate_metrics(self, landmarks, frame_shape):
        """计算所有关键指标（包括不对称度）"""
        if len(frame_shape) == 3:
            h, w = frame_shape[:2]
        else:
            h, w = frame_shape

        # 获取关键点坐标(归一化坐标)
        left_eye = np.array([landmarks.landmark[self.LEFT_EYE].x, landmarks.landmark[self.LEFT_EYE].y])
        right_eye = np.array([landmarks.landmark[self.RIGHT_EYE].x, landmarks.landmark[self.RIGHT_EYE].y])
        eye_distance = np.linalg.norm(left_eye - right_eye)

        # 眉头关键点
        left_inner = np.array([landmarks.landmark[self.LEFT_EYEBROW_INNER].x,
                               landmarks.landmark[self.LEFT_EYEBROW_INNER].y])
        right_inner = np.array([landmarks.landmark[self.RIGHT_EYEBROW_INNER].x,
                                landmarks.landmark[self.RIGHT_EYEBROW_INNER].y])
        # 眉头关键点
        left_middle = np.array([landmarks.landmark[self.left_eyebrow_middle].x,
                               landmarks.landmark[self.left_eyebrow_middle].y])
        right_middle = np.array([landmarks.landmark[self.right_eyebrow_middle].x,
                                landmarks.landmark[self.right_eyebrow_middle].y])

        # 计算眉头间距比例
        eyebrow_distance = np.linalg.norm(left_inner - right_inner) / eye_distance

        # 计算眉间区域高度比例
        nose_root = np.array([landmarks.landmark[self.NOSE_ROOT].x,
                              landmarks.landmark[self.NOSE_ROOT].y])
        glabella_points = []
        for idx in self.GLABELLA_POINTS:
            point = np.array([landmarks.landmark[idx].x, landmarks.landmark[idx].y])
            glabella_points.append(point)
        glabella_heights = [np.linalg.norm(p - nose_root) / eye_distance for p in glabella_points]
        avg_glabella_height = np.mean(glabella_heights)

        # 计算眉毛不对称度（左右眉毛高度差比例）
        left_brow_height = np.linalg.norm(left_middle - nose_root) / eye_distance
        right_brow_height = np.linalg.norm(right_middle - nose_root) / eye_distance
        asymmetry_ratio = abs(left_brow_height - right_brow_height) / max(left_brow_height, right_brow_height, 0.001)

        # 转换为像素坐标用于可视化
        left_inner_px = (int(left_inner[0] * w), int(left_inner[1] * h))
        right_inner_px = (int(right_inner[0] * w), int(right_inner[1] * h))
        glabella_points_px = [(int(p[0] * w), int(p[1] * h)) for p in glabella_points]
        nose_root_px = (int(nose_root[0] * w), int(nose_root[1] * h))

        return {
            'eyebrow_ratio': eyebrow_distance,
            'glabella_ratio': avg_glabella_height,
            'asymmetry_ratio': asymmetry_ratio,
            'left_inner': left_inner_px,
            'right_inner': right_inner_px,
            'glabella_points': glabella_points_px,
            'nose_root': nose_root_px,
            'eye_distance_px': eye_distance * w
        }

    def _update_baseline(self, metrics):
        """更新基准值（包括不对称度基准）"""
        self.calibration_values.append((metrics['eyebrow_ratio'],
                                        metrics['glabella_ratio'],
                                        metrics['asymmetry_ratio']))
        self.calibration_counter += 1

        if self.calibration_counter >= self.calibration_frames:
            ratios, heights, asymmetries = zip(*self.calibration_values)
            self.baseline_distance = np.median(ratios)
            self.baseline_glabella_height = np.median(heights)
            self.baseline_asymmetry = np.median(asymmetries)
            print(f"基准值校准完成 - 眉头间距: {self.baseline_distance:.3f}, "
                  f"眉间高度: {self.baseline_glabella_height:.3f}, "
                  f"不对称度: {self.baseline_asymmetry:.3f}")

    def process_frame(self, frame):
        """处理每一帧图像（增加不对称度检测）"""
        # 帧率计算
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        current_fps = self.frame_count / elapsed
        self.fps = 0.9 * self.fps + 0.1 * current_fps
        #初始化结果
        results = {
            'eyebrow_ratio': 0,
            'glabella_ratio': 0,
            'asymmetry_ratio': 0,
            'is_frowning': False,
            'is_asymmetric': False,
            'frown_detected': False,
            'calibrated': self.baseline_distance is not None,
            'fps': self.fps
        }

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh_results = self.face_mesh.process(rgb_frame)

        if mesh_results.multi_face_landmarks:
            #获得坐标
            landmarks = mesh_results.multi_face_landmarks[0]
            #计算度量指标，landmarks就是关键点以及坐标信息
            metrics = self._calculate_metrics(landmarks, frame.shape)

            # 平滑处理
            #平滑处理的目的是减少因噪声或瞬间变化导致的度量指标波动，使结果更加稳定。
            self.distance_history.append(metrics['eyebrow_ratio'])
            self.glabella_history.append(metrics['glabella_ratio'])
            self.asymmetry_history.append(metrics['asymmetry_ratio'])

            smoothed_distance = np.mean(self.distance_history) if self.distance_history else metrics['eyebrow_ratio']
            smoothed_glabella = np.mean(self.glabella_history) if self.glabella_history else metrics['glabella_ratio']
            smoothed_asymmetry = np.mean(self.asymmetry_history) if self.asymmetry_history else metrics[
                'asymmetry_ratio']

            results.update({
                'eyebrow_ratio': smoothed_distance,
                'glabella_ratio': smoothed_glabella,
                'asymmetry_ratio': smoothed_asymmetry,
                'landmarks': landmarks,
                'left_inner': metrics['left_inner'],
                'right_inner': metrics['right_inner'],
                'glabella_points': metrics['glabella_points'],
                'nose_root': metrics['nose_root'],
                'eye_distance_px': metrics['eye_distance_px']
            })

            if not results['calibrated']:
                self._update_baseline(metrics)
            else:
                # 计算相对于基准的变化
                distance_condition = smoothed_distance < (self.DISTANCE_THRESHOLD * self.baseline_distance)
                glabella_condition = smoothed_glabella < (self.GLABELLA_THRESHOLD * self.baseline_glabella_height)
                asymmetry_condition = smoothed_asymmetry > (self.ASYMMETRY_THRESHOLD * self.baseline_asymmetry)

                current_frowning = distance_condition and glabella_condition

                # 时间窗口验证
                current_time = time.time()
                if current_frowning:
                    if self.frown_start_time is None:
                        self.frown_start_time = current_time
                    else:
                        if (current_time - self.frown_start_time) >= self.FROWN_TIME_THRESHOLD:
                            self.frown_detected = True
                else:
                    self.frown_start_time = None
                    self.frown_detected = False

                results.update({
                    'is_frowning': current_frowning,
                    'is_asymmetric': asymmetry_condition,
                    'frown_detected': self.frown_detected,
                    'distance_condition': distance_condition,
                    'glabella_condition': glabella_condition,
                    'frown_duration': current_time - self.frown_start_time if self.frown_start_time else 0
                })

        return results

    def visualize(self, frame, results):
        """可视化检测结果（增加不对称度显示）"""
        h, w = frame.shape[:2]
        if results.get('landmarks'):
            #h, w = frame.shape[:2]

            # 绘制关键点连线
            cv2.line(frame, results['left_inner'], results['right_inner'], (0, 255, 255), 2)

            # 绘制关键点
            cv2.circle(frame, results['left_inner'], 5, (0, 255, 0), -1)
            cv2.circle(frame, results['right_inner'], 5, (0, 255, 0), -1)
            for point in results['glabella_points']:
                cv2.circle(frame, point, 3, (255, 0, 0), -1)
            cv2.circle(frame, results['nose_root'], 5, (255, 255, 0), -1)

            # 显示距离信息
            mid_point = ((results['left_inner'][0] + results['right_inner'][0]) // 2,
                         (results['left_inner'][1] + results['right_inner'][1]) // 2)
            cv2.putText(frame, f"Eyebrow Ratio: {results['eyebrow_ratio']:.3f}",
                        (mid_point[0] - 100, mid_point[1] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # 显示眉间高度信息
            glabella_center = np.mean(results['glabella_points'], axis=0).astype(int)
            cv2.putText(frame, f"Glabella Ratio: {results['glabella_ratio']:.3f}",
                        (glabella_center[0] - 50, glabella_center[1] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # 显示不对称度信息
            cv2.putText(frame, f"Asymmetry: {results['asymmetry_ratio']:.3f}",
                        (w - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

            # 显示状态信息
            status_y = 30
            if not results['calibrated']:
                cv2.putText(frame, "Calibrating...", (10, status_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 2)
            else:
                # 显示基准值
                cv2.putText(frame, f"Baseline - Eyebrow: {self.baseline_distance:.3f}",
                            (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
                status_y += 25
                cv2.putText(frame, f"Baseline - Glabella: {self.baseline_glabella_height:.3f}",
                            (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
                status_y += 25
                cv2.putText(frame, f"Baseline - Asymmetry: {self.baseline_asymmetry:.3f}",
                            (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)

                # 显示当前状态
                status_y += 30
                dist_status = "down" if results['distance_condition'] else "smooth"
                cv2.putText(frame, f"Eyebrow: {results['eyebrow_ratio']:.3f} {dist_status}",
                            (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 0, 255) if results['distance_condition'] else (200, 200, 0), 1)

                status_y += 25
                glab_status = "down" if results['glabella_condition'] else "smooth"
                cv2.putText(frame, f"Glabella: {results['glabella_ratio']:.3f} {glab_status}",
                            (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 0, 255) if results['glabella_condition'] else (200, 200, 0), 1)

                status_y += 25
                asym_status = "up" if results['is_asymmetric'] else "smooth"
                cv2.putText(frame, f"Asymmetry: {results['asymmetry_ratio']:.3f} {asym_status}",
                            (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 0, 255) if results['is_asymmetric'] else (200, 200, 0), 1)

                # 高亮特殊状态
                if results['frown_detected']:
                    cv2.putText(frame, "FROWN DETECTED!", (w // 2 - 100, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    cv2.putText(frame, f"Duration: {results['frown_duration']:.2f}s",
                                (w // 2 - 80, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                elif results['is_frowning']:
                    progress = min(1.0, results['frown_duration'] / self.FROWN_TIME_THRESHOLD)
                    cv2.putText(frame, f"Frowning... {progress * 100:.0f}%",
                                (w // 2 - 100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

                if results['is_asymmetric']:
                    cv2.putText(frame, "ASYMMETRY DETECTED!", (w // 2 - 120, h - 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)

        # 显示FPS
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (w - 120, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        return frame

    def run_realtime(self, frame=None,bbox=None):
        """运行实时检测"""
        if (bbox is not None):
            # 从bbox裁剪人脸区域
            x1, y1, x2, y2 = map(int, bbox)
            aframe = frame[y1:y2, x1:x2]
            if aframe.size == 0:
                return "Error: Invalid bbox"
                # 转换为RGB并运行MediaPipe
            rgb_frame = cv2.cvtColor(aframe, cv2.COLOR_BGR2RGB)

            results=self.process_frame(rgb_frame)
            return results
        else:
            #video_source=cv2.VideoCapture(0)
            cap = cv2.VideoCapture(0)
            try:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    results = self.process_frame(frame)
                    frame = self.visualize(frame, results)

                    cv2.imshow("Advanced Frown & Asymmetry Detection", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            finally:
                cap.release()
                cv2.destroyAllWindows()
            return results


if __name__ == "__main__":
    detector = AdvancedFrownDetector()
    detector.run_realtime()