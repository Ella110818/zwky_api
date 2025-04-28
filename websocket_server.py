import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import os
import logging
from datetime import datetime
import sys
import traceback

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("websocket_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WebSocketServer")

# 检查CUDA是否可用
cuda_available = False
cuda_devices = 0
try:
    cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
    if cuda_devices > 0:
        cuda_available = True
        # 选择第一个CUDA设备
        cv2.cuda.setDevice(0)
        logger.info(f"CUDA加速已启用，检测到 {cuda_devices} 个CUDA设备")
        # 打印CUDA设备信息
        cv2.cuda.printCudaDeviceInfo(0)
    else:
        logger.warning("未检测到支持CUDA的设备，将使用CPU模式")
except Exception as e:
    logger.warning(f"初始化CUDA失败或CUDA不可用: {e}，将使用CPU模式")
    cuda_available = False

# 导入情绪识别和人脸检测模块
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from emotion_recognition.emotions.inmidinate_output import app, process_frame, load_target_feats_from_db, StatusLogger, DataCollector
    logger.info("成功导入情绪识别模块")
except Exception as e:
    logger.error(f"导入情绪识别模块失败: {e}")
    logger.error(traceback.format_exc())
    raise

# 创建数据收集器和日志记录器
data_collector = DataCollector()
logger_obj = StatusLogger()

# 加载人脸特征向量
try:
    # 尝试多个可能的数据库路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_db_paths = [
        os.path.join(current_dir, "db.sqlite3"),
        os.path.join(os.path.dirname(current_dir), "db.sqlite3"),
        os.path.join(current_dir, "emotion_recognition", "emotions", "db.sqlite3"),
        "db.sqlite3"
    ]
    
    db_path = None
    for path in possible_db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if db_path is None:
        # 使用默认路径
        db_path = possible_db_paths[0]  
        logger.warning(f"数据库文件未找到，将使用默认路径: {db_path}")
    
    logger.info(f"尝试从以下路径加载数据库: {db_path}")
    target_feats, target_names = load_target_feats_from_db(db_path)
    logger.info(f"成功加载 {len(target_names)} 个人脸特征向量")
except Exception as e:
    logger.error(f"加载人脸特征向量失败: {e}")
    logger.error(traceback.format_exc())
    # 创建空的列表以避免程序崩溃
    target_feats, target_names = [], []

# 存储活跃连接
active_connections = set()

# 全局变量跟踪识别到的学生
recognized_students = set()

# 创建CUDA流对象(如果CUDA可用)
cuda_stream = None
if cuda_available:
    try:
        cuda_stream = cv2.cuda.Stream()
        logger.info("成功创建CUDA流")
    except Exception as e:
        logger.error(f"创建CUDA流失败: {e}")
        cuda_available = False
        logger.warning("已切换到CPU模式")

# 获取CUDA优化的重采样方法
def get_cuda_interpolation(method):
    # 确保CUDA可用，否则返回原始方法
    if not cuda_available:
        return method
        
    try:
        if method == cv2.INTER_AREA:
            return cv2.cuda.INTER_AREA
        elif method == cv2.INTER_LINEAR:
            return cv2.cuda.INTER_LINEAR
        elif method == cv2.INTER_NEAREST:
            return cv2.cuda.INTER_NEAREST
        else:
            return cv2.cuda.INTER_LINEAR
    except Exception:
        # 如果出现任何错误，返回原始方法
        return method

