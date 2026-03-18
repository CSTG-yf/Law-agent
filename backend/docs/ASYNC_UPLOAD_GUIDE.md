# 异步文档上传接口使用说明

## 概述

文档上传接口已优化为异步处理模式，使用Celery + Redis实现后台任务队列。用户上传文档后可以立即获得任务ID，无需等待文档处理完成。

## 主要优势

1. **快速响应**：上传文档后立即返回任务ID，响应时间从几分钟缩短到几秒
2. **避免超时**：大文件处理不会导致HTTP请求超时
3. **进度查询**：可以实时查询任务处理进度
4. **结果获取**：任务完成后可以获取详细的处理结果

## 启动服务

### 1. 启动Docker服务

```bash
cd f:\Law-agent
docker-compose up -d
```

这将启动以下服务：
- Ollama（向量嵌入）
- Neo4j（图数据库）
- ChromaDB（向量数据库）
- **Redis（任务队列）**

### 2. 启动FastAPI服务

```bash
cd f:\Law-agent\backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 启动Celery Worker

**Windows:**
```bash
cd f:\Law-agent\backend
scripts\start-celery.bat
```

**Linux/Mac:**
```bash
cd f:\Law-agent\backend
bash scripts/start-celery.sh
```

## API接口说明

### 1. 上传文档（异步）

**接口**: `POST /api/v1/rag/upload`

**请求示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/upload" \
  -F "file=@your_document.pdf" \
  -F "metadata={\"category\": \"合同法\", \"author\": \"张三\"}"
```

**响应示例**:
```json
{
  "success": true,
  "message": "文档上传成功，正在后台处理",
  "code": 202,
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**说明**:
- 返回HTTP状态码202（Accepted）
- `task_id`用于后续查询任务状态和结果
- 文档正在后台处理中

### 2. 查询任务状态

**接口**: `GET /api/v1/rag/task/{task_id}`

**请求示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/task/550e8400-e29b-41d4-a716-446655440000"
```

**响应示例（处理中）**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 30,
  "message": "计算文件哈希"
}
```

**响应示例（已完成）**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "处理完成"
}
```

**响应示例（失败）**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "文件内容为空或无法提取文本"
}
```

**状态说明**:
- `pending`: 任务等待中
- `processing`: 处理中（包含进度信息）
- `completed`: 处理完成
- `failed`: 处理失败

### 3. 获取任务结果

**接口**: `GET /api/v1/rag/task/{task_id}/result`

**请求示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/task/550e8400-e29b-41d4-a716-446655440000/result"
```

**响应示例**:
```json
{
  "success": true,
  "message": "文档处理并存储成功",
  "code": 200,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "legal_document.pdf",
  "file_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "chunks_count": 15,
  "document_ids": [
    "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6_chunk_0",
    "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6_chunk_1"
  ]
}
```

**说明**:
- 只有任务状态为`completed`时才能获取结果
- 包含完整的文档处理信息
- 可以用于后续的文档查询和删除操作

### 4. 删除文档（异步）

**接口**: `DELETE /api/v1/rag/document`

**请求示例**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/rag/document" \
  -H "Content-Type: application/json" \
  -d "{\"file_hash\": \"a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6\"}"
```

**响应示例**:
```json
{
  "success": true,
  "message": "删除任务已提交，正在后台处理",
  "code": 202,
  "task_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**说明**:
- 删除操作也是异步的
- 返回任务ID用于查询删除进度

## 完整使用流程

### 示例1：上传并查询文档

```bash
# 1. 上传文档
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/rag/upload" \
  -F "file=@legal_document.pdf")

# 提取task_id
TASK_ID=$(echo $UPLOAD_RESPONSE | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

echo "任务ID: $TASK_ID"

# 2. 轮询任务状态
while true; do
  STATUS_RESPONSE=$(curl -s "http://localhost:8000/api/v1/rag/task/$TASK_ID")
  STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  
  echo "当前状态: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 2
done

# 3. 获取处理结果
curl -s "http://localhost:8000/api/v1/rag/task/$TASK_ID/result"
```

### 示例2：使用Apifox测试

1. 导入API文档到Apifox
2. 测试上传接口，获取task_id
3. 使用task_id测试状态查询接口
4. 等待任务完成后测试结果获取接口

## 错误处理

### 常见错误

1. **任务不存在**
```json
{
  "detail": "查询任务状态失败: Task with ID xxx not found"
}
```

2. **任务尚未完成**
```json
{
  "success": false,
  "message": "任务尚未完成，当前状态: processing",
  "code": 400,
  "task_id": "xxx"
}
```

3. **Celery Worker未启动**
如果Celery Worker未启动，任务将一直处于`pending`状态。

## 监控和调试

### 查看Celery Worker日志

启动Celery Worker时会输出详细日志，包括：
- 任务接收
- 处理进度
- 成功/失败状态

### 查看Redis状态

```bash
docker exec legal-redis redis-cli ping
# 应该返回 PONG
```

### 查看任务队列

```bash
docker exec legal-redis redis-cli llen celery
# 查看等待处理的任务数量
```

## 性能优化建议

1. **Worker并发数**：根据服务器配置调整`--concurrency`参数
2. **任务超时**：调整`--time-limit`和`--soft-time-limit`参数
3. **Redis持久化**：确保Redis数据正确挂载到宿主机
4. **错误重试**：可以在Celery配置中添加任务重试机制

## 注意事项

1. **确保Celery Worker运行**：上传文档前必须启动Celery Worker
2. **任务ID保存**：妥善保存返回的task_id，用于后续查询
3. **轮询间隔**：建议2-5秒轮询一次任务状态，避免频繁请求
4. **超时处理**：设置合理的超时时间，避免无限等待
5. **错误处理**：处理任务失败的情况，提供友好的错误提示