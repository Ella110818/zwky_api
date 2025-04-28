#!/bin/bash
# 部署脚本，用于将zwky_api项目部署到PythonAnywhere

# 设置变量
USERNAME="wstier477"  # 替换为您的PythonAnywhere用户名
PROJECT_NAME="zwky_api"
GITHUB_REPO="https://github.com/wstier477/zwky_api.git"  # 如果使用GitHub，请替换为您的仓库URL

echo "开始部署 $PROJECT_NAME 到 PythonAnywhere..."

# 登录到PythonAnywhere
echo "请使用您的PythonAnywhere凭据登录..."
ssh $USERNAME@ssh.pythonanywhere.com << EOF

  # 创建或更新项目目录
  echo "设置项目目录..."
  if [ -d "$PROJECT_NAME" ]; then
    echo "项目目录已存在，更新代码..."
    cd $PROJECT_NAME
    
    # 如果使用Git
    if [ -d ".git" ]; then
      git pull
    else
      # 如果不使用Git，则备份并重新克隆
      cd ..
      mv $PROJECT_NAME ${PROJECT_NAME}_backup_\$(date +%Y%m%d_%H%M%S)
      git clone $GITHUB_REPO $PROJECT_NAME
      cd $PROJECT_NAME
    fi
  else
    echo "创建新项目目录并克隆代码..."
    # 如果使用Git
    git clone $GITHUB_REPO $PROJECT_NAME
    cd $PROJECT_NAME
  fi

  # 创建虚拟环境（如果不存在）
  echo "设置虚拟环境..."
  if [ ! -d "venv" ]; then
    python3 -m venv venv
  fi
  
  # 激活虚拟环境并安装依赖
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  
  # 收集静态文件
  echo "收集静态文件..."
  python manage.py collectstatic --noinput --settings=zwky_api.pythonanywhere_settings
  
  # 应用数据库迁移
  echo "应用数据库迁移..."
  python manage.py migrate --settings=zwky_api.pythonanywhere_settings
  
  # 重新加载Web应用
  echo "重新加载Web应用..."
  touch /var/www/$USERNAME\_pythonanywhere_com_wsgi.py
  
  echo "部署完成！"
EOF

echo "部署脚本执行完毕！"
echo "请确保您已在PythonAnywhere的Web选项卡中配置了正确的WSGI文件路径："
echo "/var/www/$USERNAME\_pythonanywhere_com_wsgi.py"
echo "并且源代码路径设置为："
echo "/home/$USERNAME/$PROJECT_NAME"
echo "虚拟环境路径设置为："
echo "/home/$USERNAME/$PROJECT_NAME/venv" 