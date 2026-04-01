import { request } from "../utils/request"

// 提示词列表项（与后端返回字段对齐）
export interface PromptSummary {
  id: string
  label: string
  description: string
  tags: string[]
  category: string
  source_file: string
}

// 提示词详情（在列表字段基础上补充具体内容字段）
export interface PromptDetail extends PromptSummary {
  content?: string
  prompt?: string
  template?: string
  text?: string
}

// 列表接口返回结构
export interface PromptsListResponse {
  code: number
  status: string
  message: string
  data: {
    prompts: PromptSummary[]
    total_count: number
    all_tags: string[]
  }
}

// 详情接口返回结构
export interface PromptDetailResponse {
  code: number
  status: string
  message: string
  data: PromptDetail
}

// 获取提示词列表
export function getPromptsAPI(params?: { category?: string; tag?: string }) {
  return request<PromptsListResponse>({
    url: "/api/v1/prompts/",
    method: "GET",
    params,
  })
}

// 获取提示词详情
export function getPromptDetailAPI(id: string) {
  return request<PromptDetailResponse>({
    url: `/api/v1/prompts/${id}`,
    method: "GET",
  })
}
