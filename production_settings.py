"""
Django生产环境设置文件
"""

from pathlib import Path
from datetime import timedelta
import os
import sys

# 导入基本设置
from zwky_api.settings import *

# SECURITY WARNING: 不要在生产环境中启用调试模式
DEBUG = False

# 允许的主机
ALLOWED_HOSTS = ['*']  # 替换为您的实际域名或IP

# 数据库设置
# 注意：根据您的实际情况选择一个数据库配置
# SQLite配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# MySQL配置（取消注释以使用MySQL）
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'zwky_db',
#         'USER': 'zwky_user',
#         'PASSWORD': '您的数据库密码',
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#         },
#     }
# }

# 静态文件设置
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# 媒体文件设置
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# 安全设置
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CORS设置 - 生产环境下应明确指定允许的来源
CORS_ALLOWED_ORIGINS = [
    # 替换为您的前端域名
    "http://localhost:8080",
]
# 或者在开发阶段允许所有来源（不推荐用于生产环境）
# CORS_ALLOW_ALL_ORIGINS = True

# 日志设置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'zwky_api.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'error.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'zwky_api': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
} 