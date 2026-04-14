import { request } from '../utils/request'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { ChatRequest } from '../type/homepage'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// 定义消息元数据接口（与 homepage.vue 中的定义保持一致）
interface MessageMetadata {
  message_id?: string
  session_id?: string
  role?: 'user' | 'assistant'
  content?: string
  timestamp?: string
  sources?: any[]
  rag_used?: boolean
  retrieval_strategy?: string
  tools_used?: any
  tool_results?: any
}

// 获得对话列表
export function getSessionListAPI(user_id: string) {
  return request({
    url: '/api/v1/chat/sessions',
    method: 'GET',
    params: {
      user_id
    }
  })
}

// 删除对话列表中的某个对话
export function deleteSessionAPI(session_id:string) {
  return request({
    url: `/api/v1/chat/sessions/${session_id}`,
    method: 'DELETE'
  })
}

// 查询对话列表中的某个对话
export function getSessionAPI(session_id:string) {
  return request({
    url: `/api/v1/chat/sessions/${session_id}/history`,
    method: 'GET'
  })
}


// 发送消息（SSE）
export const workspaceSimpleChatStreamAPI = async (
  data: ChatRequest,
  onMessage: (messageData: MessageMetadata) => void,
  onError?: (err: any) => void,
  onClose?: () => void
) => {
  // const token = localStorage.getItem('token')
  const ctrl = new AbortController()

  console.log('=== workspaceSimpleChatStreamAPI 调用 ===')
  console.log('请求参数:', data)
  console.log('请求 URL:', '/api/v1/chat/message')

  try {
    await fetchEventSource('/api/v1/chat/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(data),
      signal: ctrl.signal,
      openWhenHidden: true,
      onmessage(event) {
        console.log(' 收到 SSE 原始消息:', event.data)
        if (!event.data) return
        
        try {
          const parsed = JSON.parse(event.data)
          console.log('📦 解析后的数据:', parsed)
          
          // 🎯 阶段 1：接收 metadata 元数据
          // 格式：{"message_id": "...", "session_id": "...", "role": "assistant"}
          if (parsed?.message_id || parsed?.session_id) {
            console.log('📋 收到 metadata:', parsed)
            onMessage({
              message_id: parsed.message_id,
              session_id: parsed.session_id,
              role: parsed.role
            })
            return
          }
          
          // 🎯 阶段 2：接收流式 chunk 数据
          // 格式：{"content": "相关的法律文档"}
          if (parsed?.content && !parsed?.sources) {
            console.log('📝 收到 chunk:', parsed.content)
            onMessage({
              content: parsed.content
            })
            return
          }
          
          // 🎯 阶段 3：接收完整的 sources
          // 格式：{"sources": [{content, metadata}, ...]}
          if (parsed?.sources && Array.isArray(parsed.sources)) {
            console.log('📚 收到 sources:', parsed.sources)
            onMessage({
              sources: parsed.sources
            })
            return
          }
        } catch (error) {
          console.warn('⚠️ JSON 解析失败，跳过:', event.data, error)
        }
      },
      onerror(err) {
        console.error('❌ SSE 错误:', err)
        // ⚠️ 关键修复：调用 onError 后必须抛出错误以阻止 fetchEventSource 自动重试
        onError?.(err)
        // 抛出错误可以彻底终止连接，防止无限循环重试
        throw err
      },
      onclose() {
        console.log('✅ SSE 连接关闭')
        onClose?.()
      }
    })
  } catch (error: any) {
    console.error('❌ fetchEventSource 异常:', error)
    if (error?.name !== 'AbortError') {
      onError?.(error)
    }
  }
}
