import sqlite3
import numpy as np
import os
import cv2
import shutil  # 用于移动文件夹
from insightface.app import FaceAnalysis
# 检测人脸
app = FaceAnalysis(name="buffalo_sc", providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
# 创建数据库连接
def create_connection(db_path):
    conn = sqlite3.connect(db_path)
    return conn

# 创建表
def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            feat BLOB NOT NULL
        )
    ''')
    conn.commit()

# 插入目标人脸特征向量
def insert_face(conn, name, feat):
    cursor = conn.cursor()
    # 将特征向量转换为二进制格式
    feat_blob = feat.tobytes()
    cursor.execute('''
        INSERT INTO faces (name, feat) VALUES (?, ?)
    ''', (name, feat_blob))
    conn.commit()


#在成功保存后将其放入新的一个文件夹
def load_target_feats_to_db(target_folder, db_path):
    conn = create_connection(db_path)
    create_table(conn)

    # 创建 usedTargetFace 文件夹（如果不存在）
    used_target_folder = os.path.join(os.path.dirname(target_folder), "usedTargetFace")
    os.makedirs(used_target_folder, exist_ok=True)

    # 遍历目标文件夹
    for person_name in os.listdir(target_folder):
        person_folder = os.path.join(target_folder, person_name)
        # 规范化路径格式
        person_folder = os.path.normpath(person_folder)

        if os.path.isdir(person_folder):  # 确保是文件夹
            for filename in os.listdir(person_folder):
                # 确保是一个图片文件
                if filename.endswith(".jpg") or filename.endswith(".png"):
                    target_path = os.path.join(person_folder, filename)
                    # 使用 open 读取文件内容
                    with open(target_path, 'rb') as f:
                        file_data = np.frombuffer(f.read(), dtype=np.uint8)
                    # 使用 cv2.imdecode 解码图片
                    target_img = cv2.imdecode(file_data, cv2.IMREAD_COLOR)
                    if target_img is None:
                        print(f"无法加载目标图片：{target_path}")
                        continue
                    target_faces = app.get(target_img)
                    if not target_faces:
                        print(f"目标图片中未检测到人脸：{target_path}")
                        continue
                    # 获得人脸特征向量
                    target_feat = np.array(target_faces[0].normed_embedding, dtype=np.float32)
                    insert_face(conn, person_name, target_feat)

            # 将处理完的文件夹移动到 usedTargetFace
            used_person_folder = os.path.join(used_target_folder, person_name)
            try:
                shutil.move(person_folder, used_person_folder)
                print(f"已将文件夹 {person_name} 移动到 {used_target_folder}")
            except Exception as e:
                print(f"移动文件夹失败：{e}")

    conn.close()

# # 加载目标人脸特征向量到数据库
# def load_target_feats_to_db(target_folder, db_path):
#     conn = create_connection(db_path)
#     create_table(conn)
#     # for filename in os.listdir(target_folder):
#     #     if filename.endswith(".jpg") or filename.endswith(".png"):
#     #         target_path = os.path.join(target_folder, filename)
#     #         target_img = cv2.imread(target_path)
#     #         if target_img is None:
#     #             print(f"无法加载目标图片：{target_path}")
#     #             continue
#     #         target_faces = app.get(target_img)
#     #         if not target_faces:
#     #             print(f"目标图片中未检测到人脸：{target_path}")
#     #             continue
#     #         target_feat = np.array(target_faces[0].normed_embedding, dtype=np.float32)
#     #         name = os.path.splitext(filename)[0]
#     #         insert_face(conn, name, target_feat)
#     # conn.close()
#     # 遍历目标文件夹
#     for person_name in os.listdir(target_folder):
#         person_folder = os.path.join(target_folder, person_name)
#         #规范化路径格式
#         person_folder = os.path.normpath(person_folder)
#         if os.path.isdir(person_folder):  # 确保是文件夹
#             for filename in os.listdir(person_folder):
#                 #确保是以一个图片文件夹
#                 if filename.endswith(".jpg") or filename.endswith(".png"):
#                     target_path = os.path.join(person_folder, filename)
#                     # 使用 open 读取文件内容
#                     with open(target_path, 'rb') as f:
#                         file_data = np.frombuffer(f.read(), dtype=np.uint8)
#                     # 使用 cv2.imdecode 解码图片
#                     target_img = cv2.imdecode(file_data, cv2.IMREAD_COLOR)
#                     if target_img is None:
#                         print(f"无法加载目标图片：{target_path}")
#                         continue
#                     target_faces = app.get(target_img)
#                     if not target_faces:
#                         print(f"目标图片中未检测到人脸：{target_path}")
#                         continue
#                         #获得人脸特征向量
#                     target_feat = np.array(target_faces[0].normed_embedding, dtype=np.float32)
#                     insert_face(conn, person_name, target_feat)

# 从数据库加载目标人脸特征向量
def load_target_feats_from_db(db_path):
    conn = create_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT name, feat FROM faces')
    rows = cursor.fetchall()
    target_feats = []
    target_names = []
    for row in rows:
        name, feat_blob = row
        # 将二进制数据转换回 numpy 数组
        feat = np.frombuffer(feat_blob, dtype=np.float32)
        target_feats.append(feat)
        target_names.append(name)
    conn.close()
    return target_feats, target_names




def compare_faces(target_feats, target_names, feats, similarity_threshold=0.6):
    """
    对比检测到的人脸特征向量与目标人脸特征向量，返回所有匹配的人脸。

    参数:
        target_feats (list): 目标人脸特征向量列表。
        target_names (list): 目标人脸名字列表。
        feats (np.ndarray): 检测到的人脸特征向量。
        similarity_threshold (float): 相似度阈值，默认 0.6。

    返回:
        matches (list): 包含匹配的人脸信息的列表，每个元素是一个字典，包含：
            - "target_index": 匹配的人脸索引。
            - "target_name": 匹配的人脸名字。
            - "similarity": 匹配的相似度。
    """
    matches = []  # 用于存储所有匹配的人脸信息

    # 遍历所有目标人脸特征向量
    for i, target_feat in enumerate(target_feats):
        # 计算相似度
        sims = np.dot(feats, target_feat)
        max_similarity = np.max(sims)  # 当前目标人脸的最大相似度
        target_index = int(sims.argmax())  # 最匹配的人脸索引

        # 如果相似度超过阈值，记录匹配信息
        if max_similarity > similarity_threshold:
            match_info = {
                "target_index": target_index,
                "target_name": target_names[i],
                "similarity": max_similarity
            }
            matches.append(match_info)

    # 如果没有找到匹配的人脸
    if not matches:
        print("未找到明显匹配的人脸")
        return []

    return matches


def draw_target_face(frame, faces, matches):
    """
    在视频帧上绘制多个人脸框和名字。

    参数:
        frame (np.ndarray): 视频帧（单张图像）。
        faces (list): 检测到的人脸对象列表（每个对象包含 bbox 和 kps）。
        matches (list): 包含匹配的人脸信息的列表，每个元素是一个字典，包含：
            - "target_index": 匹配的人脸索引。
            - "target_name": 匹配的人脸名字。
            - "similarity": 匹配的相似度。

    返回:
        frame (np.ndarray): 绘制了多个人脸框和名字的视频帧。
    """
    # 遍历所有检测到的人脸
    for i, face in enumerate(faces):
        # 获取人脸框坐标
        bbox = face.bbox.astype(int)  # 人脸框坐标
        kps = face.kps.astype(int)  # 人脸关键点坐标（可选）

        # 检查当前人脸是否有匹配
        match_found = False
        for match in matches:
            if match["target_index"] == i:
                match_found = True
                target_name = match["target_name"]
                similarity = match["similarity"]
                label = f"{target_name} ({similarity:.2f})"
                break

        # 如果没有匹配的人脸，显示 "unknown"
        if not match_found:
            label = "unknown"

        # 绘制人脸框
        frame = app.draw_on(frame, [face])

        # 在人脸框上方添加名字和相似度
        cv2.putText(
            frame,  # 图像
            label,  # 名字和相似度
            (bbox[0], bbox[1] - 10),  # 文字位置
            cv2.FONT_HERSHEY_SIMPLEX,  # 字体
            0.9,  # 字体大小
            (0, 255, 0) if match_found else (0, 0, 255),  # 颜色 (绿色匹配，红色未知)
            2  # 线宽
        )

    return frame

# 示例：将目标人脸特征向量存储到数据库
if __name__ == '__main__':
    target_folder = r"data/targetFace"
    db_path = r"data/faces.db"
    load_target_feats_to_db(target_folder, db_path)