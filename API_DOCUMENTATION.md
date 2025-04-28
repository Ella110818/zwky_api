# zwky_api 接口文档

## 目录

1. [概述](#概述)
2. [接口规范](#接口规范)
3. [认证机制](#认证机制)
4. [错误码](#错误码)
5. [接口详情](#接口详情)
   - [用户注册](#用户注册)
   - [用户登录](#用户登录)
   - [退出登录](#退出登录)
   - [刷新令牌](#刷新令牌)

## 概述

本文档描述了zwky_api项目的REST API接口。该API提供用户管理功能，包括注册、登录、退出登录等操作。

- **基础URL**: `/api`
- **数据格式**: JSON
- **认证方式**: JWT (JSON Web Token)

## 接口规范

### 请求格式

所有请求应使用JSON格式的请求体，并设置以下请求头：

```
Content-Type: application/json
```

对于需要认证的接口，还需要添加以下请求头：

```
Authorization: Bearer {access_token}
```

### 响应格式

所有API响应均使用统一的JSON格式：

```json
{
  "code": 200,       // 状态码，200表示成功，其他值表示错误
  "message": "成功",  // 状态描述
  "data": {}         // 响应数据，可能为null
}
```

## 认证机制

本API使用JWT (JSON Web Token) 进行认证。用户登录成功后，服务器会返回一个访问令牌（access_token）。客户端需要在后续请求中通过Authorization请求头携带此令牌。

令牌有效期为1天，过期后需要使用刷新令牌（refresh_token）获取新的访问令牌。

## 错误码

| 错误码 | 描述 |
|-------|------|
| 10000 | 用户不存在 |
| 10001 | 用户名或密码错误 |
| 10002 | 用户名已存在 |
| 10003 | 邮箱已存在 |
| 10004 | 旧密码错误 |
| 400   | 请求参数错误 |
| 401   | 未认证或认证失败 |
| 403   | 权限不足 |
| 404   | 资源不存在 |
| 500   | 服务器内部错误 |

## 接口详情

### 用户注册

注册新用户。

- **URL**: `/api/register/`
- **方法**: `POST`
- **认证要求**: 无

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| username | string | 是 | 用户名，唯一 |
| password | string | 是 | 密码 |
| email | string | 是 | 邮箱，唯一 |
| role | string | 是 | 角色，可选值：`student`（学生）、`teacher`（教师） |
| name | string | 是 | 真实姓名 |

**请求示例**:

```json
{
  "username": "testuser",
  "password": "Test@123456",
  "email": "testuser@example.com",
  "role": "student",
  "name": "测试用户"
}
```

**成功响应**:

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "userId": "1",
    "username": "testuser"
  }
}
```

**错误响应**:

- 用户名已存在:

```json
{
  "code": 10002,
  "message": "用户名已存在",
  "data": null
}
```

- 邮箱已存在:

```json
{
  "code": 10003,
  "message": "邮箱已存在",
  "data": null
}
```

### 用户登录

用户登录并获取访问令牌。

- **URL**: `/api/login/`
- **方法**: `POST`
- **认证要求**: 无

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例**:

```json
{
  "username": "testuser",
  "password": "Test@123456"
}
```

**成功响应**:

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "userId": "1",
    "username": "testuser",
    "role": "student",
    "avatar": null
  }
}
```

**错误响应**:

- 用户名或密码错误:

```json
{
  "code": 10001,
  "message": "用户名或密码错误",
  "data": null
}
```

### 退出登录

退出登录（由于JWT是无状态的，此接口仅作为前端清除token的标志）。

- **URL**: `/api/logout/`
- **方法**: `POST`
- **认证要求**: 需要JWT认证

**请求参数**: 无

**请求头**:

```
Authorization: Bearer {access_token}
```

**成功响应**:

```json
{
  "code": 200,
  "message": "退出成功",
  "data": null
}
```

### 刷新令牌

使用刷新令牌获取新的访问令牌。

- **URL**: `/api/token/refresh/`
- **方法**: `POST`
- **认证要求**: 无

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| refresh | string | 是 | 刷新令牌 |

**请求示例**:

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**成功响应**:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## 用户模型

用户模型包含以下字段：

| 字段名 | 类型 | 描述 |
|-------|------|------|
| id | integer | 用户ID，自动生成 |
| username | string | 用户名，唯一 |
| email | string | 邮箱，唯一 |
| phone | string | 电话号码，可选 |
| role | string | 角色，可选值：`student`（学生）、`teacher`（教师） |
| avatar | string | 头像URL，可选 |
| first_name | string | 真实姓名 |
| create_time | datetime | 创建时间，自动生成 |
| update_time | datetime | 更新时间，自动更新 |

## 开发与测试

项目提供了测试脚本和测试页面，可用于API测试：

1. 测试脚本: `test_api.py`
2. 测试页面: `test_api.html`

测试脚本可以通过命令行运行：

```bash
python test_api.py
```

测试页面可以在浏览器中打开，提供了用户友好的界面进行API测试。

## 部署说明

项目可以部署到PythonAnywhere平台，详细部署步骤请参考项目中的`README_DEPLOY.md`文件。 