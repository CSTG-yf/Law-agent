import { request } from "../utils/request"

// 主要获取配置的默认内容
export function getConfigAPI() {
  return request({
    url: '/api/v1/config',
    method: 'GET',
  })
}

// 修改配置的默认内容（支持 JSON 格式）
export function updateConfigAPI(data: {
  OPENAI_BASE_URL?: string
  OPENAI_API_KEY?: string
  DASHSCOPE_API_KEY?: string
  HF_TOKEN?: string
  MODEL_NAME?: string
  RAG_TOP_K?: string
  RAG_FETCH_K?: string
  PRE_RETRIEVE_TOP_K?: string
  MAX_HISTORY_LENGTH?: string
}) {
  return request({
    url: '/api/v1/config',
    method: 'PUT',
    data  // Axios 会自动将对象转换为 JSON 并设置 Content-Type: application/json
  })
}

// 测试模型配置
export function testModelAPI(data: { message: string }) {
  return request({
    url: '/api/v1/config/test',
    method: 'POST',
    data
  })
}
