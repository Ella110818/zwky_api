import logging
import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware

# 获取日志记录器
logger = logging.getLogger('zwky_api')

class CSRFExemptMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # 豁免所有API路径的CSRF验证
        if (request.path.startswith('/api/') or 
            request.path.startswith('/face_recognition/')):
            logger.debug(f"CSRF豁免路径: {request.path}")
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)

class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 记录请求开始时间
        request.start_time = time.time()
        
        # 获取请求体（如果有）
        # 检查内容类型，对于文件上传和非JSON请求，不尝试解析
        content_type = request.META.get('CONTENT_TYPE', '')
        
        if request.body and 'application/json' in content_type:
            try:
                body = json.loads(request.body)
                logger.debug(f"请求体: {json.dumps(body, ensure_ascii=False)}")
            except json.JSONDecodeError:
                logger.warning(f"无法解析JSON请求体: {request.body[:100]}")
        else:
            # 对于文件上传或其他类型的请求，只记录内容类型，不尝试解析请求体
            logger.info(f"请求内容类型: {content_type}")
            
        # 记录请求信息
        logger.info(
            f"收到请求 - 方法: {request.method}, "
            f"路径: {request.path}, "
            f"用户: {request.user if request.user.is_authenticated else '未认证'}, "
            f"IP: {request.META.get('REMOTE_ADDR')}"
        )

    def process_response(self, request, response):
        # 计算请求处理时间
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                f"请求完成 - 路径: {request.path}, "
                f"状态码: {response.status_code}, "
                f"处理时间: {duration:.2f}秒"
            )
        return response

    def process_exception(self, request, exception):
        # 记录异常信息
        logger.error(
            f"请求异常 - 路径: {request.path}, "
            f"异常类型: {type(exception).__name__}, "
            f"异常信息: {str(exception)}",
            exc_info=True
        ) 