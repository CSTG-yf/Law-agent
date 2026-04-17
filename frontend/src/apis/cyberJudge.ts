import { request } from '../utils/request'

export interface analyzepayload {
  session_id?: string
  message: string
  user_id: string
  file_paths?: string[]
  stream?: boolean
  max_history?: number
}

export interface CyberJudgeStreamHandlers {
  onMetadata?: (data: any) => void
  onProgress?: (data: any) => void
  onFactsSummary?: (data: any) => void
  onToken?: (data: any) => void
  onComplete?: (data: any) => void
  onTitle?: (data: any) => void
  onError?: (data: any) => void
  onDone?: () => void
}

function resolveApiUrl(path: string) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  if (!baseURL) {
    return path
  }
  return `${baseURL.replace(/\/$/, '')}${path}`
}

async function consumeSSEStream(response: Response, handlers: CyberJudgeStreamHandlers) {
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  if (!response.body) {
    throw new Error('响应流为空')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const handleEvent = (rawEvent: string) => {
    const lines = rawEvent.split('\n')
    let eventName = 'message'
    const dataLines: string[] = []

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }

    const dataText = dataLines.join('\n')
    const parsed = dataText ? JSON.parse(dataText) : {}

    if (eventName === 'metadata') {
      handlers.onMetadata?.(parsed)
    } else if (eventName === 'progress') {
      handlers.onProgress?.(parsed)
    } else if (eventName === 'facts_summary') {
      handlers.onFactsSummary?.(parsed)
    } else if (eventName === 'token') {
      handlers.onToken?.(parsed)
    } else if (eventName === 'complete') {
      handlers.onComplete?.(parsed)
    } else if (eventName === 'title') {
      handlers.onTitle?.(parsed)
    } else if (eventName === 'error') {
      handlers.onError?.(parsed)
    } else if (eventName === 'done') {
      handlers.onDone?.()
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

    let boundaryIndex = buffer.indexOf('\n\n')
    while (boundaryIndex !== -1) {
      const rawEvent = buffer.slice(0, boundaryIndex).trim()
      buffer = buffer.slice(boundaryIndex + 2)
      if (rawEvent) {
        handleEvent(rawEvent)
      }
      boundaryIndex = buffer.indexOf('\n\n')
    }

    if (done) {
      const trailingEvent = buffer.trim()
      if (trailingEvent) {
        handleEvent(trailingEvent)
      }
      break
    }
  }
}

// 获得对话列表
export function getSessionListAPI(user_id: string) {
  return request({
    url: '/api/v1/cyber-judge/sessions',
    method: 'GET',
    params: {
      user_id
    }
  })
}

// 删除对话列表中的某个对话
export function deleteSessionAPI(session_id:string) {
  return request({
    url: `/api/v1/cyber-judge/sessions/${session_id}`,
    method: 'DELETE'
  })
}

// 查询对话列表中的某个对话
export function getSessionAPI(session_id:string) {
  return request({
    url: `/api/v1/cyber-judge/sessions/${session_id}/history`,
    method: 'GET'
  })
}

// 发送消息进行流式分析
export async function sendMessageStream(
  payload: analyzepayload,
  handlers: CyberJudgeStreamHandlers
) {
  const token = localStorage.getItem('token')
  const response = await fetch(resolveApiUrl('/api/v1/cyber-judge/analyze'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(payload)
  })

  await consumeSSEStream(response, handlers)
}

//上传文件
export const uploadFile = async (file: File) => {
  const formData = new FormData() //使用 FormData 对象包装文件，这是前端发送文件的标准方式
  formData.append('file', file)
  return request({
    url: `/api/v1/cyber-judge/upload`,
    method: 'post',
    data: formData
  })
}
