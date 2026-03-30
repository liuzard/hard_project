# Bully Center API 接口文档

## 项目简介

Bully Center 是一个音频管理系统，提供音频文件上传、存储、查询等功能。音频文件存储在本地服务器，元数据存储在 MySQL 数据库。

## 基础信息

| 项目 | 内容 |
|------|------|
| 服务地址 | `http://localhost:8080` |
| 接口前缀 | `/audio` |
| 数据格式 | JSON |
| 编码格式 | UTF-8 |

## 响应格式

所有接口返回统一格式：

```json
{
    "code": 0,          // 状态码：0-成功，其他-失败
    "message": "success", // 提示信息
    "data": {}          // 业务数据
}
```

## 音频类型枚举

| 枚举值 | 说明 |
|--------|------|
| normal | 正常音频 |
| bully | 霸凌音频 |

**说明**：
- 音频类型使用枚举类 `AudioTypeEnum` 进行校验
- 无效的音频类型会返回错误码 1003
- 不传时默认为 `normal`

## 接口列表

### 1. 上传音频文件

**接口地址**：`POST /audio/upload/file`

**Content-Type**：`multipart/form-data`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | File | 是 | 音频文件（mp3, wav, m4a 等） |
| textContent | String | 否 | 音频文字内容 |
| audioType | String | 否 | 音频类型：normal-正常，bully-霸凌，默认 normal |
| duration | Integer | 否 | 音频时长（秒） |

**请求示例**：

```http
POST /audio/upload/file
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="test.mp3"
Content-Type: audio/mpeg

[二进制文件内容]
------WebKitFormBoundary
Content-Disposition: form-data; name="textContent"

这是一段测试音频的文字内容
------WebKitFormBoundary
Content-Disposition: form-data; name="audioType"

bully
------WebKitFormBoundary
Content-Disposition: form-data; name="duration"

60
------WebKitFormBoundary--
```

**响应示例**：

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "audioId": "audio_a1b2c3d4e5f6g7h8",
        "audioUrl": "http://localhost:8080/files/audio/20240328/a1b2c3d4e5f6g7h8.mp3",
        "message": "上传成功"
    }
}
```

---

### 2. 上传音频信息（URL方式）

**接口地址**：`POST /audio/upload`

**Content-Type**：`application/json`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audioUrl | String | 是 | 音频文件URL |
| textContent | String | 否 | 音频文字内容 |
| audioType | String | 否 | 音频类型：normal-正常，bully-霸凌，默认 normal |
| duration | Integer | 否 | 音频时长（秒） |
| fileSize | Long | 否 | 文件大小（字节） |

**请求示例**：

```json
{
    "audioUrl": "https://example.com/audio/test.mp3",
    "textContent": "这是一段测试音频的文字内容",
    "audioType": "bully",
    "duration": 60,
    "fileSize": 1024000
}
```

**响应示例**：

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "audioId": "audio_x9y8z7w6v5u4t3s2",
        "message": "上传成功"
    }
}
```

---

### 3. 根据ID查询音频

**接口地址**：`POST /audio/get`

**Content-Type**：`application/json`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audioId | String | 是 | 音频ID |

**请求示例**：

```json
{
    "audioId": "audio_a1b2c3d4e5f6g7h8"
}
```

**响应示例**：

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "audioId": "audio_a1b2c3d4e5f6g7h8",
        "audioUrl": "http://localhost:8080/files/audio/20240328/a1b2c3d4e5f6g7h8.mp3",
        "textContent": "这是一段测试音频的文字内容",
        "audioType": "bully",
        "duration": 60,
        "fileSize": 1024000,
        "createTime": "2024-03-28 10:30:00",
        "updateTime": "2024-03-28 10:30:00"
    }
}
```

---

### 4. 分页查询音频列表

**接口地址**：`POST /audio/list`

**Content-Type**：`application/json`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|--------|
| audioType | String | 否 | 音频类型筛选：normal-正常，bully-霸凌，不传则查询全部 | - |
| pageNum | Integer | 否 | 页码 | 1 |
| pageSize | Integer | 否 | 每页大小 | 10 |

**请求示例**：

```json
{
    "audioType": "bully",
    "pageNum": 1,
    "pageSize": 10
}
```

**响应示例**：

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "audioList": [
            {
                "audioId": "audio_a1b2c3d4e5f6g7h8",
                "audioUrl": "http://localhost:8080/files/audio/20240328/a1b2c3d4e5f6g7h8.mp3",
                "textContent": "第一段音频",
                "audioType": "bully",
                "duration": 60,
                "fileSize": 1024000,
                "createTime": "2024-03-28 10:30:00",
                "updateTime": "2024-03-28 10:30:00"
            },
            {
                "audioId": "audio_x9y8z7w6v5u4t3s2",
                "audioUrl": "http://localhost:8080/files/audio/20240328/x9y8z7w6v5u4t3s2.mp3",
                "textContent": "第二段音频",
                "audioType": "bully",
                "duration": 120,
                "fileSize": 2048000,
                "createTime": "2024-03-28 09:15:00",
                "updateTime": "2024-03-28 09:15:00"
            }
        ],
        "totalCount": 2,
        "pageNum": 1,
        "pageSize": 10
    }
}
```

