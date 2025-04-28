"""
WSGI配置文件，用于PythonAnywhere部署
"""

import os
import sys

# 添加项目路径到系统路径
# 替换 '你的用户名' 为您的PythonAnywhere用户名
path = '/home/wstier477/zwky_api'
if path not in sys.path:    
    sys.path.append(path)

# 设置Django设置模块  
os.environ['DJANGO_SETTINGS_MODULE'] = 'zwky_api.pythonanywhere_settings'

# 导入Django的WSGI应用
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application() 