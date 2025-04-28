import cv2
import mediapipe as mp
import numpy as np


class HeadDownDetector:
    def __init__(self, calibration_frames=30, threshold_multiplier=1.3):
        """
        初始化低头检测器

        参数:
            calibration_frames: 校准所需的帧数 (默认30帧)
            threshold_multiplier: 低头检测阈值乘数 (默认1.3)
        """
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 关键点索引
        self.NOSE_TIP = 4
        self.FOREHEAD = 10
        self.CHIN = 152

        # 校准参数
        self.calibration_frames = calibration_frames
        self.frame_count = 0
        self.vertical_ratios = []
        self.baseline_ratio = None
        self.calibrated = False
        self.threshold_multiplier = threshold_multiplier

    def detect_head_down(self, frame):
        """
        检测头部上下状态

        参数:
            frame: 输入图像帧 (BGR格式)

        返回:
            {
                "head_status": "HEAD DOWN" | "HEAD UP",
                "color": (B, G, R),  # 状态对应的显示颜色
                "vertical_ratio": float,  # 当前垂直比例
                "calibrated": bool  # 是否已完成校准
            }
        """
        # 默认返回值
        result = {
            "head_status": "HEAD UP",
            "color": (0, 255, 0),  # 绿色
            "vertical_ratio": 0.0,
            "calibrated": self.calibrated
        }

        # 预处理图像
        image = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # 检测面部和姿势
        face_results = self.face_mesh.process(image)
        pose_results = self.pose.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if face_results.multi_face_landmarks and pose_results.pose_landmarks:
            # 获取关键点坐标
            landmarks = face_results.multi_face_landmarks[0].landmark
            h, w = frame.shape[:2]

            nose_tip = (int(landmarks[self.NOSE_TIP].x * w), int(landmarks[self.NOSE_TIP].y * h))
            forehead = (int(landmarks[self.FOREHEAD].x * w), int(landmarks[self.FOREHEAD].y * h))
            chin = (int(landmarks[self.CHIN].x * w), int(landmarks[self.CHIN].y * h))

            # 计算垂直比例
            chin_to_nose = np.linalg.norm(np.array(chin) - np.array(nose_tip))
            nose_to_forehead = np.linalg.norm(np.array(nose_tip) - np.array(forehead))

            if chin_to_nose > 0:
                vertical_ratio = nose_to_forehead / chin_to_nose
                result["vertical_ratio"] = vertical_ratio

                # 校准阶段
                if not self.calibrated:
                    self.frame_count += 1
                    self.vertical_ratios.append(vertical_ratio)

                    if self.frame_count >= self.calibration_frames:
                        self.baseline_ratio = np.mean(self.vertical_ratios)
                        self.calibrated = True
                        result["calibrated"] = True

                # 检测阶段
                elif self.baseline_ratio is not None:
                    if vertical_ratio > self.baseline_ratio * self.threshold_multiplier:
                        result["head_status"] = "HEAD DOWN"
                        result["color"] = (0, 0, 255)  # 红色

        return result


# 使用示例
if __name__ == "__main__":
    detector = HeadDownDetector()
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 检测头部状态
        head_result = detector.detect_head_down(frame)

        # 在图像上显示结果
        status_text = f"Status: {head_result['head_status']}"
        ratio_text = f"Ratio: {head_result['vertical_ratio']:.2f}"
        calib_text = "Calibrated" if head_result['calibrated'] else "Calibrating..."

        cv2.putText(frame, status_text, (30, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, head_result['color'], 2)
        cv2.putText(frame, ratio_text, (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 1)
        cv2.putText(frame, calib_text, (30, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 1)

        cv2.imshow('Head Down Detection', frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()