---

### 5. 搜索音频

**接口地址**：`POST /audio/search`

**Content-Type**：`application/json`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|--------|
| keyword | String | 否 | 搜索关键词（匹配文字内容） | - |
| audioType | String | 否 | 音频类型筛选：normal-正常，bully-霸凌，不传则查询全部 | - |
| pageNum | Integer | 否 | 页码 | 1 |
| pageSize | Integer | 否 | 每页大小 | 10 |

**请求示例**：

```json
{
    "keyword": "测试",
    "audioType": "bully",
    "pageNum": 1,
    "pageSize": 10
}
```

**响应示例**：

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "audioList": [
            {
                "audioId": "audio_a1b2c3d4e5f6g7h8",
                "audioUrl": "http://localhost:8080/files/audio/20240328/a1b2c3d4e5f6g7h8.mp3",
                "textContent": "这是一段测试音频的文字内容",
                "audioType": "bully",
                "duration": 60,
                "fileSize": 1024000,
                "createTime": "2024-03-28 10:30:00",
                "updateTime": "2024-03-28 10:30:00"
            }
        ],
        "totalCount": 1,
        "pageNum": 1,
        "pageSize": 10
    }
}
```

---

### 6. 删除音频

**接口地址**：`POST /audio/delete`

**Content-Type**：`application/json`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audioId | String | 是 | 音频ID |

**请求示例**：

```json
{
    "audioId": "audio_a1b2c3d4e5f6g7h8"
}
```

**响应示例**：

```json
{
    "code": 0,
    "message": "success",
    "data": "删除成功"
}
```

**说明**：删除音频时会同时删除本地存储的音频文件和数据库记录。

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数缺失或无效 |
| 1002 | 音频不存在 |
| 1003 | 音频类型无效（只能是 normal 或 bully） |
| 500 | 服务器内部错误 |

## 数据模型

### AudioData（音频数据）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| audioId | String | 音频唯一标识 |
| audioUrl | String | 音频文件访问URL |
| textContent | String | 音频文字内容 |
| audioType | String | 音频类型：normal-正常，bully-霸凌 |
| duration | Integer | 音频时长（秒） |
| fileSize | Long | 文件大小（字节） |
| createTime | DateTime | 创建时间 |
| updateTime | DateTime | 更新时间 |

## 文件存储说明

### 存储路径配置

在 `application.yml` 中配置：

```yaml
file:
  storage:
    path-prefix: F:/bully-center/files    # 本地存储根路径（可修改）
    audio-subdir: audio                    # 音频子目录
    url-prefix: http://localhost:8080/files # 访问URL前缀
```

**注意**：`path-prefix` 是本地文件存储路径的前缀，可根据服务器环境修改。

### 文件存储结构

```
F:/bully-center/files/
└── audio/                          # 音频文件目录
    └── 20240328/                   # 按日期分子目录
        ├── a1b2c3d4e5f6g7h8.mp3
        └── x9y8z7w6v5u4t3s2.wav
```

### 访问方式

音频文件上传后会返回访问URL，可直接通过浏览器访问：

```
http://localhost:8080/files/audio/20240328/a1b2c3d4e5f6g7h8.mp3
```

## 数据库表结构

### audio_data（音频数据表）

```sql
CREATE TABLE audio_data (
    audio_id VARCHAR(32) NOT NULL COMMENT '音频ID',
    audio_url VARCHAR(500) NOT NULL COMMENT '音频文件URL',
    text_content TEXT COMMENT '音频文字内容',
    audio_type VARCHAR(20) DEFAULT 'normal' COMMENT '音频类型：normal-正常，bully-霸凌',
    duration INT DEFAULT 0 COMMENT '音频时长（秒）',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (audio_id),
    INDEX idx_create_time (create_time),
    INDEX idx_audio_type (audio_type),
    INDEX idx_text_content (text_content(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='音频数据表';
```

## 技术栈

- **框架**：Spring Boot 2.0.4
- **数据库**：MySQL 5.7
- **ORM**：MyBatis
- **连接池**：Druid
- **文档**：Swagger 2.9.2

## 数据库字段映射说明

项目使用 MyBatis 的驼峰命名自动转换功能，数据库下划线字段名（如 `audio_id`）会自动映射为 Java 驼峰字段名（如 `audioId`）。

配置方式：
```java
// SqlConfigBean.java
configuration.setMapUnderscoreToCamelCase(true);
```

## Swagger 接口文档

启动项目后访问：

```
http://localhost:8080/swagger-ui.html
```

## 更新日志

### 2025-03-28
- 新增音频类型枚举 `AudioTypeEnum`（normal/bully）
- 新增音频类型校验，无效类型返回错误码 1003
- 使用 `SqlConfigBean` 配置 MyBatis 驼峰命名自动转换
- 文件存储路径支持配置化
