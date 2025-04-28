#!/usr/bin/env python
"""
PythonAnywhere设置脚本
在PythonAnywhere上运行此脚本，以自动设置项目环境
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """运行命令并打印输出"""
    print(f"执行: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"错误: {result.stderr}")
    return result.returncode == 0

def setup_virtualenv():
    """设置虚拟环境"""
    print("\n设置虚拟环境...")
    
    # 检查是否已存在虚拟环境
    venv_dir = Path("venv")
    if venv_dir.exists():
        print("虚拟环境已存在，跳过创建")
    else:
        print("创建虚拟环境...")
        if not run_command("python3 -m venv venv"):
            return False
    
    # 安装依赖
    print("安装依赖...")
    if not run_command("source venv/bin/activate && pip install --upgrade pip"):
        return False
    
    if not run_command("source venv/bin/activate && pip install -r requirements.txt"):
        return False
    
    return True

def collect_static():
    """收集静态文件"""
    print("\n收集静态文件...")
    
    # 创建static目录（如果不存在）
    static_dir = Path("static")
    if not static_dir.exists():
        static_dir.mkdir()
    
    # 收集静态文件
    return run_command("source venv/bin/activate && python manage.py collectstatic --noinput --settings=zwky_api.pythonanywhere_settings")

def apply_migrations():
    """应用数据库迁移"""
    print("\n应用数据库迁移...")
    return run_command("source venv/bin/activate && python manage.py migrate --settings=zwky_api.pythonanywhere_settings")

def create_superuser():
    """创建超级用户"""
    print("\n是否要创建超级用户？(y/n)")
    choice = input().lower()
    if choice == 'y':
        return run_command("source venv/bin/activate && python manage.py createsuperuser --settings=zwky_api.pythonanywhere_settings")
    return True

def print_next_steps():
    """打印下一步操作"""
    username = os.path.basename(os.path.expanduser("~"))
    project_path = os.getcwd()
    
    print("\n" + "="*50)
    print("设置完成！接下来的步骤：")
    print("="*50)
    print("\n1. 配置Web应用")
    print("   - 访问 https://www.pythonanywhere.com/user/{}/webapps/".format(username))
    print("   - 点击您的Web应用或创建一个新的Web应用")
    
    print("\n2. 配置WSGI文件")
    print("   - 点击WSGI配置文件链接")
    print("   - 删除文件中的所有内容，并粘贴pythonanywhere_wsgi.py的内容")
    print("   - 确保路径设置正确：{}".format(project_path))
    
    print("\n3. 配置虚拟环境")
    print("   - 在'Virtualenv'部分，输入：{}/venv".format(project_path))
    
    print("\n4. 配置静态文件")
    print("   - 在'Static files'部分，添加：")
    print("     URL: /static/")
    print("     Directory: {}/static".format(project_path))
    
    print("\n5. 重新加载Web应用")
    print("   - 点击'Reload'按钮")
    
    print("\n6. 访问您的网站")
    print("   - 访问 https://{}.pythonanywhere.com".format(username))
    print("\n祝您部署成功！")

def main():
    """主函数"""
    print("开始在PythonAnywhere上设置zwky_api项目...\n")
    
    # 检查是否在项目根目录
    if not Path("manage.py").exists() or not Path("zwky_api").is_dir():
        print("错误: 请在项目根目录中运行此脚本")
        return 1
    
    # 检查是否在PythonAnywhere上运行
    if not "PYTHONANYWHERE_DOMAIN" in os.environ and not "pythonanywhere" in os.getcwd():
        print("警告: 此脚本设计用于在PythonAnywhere上运行")
        print("是否继续？(y/n)")
        if input().lower() != 'y':
            return 1
    
    # 设置虚拟环境
    if not setup_virtualenv():
        print("设置虚拟环境失败")
        return 1
    
    # 收集静态文件
    if not collect_static():
        print("收集静态文件失败")
        return 1
    
    # 应用数据库迁移
    if not apply_migrations():
        print("应用数据库迁移失败")
        return 1
    
    # 创建超级用户
    create_superuser()
    
    # 打印下一步操作
    print_next_steps()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 