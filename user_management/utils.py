from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def api_response(code=200, message="success", data=None):
    """
    自定义API响应格式
    """
    return Response({
        "code": code,
        "message": message,
        "data": data
    })

def custom_exception_handler(exc, context):
    """
    自定义异常处理
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # 获取错误详情
        error_message = ""
        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if isinstance(value, list):
                    error_message = f"{key}: {value[0]}"
                    break
                else:
                    error_message = f"{key}: {value}"
                    break
        elif isinstance(response.data, list) and len(response.data) > 0:
            error_message = response.data[0]
        else:
            error_message = "未知错误"
        
        # 设置自定义响应格式
        custom_response_data = {
            "code": response.status_code,
            "message": error_message,
            "data": None
        }
        response.data = custom_response_data
    
    return response

# 错误码定义
class ErrorCode:
    # 用户相关错误码
    USER_NOT_FOUND = 10000
    INVALID_CREDENTIALS = 10001
    USERNAME_EXISTS = 10002
    EMAIL_EXISTS = 10003
    INVALID_OLD_PASSWORD = 10004 