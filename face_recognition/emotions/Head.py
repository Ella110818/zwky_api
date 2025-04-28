import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque
from scipy.spatial import distance

class HeadAnalyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # 定义关键点索引
        self.NOSE_TIP = 4  # 鼻尖
        self.FOREHEAD = 10  # 前额
        self.CHIN = 152  # 下巴
        self.LEFT_EAR = 127  # 左耳
        self.RIGHT_EAR = 356  # 右耳
        self.LEFT_EYE_INNER = 468  # 左眼内角
        self.RIGHT_EYE_INNER = 473  # 右眼内角

        # 初始化摄像头
        self.cap = cv2.VideoCapture(0)

        # 校准和检测参数
        self.calibration_frames = 30  # 30帧校准
        self.frame_count = 0
        self.vertical_ratios = []
        self.baseline_ratio = None
        self.calibrated = False

        # 点头检测参数
        self.NOD_THRESHOLD = 0.90  # 点头阈值(低于基准值的比例)
        self.nod_count = 0
        self.nod_start_time = time.time()
        self.nod_detected = False
        self.nod_history = deque(maxlen=10)  # 用于平滑处理

        # 状态常量
        self.STATE_UP = 0
        self.STATE_DOWN = 1
        self.current_state = self.STATE_UP

    def _update_baseline(self, smoothed_ratio):
        """更新基准值"""
        self.frame_count += 1
        self.vertical_ratios.append(smoothed_ratio)
        if self.frame_count > self.calibration_frames:
            self.baseline_ratio = np.mean(self.vertical_ratios)
            print(f"基准值校准完成 - 鼻子下巴间距与鼻子前额间距比值: {self.baseline_ratio:.4f}")

    def _getpixel(self,landmarks,w,h):
        return int(landmarks.x*w),int(landmarks.y*h)

    def analyze_frame(self, image):
        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.face_mesh.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        output={'Head Angle':0,
                'Rate':0,
                "landmarks": None,
                "calibrated": self.baseline_ratio is not None
                }

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            h, w = image.shape[:2]
            output["landmarks"] = landmarks

            # 获取关键点坐标
            left_eye = self._getpixel(landmarks.landmark[self.LEFT_EYE_INNER],w,h)
            right_eye = self._getpixel(landmarks.landmark[self.RIGHT_EYE_INNER],w,h)
            nose_tip = self._getpixel(landmarks.landmark[self.NOSE_TIP], w, h)
            forehead = self._getpixel(landmarks.landmark[self.FOREHEAD], w, h)

            # 计算参考距离(两眼内角距离)
            ref_distance = distance.euclidean(left_eye, right_eye)

            # 计算头部倾斜角度
            # 方法1：基于鼻子到前额的垂直线
            dx = nose_tip[0] - forehead[0]
            dy = nose_tip[1] - forehead[1]
            angle = np.degrees(np.arctan2(dy, dx)) - 90  # 转换为垂直角度

            # 方法2：基于两眼连线与水平线的角度
            eye_dx = right_eye[0] - left_eye[0]
            eye_dy = right_eye[1] - left_eye[1]
            eye_angle = np.degrees(np.arctan2(eye_dy, eye_dx))

            # 综合角度计算（微调版本）
            if abs(angle) > 10:  # 如果垂直角度较大，使用垂直角度
                final_angle = angle
            else:  # 否则使用眼睛连线角度（对微侧更敏感）
                final_angle = eye_angle * 0.7  # 加权系数
            output['Head Angle']=final_angle

            chin = self._getpixel(landmarks.landmark[self.CHIN],w,h)

            # 计算垂直比例 (下巴到鼻尖距离 / 鼻尖到前额距离)
            chin_to_nose = np.linalg.norm(np.array(chin) - np.array(nose_tip))
            nose_to_forehead = np.linalg.norm(np.array(nose_tip) - np.array(forehead))

            if nose_to_forehead > 0:
                vertical_ratio = chin_to_nose / nose_to_forehead
                self.nod_history.append(vertical_ratio)
                smoothed_ratio = np.mean(self.nod_history) if self.nod_history else vertical_ratio

                # 校准阶段
                if not output["calibrated"]:
                    self._update_baseline(smoothed_ratio)
                    return output

                # 检测阶段
                else:
                    # 计算当前比例与基准值的比例
                    ratio = smoothed_ratio / self.baseline_ratio

                    # 状态机检测点头动作
                    if ratio < self.NOD_THRESHOLD and self.current_state == self.STATE_UP:
                        self.current_state = self.STATE_DOWN
                    elif ratio >= self.NOD_THRESHOLD and self.current_state == self.STATE_DOWN:
                        self.current_state = self.STATE_UP
                        self.nod_count += 1  # 完成一次点头

                    # 计算点头频率
                    elapsed_time = time.time() - self.nod_start_time
                    if elapsed_time > 0:
                        nods_per_minute = (self.nod_count / elapsed_time) * 60
                    else:
                        nods_per_minute = 0
                    output['Rate']=nods_per_minute
        return output

    def visualize(self, image, results) :
        if results["landmarks"]:
            h, w = image.shape[:2]
            landmarks = results["landmarks"]
            angle=results['Head Angle']
            # 判断微侧方向
            if abs(angle) < 5:
                status = "CENTER"
                color = (0, 255, 0)  # 绿色
            elif angle > 0:
                status = "TILT RIGHT"
                color = (0, 0, 255)  # 红色
            else:
                status = "TILT LEFT"
                color = (255, 0, 0)  # 蓝色

            cv2.putText(image, f"Status: {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.putText(image, f"Head Angle: {angle}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            # 显示状态
            status = "NODDING DOWN" if self.current_state == self.STATE_DOWN else "HEAD UP"
            color = (0, 0, 255) if self.current_state == self.STATE_DOWN else (0, 255, 0)
            cv2.putText(image, f"Status: {status}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(image, f"Rate: {results['Rate']}", (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        return image

    def run_realtime(self, frame=None ,bbox=None):
        """实时检测"""
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
    analyzer = HeadAnalyzer()
    analyzer.run_realtime()