async def process_video_frame(websocket, frame_data):
    """处理从客户端接收的视频帧"""
    try:
        # 解码Base64图像 - 使用更高效的解码方式
        img_data = base64.b64decode(frame_data)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error("无法解码图像数据")
            return {"error": "无法解码图像数据"}
        
        # 缩小图像尺寸以提高处理速度
        height, width = frame.shape[:2]
        if width > 640:  # 如果宽度大于640，则缩小
            scale = 640 / width
            new_width = 640
            new_height = int(height * scale)
            
            if cuda_available:
                try:
                    # 使用CUDA加速图像缩放
                    gpu_frame = cv2.cuda_GpuMat()
                    gpu_frame.upload(frame)
                    
                    # 使用CUDA重采样
                    gpu_resized = cv2.cuda.resize(
                        gpu_frame, 
                        (new_width, new_height), 
                        interpolation=get_cuda_interpolation(cv2.INTER_AREA),
                        stream=cuda_stream
                    )
                    
                    # 下载结果
                    frame = gpu_resized.download()
                except Exception as e:
                    logger.warning(f"CUDA图像缩放失败，回退到CPU: {e}")
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            else:
                # CPU缩放
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # 使用process_frame处理图像
        student_set = set()
        try:
            # 修改为接收任意数量的返回值，只使用第一个返回值（处理后的帧）
            result = process_frame(
                frame, target_feats, target_names, student_set, similarity_threshold=0.45
            )
            # 确保至少有一个返回值
            if isinstance(result, tuple):
                processed_frame = result[0]
                num_faces = result[1] if len(result) > 1 else len(student_set)
            else:
                processed_frame = result
                num_faces = len(student_set)
        except Exception as e:
            logger.error(f"处理图像时出错: {e}")
            logger.error(traceback.format_exc())
            return {"error": f"处理图像失败: {str(e)}"}
        
        # 更新全局识别到的学生集合
        recognized_students.update(student_set)
        
        # 优化：不是每帧都获取情绪状态数据
        static_frame_count = getattr(process_video_frame, 'frame_count', 0) + 1
        process_video_frame.frame_count = static_frame_count
        
        # 每3帧更新一次情绪统计
        if static_frame_count % 3 == 0:
            emotion_stats = data_collector.get_status_stats()
        else:
            emotion_stats = getattr(process_video_frame, 'last_emotion_stats', None)
        
        # 保存最后的情绪状态
        process_video_frame.last_emotion_stats = emotion_stats
        
        # 将处理后的帧编码为JPEG，优化质量和速度
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]  # 降低质量以减小数据量
        
        if cuda_available:
            try:
                # 使用CUDA加速JPEG编码
                gpu_processed = cv2.cuda_GpuMat()
                gpu_processed.upload(processed_frame)
                
                # 目前CUDA不直接支持JPEG编码，需要下载回CPU
                _, buffer = cv2.imencode('.jpg', processed_frame, encode_params)
            except Exception as e:
                logger.warning(f"CUDA图像编码失败，回退到CPU: {e}")
                _, buffer = cv2.imencode('.jpg', processed_frame, encode_params)
        else:
            # CPU编码
            _, buffer = cv2.imencode('.jpg', processed_frame, encode_params)
            
        processed_frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 返回结果，仅每3帧发送一次完整的统计数据
        if static_frame_count % 3 == 0:
            result = {
                "processed_frame": processed_frame_base64,
                "face_count": num_faces,
                "students_detected": list(student_set),
                "all_recognized_students": list(recognized_students),
                "emotion_stats": emotion_stats
            }
        else:
            # 简化返回数据，仅包含必要信息
            result = {
                "processed_frame": processed_frame_base64,
                "face_count": num_faces,
                "students_detected": list(student_set)
            }
        
        return result
    except Exception as e:
        logger.error(f"处理视频帧时发生错误: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

async def handle_client(websocket):
    """处理WebSocket客户端连接"""
    active_connections.add(websocket)
    client_id = id(websocket)
    logger.info(f"新客户端连接 [ID: {client_id}]")
    
    try:
        async for message in websocket:
            try:
                # 解析JSON消息
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "video_frame":
                    # 处理视频帧
                    frame_data = data.get("data", "")
                    if not frame_data:
                        await websocket.send(json.dumps({"error": "未提供视频帧数据"}))
                        continue
                    
                    result = await process_video_frame(websocket, frame_data)
                    await websocket.send(json.dumps(result))
                
                elif message_type == "reset":
                    # 重置会话数据
                    recognized_students.clear()
                    data_collector.reset()
                    await websocket.send(json.dumps({"status": "reset_complete"}))
                
                elif message_type == "ping":
                    # 心跳检测
                    await websocket.send(json.dumps({"type": "pong"}))
                
                else:
                    logger.warning(f"未知消息类型: {message_type}")
                    await websocket.send(json.dumps({"error": "未知消息类型"}))
            
            except json.JSONDecodeError:
                logger.error("JSON解析错误")
                await websocket.send(json.dumps({"error": "无效的JSON格式"}))
            
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}")
                logger.error(traceback.format_exc())
                await websocket.send(json.dumps({"error": str(e)}))
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端断开连接 [ID: {client_id}]")
    
    finally:
        # 清理连接
        active_connections.remove(websocket)
        logger.info(f"清理完成 [ID: {client_id}]")

async def shutdown_handler():
    """关闭服务器时的清理处理"""
    # 关闭所有连接
    if active_connections:
        await asyncio.gather(*(ws.close() for ws in active_connections))
    
    # 关闭日志记录器
    logger_obj.close()
    logger.info("服务器已关闭，所有连接已清理")

async def main():
    # 设置WebSocket服务器
    host = "0.0.0.0"  # 监听所有网络接口
    port = 8765
    
    # WebSocket服务器配置 - 优化并发和消息大小
    ws_config = {
        "max_size": 10 * 1024 * 1024,  # 增大最大消息大小为10MB
        "max_queue": 32,  # 增加队列大小
        "ping_timeout": 60,  # 增加ping超时时间
        "ping_interval": 30,  # 降低ping间隔
        "close_timeout": 10,  # 关闭超时时间
    }
    
    try:
        # 创建WebSocket服务器
        logger.info(f"正在启动WebSocket服务器 ws://{host}:{port}...")
        server = await websockets.serve(
            handle_client, 
            host, 
            port,
            max_size=ws_config["max_size"],
            ping_timeout=ws_config["ping_timeout"],
            ping_interval=ws_config["ping_interval"],
            close_timeout=ws_config["close_timeout"],
            max_queue=ws_config["max_queue"]
        )
        logger.info(f"WebSocket服务器启动成功，监听在 ws://{host}:{port}")
        
        # 运行服务器直到被取消
        await asyncio.Future()
    finally:
        # 关闭服务器时执行清理
        if 'server' in locals():
            server.close()
            await server.wait_closed()
        await shutdown_handler()

if __name__ == "__main__":
    # 设置更高的线程优先级（仅在Windows上有效）
    try:
        import os
        if os.name == 'nt':  # Windows系统
            import win32api, win32process, win32con
            pid = win32api.GetCurrentProcessId()
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
            win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
            logger.info("已将进程优先级设置为高")
    except ImportError:
        logger.info("无法设置进程优先级，缺少win32api模块")
    except Exception as e:
        logger.error(f"设置进程优先级时出错: {e}")
    
    # 增加事件循环的性能
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("已使用uvloop优化事件循环")
    except ImportError:
        logger.info("未安装uvloop，使用默认事件循环")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器错误: {e}")
        logger.error(traceback.format_exc()) 