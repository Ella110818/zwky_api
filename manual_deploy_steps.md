# zwky_api 手动部署步骤

由于PythonAnywhere的免费账户不支持SSH访问，您需要按照以下步骤手动部署您的应用：

## 1. 准备本地代码

确保您的本地代码已经准备好部署：

```bash
# 运行部署前检查脚本
python prepare_for_deployment.py

# 如果使用Git，提交所有更改
git add .
git commit -m "准备部署到PythonAnywhere"
git push
```

## 2. 登录PythonAnywhere

访问 [PythonAnywhere](https://www.pythonanywhere.com/) 并登录到您的账户。

## 3. 创建Web应用

如果您还没有创建Web应用：

1. 点击"Web"选项卡
2. 点击"Add a new web app"
3. 选择您的域名（通常是`wstier477.pythonanywhere.com`）
4. 选择"Manual configuration"
5. 选择Python版本（推荐Python 3.8或更高版本）

## 4. 上传代码

有两种方式上传您的代码：

### 方式1：使用Git（如果PythonAnywhere上已安装Git）

1. 打开PythonAnywhere的Bash控制台
2. 运行以下命令：

```bash
# 克隆仓库
git clone https://github.com/wstier477/zwky_api.git

# 或者如果已经克隆，则更新
cd zwky_api
git pull
```

### 方式2：直接上传文件

1. 在PythonAnywhere的"Files"选项卡中，创建一个`zwky_api`目录
2. 使用上传功能上传您的项目文件
3. 或者使用PythonAnywhere的Bash控制台，通过`wget`下载您的项目压缩包：

```bash
wget https://github.com/wstier477/zwky_api/archive/main.zip
unzip main.zip
mv zwky_api-main zwky_api
```

## 5. 设置虚拟环境

在PythonAnywhere的Bash控制台中：

```bash
# 创建虚拟环境
cd ~/zwky_api
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. 配置Django设置

确保`zwky_api/pythonanywhere_settings.py`文件中的设置正确：

1. 检查`ALLOWED_HOSTS`是否包含您的PythonAnywhere域名
2. 如果使用MySQL数据库，配置数据库设置

## 7. 收集静态文件

```bash
python manage.py collectstatic --noinput --settings=zwky_api.pythonanywhere_settings
```

## 8. 应用数据库迁移

```bash
python manage.py migrate --settings=zwky_api.pythonanywhere_settings
```

## 9. 配置WSGI文件

1. 在Web应用配置页面，找到"Code"部分
2. 点击WSGI配置文件链接（通常是`/var/www/wstier477_pythonanywhere_com_wsgi.py`）
3. 删除文件中的所有内容，并粘贴以下内容：

```python
import os
import sys

# 添加项目路径到系统路径
path = '/home/wstier477/zwky_api'
if path not in sys.path:
    sys.path.append(path)

# 设置Django设置模块
os.environ['DJANGO_SETTINGS_MODULE'] = 'zwky_api.pythonanywhere_settings'

# 导入Django的WSGI应用
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 10. 配置虚拟环境路径

在Web应用配置页面的"Virtualenv"部分：

1. 输入您的虚拟环境路径：`/home/wstier477/zwky_api/venv`
2. 点击"Virtualenv"部分的保存按钮

## 11. 配置静态文件

在Web应用配置页面的"Static files"部分：

1. 添加一个新条目：
   - URL: `/static/`
   - Directory: `/home/wstier477/zwky_api/static/`
2. 如果需要媒体文件，再添加一个条目：
   - URL: `/media/`
   - Directory: `/home/wstier477/zwky_api/media/`
3. 点击"Static files"部分的保存按钮

## 12. 重新加载Web应用

点击Web应用配置页面顶部的"Reload"按钮。

## 13. 检查部署

访问您的PythonAnywhere域名（`wstier477.pythonanywhere.com`）检查应用是否正常运行。

如果遇到问题，请查看PythonAnywhere的错误日志（在Web应用配置页面的"Logs"部分）。 