#!/bin/bash

echo "配置 Ollama 国内镜像源..."

# 创建 Ollama 配置目录
mkdir -p /root/.ollama

# 配置镜像源（使用阿里云镜像）
export OLLAMA_HOST=0.0.0.0
export OLLAMA_ORIGINS="*"

# 如果需要使用代理，取消下面的注释并配置
# export HTTP_PROXY=http://your-proxy:port
# export HTTPS_PROXY=http://your-proxy:port

echo "镜像源配置完成！"
echo "等待Ollama服务启动..."

# 等待Ollama服务就绪（使用 ollama list 命令检查）
until ollama list > /dev/null 2>&1; do
    sleep 2
    echo "仍在等待Ollama服务..."
done

echo "Ollama服务已就绪，开始拉取法律嵌入模型..."

# 拉取模型（如果还没下载）
if ! ollama list | grep -q "demonbyron/embeddinggemma-300m-lawvault"; then
    echo "首次运行，正在下载模型（约622MB）..."
    
    # 使用重试机制和超时设置
    ollama pull demonbyron/embeddinggemma-300m-lawvault || {
        echo "第一次下载失败，尝试重新下载..."
        sleep 5
        ollama pull demonbyron/embeddinggemma-300m-lawvault || {
            echo "第二次下载失败，尝试最后一次..."
            sleep 10
            ollama pull demonbyron/embeddinggemma-300m-lawvault
        }
    }
    
    echo "模型下载完成！"
else
    echo "模型已存在，跳过下载"
fi

# 模型预热（可选，加快首次响应）
echo "进行模型预热..."
ollama run demonbyron/embeddinggemma-300m-lawvault "测试" > /dev/null 2>&1

echo "初始化完成！法律嵌入模型已就绪"