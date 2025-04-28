import os
import sys
import json
import requests
from pathlib import Path

# 设置 Django 环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zwky_api.settings')

import django
django.setup()

# 导入所有 URL 模式
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

def generate_api_docs():
    """生成 API 文档 Markdown"""
    with open('API_DOCUMENTATION.md', 'w', encoding='utf-8') as f:
        f.write('# 智慧课堂 API 文档\n\n')
        f.write('本文档提供了智慧课堂系统的 API 接口说明。\n\n')
        
        # 用户管理模块
        f.write('## 1. 用户管理模块\n\n')
        f.write('### 1.1 登录\n\n')
        f.write('- **URL**: `/api/user/login/`\n')
        f.write('- **方法**: POST\n')
        f.write('- **描述**: 用户登录并获取 JWT 令牌\n')
        f.write('- **请求参数**:\n')
        f.write('  - `username`: 用户名\n')
        f.write('  - `password`: 密码\n')
        f.write('- **响应示例**:\n')
        f.write('```json\n')
        f.write('{\n')
        f.write('  "refresh": "刷新令牌",\n')
        f.write('  "access": "访问令牌",\n')
        f.write('  "user": {\n')
        f.write('    "id": 1,\n')
        f.write('    "username": "admin",\n')
        f.write('    "email": "admin@example.com",\n')
        f.write('    "role": "admin"\n')
        f.write('  }\n')
        f.write('}\n')
        f.write('```\n\n')
        
        # 课程管理模块
        f.write('## 2. 课程管理模块\n\n')
        f.write('### 2.1 获取课程列表\n\n')
        f.write('- **URL**: `/api/course/`\n')
        f.write('- **方法**: GET\n')
        f.write('- **描述**: 获取所有课程的列表\n')
        f.write('- **权限**: 仅管理员和教师可查看所有课程，学生仅可查看已选课程\n')
        f.write('- **请求参数**:\n')
        f.write('  - 无\n')
        f.write('- **响应示例**:\n')
        f.write('```json\n')
        f.write('[\n')
        f.write('  {\n')
        f.write('    "id": 1,\n')
        f.write('    "title": "Python编程基础",\n')
        f.write('    "code": "CS101",\n')
        f.write('    "teacher": {\n')
        f.write('      "id": 2,\n')
        f.write('      "username": "teacher1",\n')
        f.write('      "name": "张教授"\n')
        f.write('    },\n')
        f.write('    "description": "Python编程入门课程",\n')
        f.write('    "term": "2023-2024-1",\n')
        f.write('    "status": "active"\n')
        f.write('  }\n')
        f.write(']\n')
        f.write('```\n\n')
        
        # 课堂管理模块
        f.write('## 3. 课堂管理模块\n\n')
        f.write('### 3.1 获取班级列表\n\n')
        f.write('- **URL**: `/api/class/`\n')
        f.write('- **方法**: GET\n')
        f.write('- **描述**: 获取所有班级的列表\n')
        f.write('- **权限**: 仅管理员可查看所有班级，教师仅可查看教授的班级\n')
        f.write('- **请求参数**:\n')
        f.write('  - 无\n')
        f.write('- **响应示例**:\n')
        f.write('```json\n')
        f.write('[\n')
        f.write('  {\n')
        f.write('    "id": 1,\n')
        f.write('    "name": "计算机科学1班",\n')
        f.write('    "code": "CS-2023-1",\n')
        f.write('    "head_teacher": {\n')
        f.write('      "id": 2,\n')
        f.write('      "username": "teacher1",\n')
        f.write('      "name": "张教授"\n')
        f.write('    },\n')
        f.write('    "students_count": 30\n')
        f.write('  }\n')
        f.write(']\n')
        f.write('```\n\n')
        
        # 高级功能模块
        f.write('## 4. 高级功能模块\n\n')
        f.write('### 4.1 课程公告\n\n')
        f.write('- **URL**: `/api/advanced/course/{course_id}/announcements/`\n')
        f.write('- **方法**: GET\n')
        f.write('- **描述**: 获取课程公告列表\n')
        f.write('- **权限**: 教师和已选课学生可查看\n')
        f.write('- **请求参数**:\n')
        f.write('  - `course_id`: 课程ID (路径参数)\n')
        f.write('- **响应示例**:\n')
        f.write('```json\n')
        f.write('[\n')
        f.write('  {\n')
        f.write('    "id": 1,\n')
        f.write('    "title": "期末考试安排",\n')
        f.write('    "content": "期末考试将于6月20日举行...",\n')
        f.write('    "type": "warning",\n')
        f.write('    "course": 1,\n')
        f.write('    "publisher": {\n')
        f.write('      "id": 2,\n')
        f.write('      "username": "teacher1",\n')
        f.write('      "name": "张教授"\n')
        f.write('    },\n')
        f.write('    "created_at": "2023-06-01T10:00:00Z"\n')
        f.write('  }\n')
        f.write(']\n')
        f.write('```\n\n')
        
        # 人脸识别模块
        f.write('## 5. 人脸识别模块\n\n')
        f.write('### 5.1 人脸注册\n\n')
        f.write('- **URL**: `/api/face/register/`\n')
        f.write('- **方法**: POST\n')
        f.write('- **描述**: 注册用户人脸信息\n')
        f.write('- **请求参数**:\n')
        f.write('  - `image`: 人脸图像 (BASE64编码)\n')
        f.write('- **响应示例**:\n')
        f.write('```json\n')
        f.write('{\n')
        f.write('  "success": true,\n')
        f.write('  "message": "人脸注册成功"\n')
        f.write('}\n')
        f.write('```\n\n')

if __name__ == '__main__':
    generate_api_docs()
    print("API 文档已生成到 API_DOCUMENTATION.md") 