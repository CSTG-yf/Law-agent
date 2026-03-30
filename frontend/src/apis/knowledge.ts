import { request } from "../utils/request"

// 统一响应模型
export interface UnifiedResponse<T = any> {
  status_code: number
  status_message: string
  data?: T
}

// 知识库响应类型
export interface KnowledgeResponse {
  id: string
  name: string
  description: string | null
  user_id: string | null
  create_time: string
  update_time: string
  count: number // 文件数量
  file_size: string // 文件总大小（已格式化）
}

// 知识库创建请求
export interface KnowledgeCreateRequest {
  knowledge_name: string
  knowledge_desc?: string
}

// 知识库更新请求
export interface KnowledgeUpdateRequest {
  knowledge_id: string
  knowledge_name?: string
  knowledge_desc?: string
}

// 知识库删除请求
export interface KnowledgeDeleteRequest {
  knowledge_id: string
}

// 知识库检索请求
export interface KnowledgeRetrievalRequest {
  query: string
  knowledge_id: string | string[]
  top_k?: number
}

// RAG 文档响应类型（对应后端 DocumentInfo）
export interface RagDocumentResponse {
  file_hash: string
  file_name: string
  chunks_count: number
  uploaded_at?: string
}

// RAG 文档列表响应（后端返回 { documents: [...], total: number }）
export interface RagDocumentsListResponse {
  documents: RagDocumentResponse[]
  total: number
}

// 单个 RAG 文档内容响应（这里暂不限定结构，交由后端决定）
export interface RagDocumentContentResponse {
  // 常见情况是后端返回 { content: string }
  // 如有更多字段，可在此补充类型
  content?: string
  [key: string]: any
}

// 查询知识库列表
export function getKnowledgeListAPI() {
  return request<UnifiedResponse<KnowledgeResponse[]>>({
    url: '/api/v1/knowledge/select',
    method: 'GET'
  })
}

// 创建知识库
export function createKnowledgeAPI(data: KnowledgeCreateRequest) {
  return request<UnifiedResponse<null>>({
    url: '/api/v1/knowledge/create',
    method: 'POST',
    data
  })
}

// 更新知识库
export function updateKnowledgeAPI(data: KnowledgeUpdateRequest) {
  return request<UnifiedResponse<null>>({
    url: '/api/v1/knowledge/update',
    method: 'PUT',
    data
  })
}

// 删除知识库
export function deleteKnowledgeAPI(data: KnowledgeDeleteRequest) {
  return request<UnifiedResponse<null>>({
    url: '/api/v1/knowledge/delete',
    method: 'DELETE',
    data
  })
}

// 知识库检索
export function knowledgeRetrievalAPI(data: KnowledgeRetrievalRequest) {
  return request<UnifiedResponse<string>>({
    url: '/api/v1/knowledge/retrieval',
    method: 'POST',
    data
  })
} 

// 获取 RAG 文档列表（该接口直接返回 { documents, total }，不包统一响应壳）
export function getRagDocumentsAPI() {
  return request<RagDocumentsListResponse>({
    url: '/api/v1/rag/documents',
    method: 'GET',
    timeout: 60000
  })
}

// 根据 file_hash 获取单个文档内容
export function getRagDocumentContentAPI(file_hash: string) {
  return request<RagDocumentContentResponse | string>({
    url: `/api/v1/rag/document/${file_hash}`,
    method: 'GET',
    timeout: 60000
  })
}

// 删除单个 RAG 文档（异步删除，返回任务信息）
export function deleteRagDocumentAPI(file_hash: string) {
  return request<{
    success: boolean
    message: string
    code: number
    task_id?: string
  }>({
    url: '/api/v1/rag/document',
    method: 'DELETE',
    data: { file_hash }
  })
}

// 上传 RAG 文档（异步）
export function uploadRagDocumentAPI(formData: FormData) {
  return request<{ task_id?: string }>({
    url: '/api/v1/rag/upload',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 600000 // 上传和异步处理可能比较久
  })
}

// 批量上传 RAG 文档（ZIP 异步上传）
export function uploadRagDocumentsBatchAPI(formData: FormData) {
  return request<{ task_id?: string}>({
    url: '/api/v1/rag/upload/batch',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 600000
  })
}
