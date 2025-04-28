#!/bin/bash

echo "开始部署..."

# 进入项目目录
cd /home/wstier477/zwky_api

# 激活虚拟环境（虚拟环境可能位置不同，根据实际情况修改）
cd /home/wstier477/.virtualenvs/ENV_DIR/bin
source activate
cd /home/wstier477/zwky_api
 
# 拉取最新代码
echo "拉取最新代码..."
git pull

# 安装/更新依赖
echo "更新依赖..."
pip install -r requirements.txt

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate



# 设置文件权限
echo "设置文件权限..."
chmod 664 db.sqlite3
mkdir -p logs
chmod -R 775 logs

# 重启 web 应用
echo "重启 web 应用..."
touch /var/www/wstier477_pythonanywhere_com_wsgi.py

echo "部署完成!" 