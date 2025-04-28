from zwky_api.settings import *

# 关闭调试模式
DEBUG = False

# 允许的主机 - 允许所有访问
ALLOWED_HOSTS = ['*']

# 静态文件配置
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# 媒体文件配置
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 安全设置
SECURE_SSL_REDIRECT = False  # 如果使用HTTPS，设为True
SESSION_COOKIE_SECURE = False  # 如果使用HTTPS，设为True
CSRF_COOKIE_SECURE = False  # 如果使用HTTPS，设为True

# 数据库配置 - 使用SQLite3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS设置
CORS_ALLOW_ALL_ORIGINS = True 