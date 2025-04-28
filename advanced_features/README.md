# 高级功能模块

本模块实现了学生课程信息系统的高级功能，根据`api-documentation-new.md`接口文档的要求。

## 功能列表

1. 课程公告管理
   - 获取课程公告列表
   - 发布课程公告

2. 作业与考试管理
   - 获取作业和考试列表
   - 发布作业或考试

3. 课程分组管理
   - 获取课程分组列表
   - 创建或更新分组
   - 自动分组

## 数据模型

本模块定义了以下数据模型：

- `CourseAnnouncement`: 课程公告
- `Assignment`: 作业和考试
- `AssignmentSubmission`: 作业提交
- `CourseGroup`: 课程分组

## API接口

### 1. 课程公告相关接口

#### 1.1 获取课程公告列表

- **URL**: `/api/courses/{course_id}/announcements/`
- **方法**: GET
- **描述**: 获取课程的所有公告
- **权限**: 需要认证，必须是课程的教师或学生

查询参数:
- `type`: 公告类型，可选值：'info', 'warning', 'danger'
- `page`: 页码，默认1
- `size`: 每页条数，默认10

#### 1.2 发布课程公告

- **URL**: `/api/courses/{course_id}/announcements/`
- **方法**: POST
- **描述**: 为课程发布新公告
- **权限**: 需要认证，必须是课程的教师

请求参数:
- `title`: 公告标题
- `content`: 公告内容
- `type`: 公告类型：'info'(普通),'warning'(重要),'danger'(紧急)

### 2. 作业与考试相关接口

#### 2.1 获取作业和考试列表

- **URL**: `/api/courses/{course_id}/assignments/`
- **方法**: GET
- **描述**: 获取课程的所有作业和考试
- **权限**: 需要认证，必须是课程的教师或学生

查询参数:
- `type`: 类型筛选，可选值：'homework'(作业),'exam'(考试)
- `status`: 状态筛选，可选值：'未开始','进行中','已截止'
- `page`: 页码，默认1
- `size`: 每页条数，默认10

#### 2.2 发布作业/考试

- **URL**: `/api/courses/{course_id}/assignments/`
- **方法**: POST
- **描述**: 发布新作业或考试
- **权限**: 需要认证，必须是课程的教师

请求参数:
- `title`: 标题
- `type`: 类型：'homework'或'exam'
- `description`: 描述
- `start_time`: 开始时间
- `deadline`: 截止时间
- `full_score`: 总分

### 3. 分组管理相关接口

#### 3.1 获取课程分组列表

- **URL**: `/api/courses/{course_id}/groups/`
- **方法**: GET
- **描述**: 获取课程的所有分组信息
- **权限**: 需要认证，必须是课程的教师或学生

#### 3.2 创建/更新分组

- **URL**: `/api/courses/{course_id}/groups/`
- **方法**: POST
- **描述**: 创建新分组或更新现有分组
- **权限**: 需要认证，必须是课程的教师

请求参数:
- `name`: 分组名称
- `studentIds`: 学生ID列表

#### 3.3 自动分组

- **URL**: `/api/courses/{course_id}/groups/auto`
- **方法**: POST
- **描述**: 自动将学生分配到指定数量的分组中
- **权限**: 需要认证，必须是课程的教师

请求参数:
- `groupCount`: 分组数量
- `method`: 分组方式：'random'(随机),'average'(平均)

## 部署说明

1. 确保项目依赖已安装:
   ```
   pip install djangorestframework djangorestframework-simplejwt django-cors-headers
   ```

2. 在项目settings.py中添加应用:
   ```python
   INSTALLED_APPS = [
       # ...
       'advanced_features',
   ]
   ```

3. 执行数据库迁移:
   ```
   python manage.py makemigrations advanced_features
   python manage.py migrate advanced_features
   ```

4. 在主URL配置中添加URL路由:
   ```python
   urlpatterns = [
       # ...
       path('api/', include([
           # ...
           path('', include('advanced_features.urls')),
       ])),
   ]
   ``` 