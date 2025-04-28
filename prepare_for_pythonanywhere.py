#!/usr/bin/env python
"""
准备PythonAnywhere部署文件
此脚本将创建一个zip文件，包含部署到PythonAnywhere所需的所有文件
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_deployment_zip():
    """创建部署用的zip文件"""
    print("准备创建部署文件...")
    
    # 创建临时目录
    temp_dir = Path("deploy_temp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    # 要包含的文件和目录
    include_paths = [
        "manage.py",
        "requirements.txt",
        "zwky_api",
        "user_management",
        "pythonanywhere_wsgi.py",
        "static",
        "media",
    ]
    
    # 要排除的文件和目录
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".git",
        ".gitignore",
        ".gitattributes",
        "db.sqlite3",
        "venv",
        "deploy_temp",
    ]
    
    # 复制文件到临时目录
    for path in include_paths:
        src_path = Path(path)
        if not src_path.exists():
            if path in ["static", "media"]:
                # 创建空目录
                (temp_dir / path).mkdir(exist_ok=True)
                print(f"创建空目录: {path}")
                continue
            else:
                print(f"警告: {path} 不存在，将被跳过")
                continue
        
        dst_path = temp_dir / path
        
        if src_path.is_dir():
            print(f"复制目录: {path}")
            shutil.copytree(
                src_path, 
                dst_path,
                ignore=shutil.ignore_patterns(*exclude_patterns)
            )
        else:
            print(f"复制文件: {path}")
            shutil.copy2(src_path, dst_path)
    
    # 创建zip文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"zwky_api_deploy_{timestamp}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    # 清理临时目录
    shutil.rmtree(temp_dir)
    
    print(f"\n部署文件已创建: {zip_filename}")
    print(f"文件大小: {os.path.getsize(zip_filename) / 1024:.2f} KB")
    print("\n请将此文件上传到PythonAnywhere，然后按照manual_deploy_steps.md中的步骤进行部署。")
    
    return zip_filename

def main():
    """主函数"""
    print("开始准备PythonAnywhere部署文件...\n")
    
    # 检查是否在项目根目录
    if not Path("manage.py").exists() or not Path("zwky_api").is_dir():
        print("错误: 请在项目根目录中运行此脚本")
        return 1
    
    try:
        zip_file = create_deployment_zip()
        print(f"\n✅ 部署文件准备完成: {zip_file}")
        return 0
    except Exception as e:
        print(f"\n❌ 创建部署文件时出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 