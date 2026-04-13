import { request } from '../utils/request'

export interface GraphDocumentResponse {
  file_hash: string
  file_name: string
  chunks_count?: number
  uploaded_at?: string
  [key: string]: any
}

export interface GraphDocumentsListData {
  documents: GraphDocumentResponse[]
  total: number
}

export interface GraphDocumentsListResponse {
  code: number
  status: string
  message: string
  data: GraphDocumentsListData
}

export type GraphDocumentInfoResponse = Record<string, any>

export interface GraphUploadResponse {
  task_id?: string
  message?: string
  [key: string]: any
}

export interface GraphQueryRequest {
  query_type: string
  query: string
  entity_type?: string
  relation_type?: string
  limit?: number
}

export type GraphQueryResponse = Record<string, any>

export interface GraphVisualizationRequest {
  node_types?: string
  relation_types?: string
  node_limit?: number
  depth?: number
  search_term?: string
}

export type GraphVisualizationResponse = Record<string, any>

// 获取知识图谱文档列表
export function getGraphDocumentsAPI() {
  return request<GraphDocumentsListResponse>({
    url: '/api/v1/graph/documents',
    method: 'GET',
    timeout: 60000
  })
}

// 获取单个知识图谱文档详情
export function getGraphDocumentInfoAPI(file_hash: string) {
  return request<GraphDocumentInfoResponse>({
    url: `/api/v1/graph/documents/${file_hash}`,
    method: 'GET',
    timeout: 60000
  })
}

// 删除知识图谱文档
export function deleteGraphDocumentAPI(file_hash: string) {
  return request<{ message?: string }>({
    url: `/api/v1/graph/documents/${file_hash}`,
    method: 'DELETE',
    timeout: 60000
  })
}

// 上传知识图谱文档
export function uploadGraphDocumentAPI(formData: FormData) {
  return request<GraphUploadResponse>({
    url: '/api/v1/graph/upload',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 600000
  })
}

// 查询知识图谱
export function queryGraphAPI(data: GraphQueryRequest) {
  return request<GraphQueryResponse>({
    url: '/api/v1/graph/query',
    method: 'POST',
    data,
    timeout: 60000
  })
}

// 获取知识图谱可视化数据（POST）
export function postGraphVisualizationAPI(data: GraphVisualizationRequest) {
  return request<GraphVisualizationResponse>({
    url: '/api/v1/graph/visualization',
    method: 'POST',
    data,
    timeout: 600000
  })
}

// 获取知识图谱可视化数据（GET，可选）
export function getGraphVisualizationAPI(params: GraphVisualizationRequest) {
  return request<GraphVisualizationResponse>({
    url: '/api/v1/graph/visualization',
    method: 'GET',
    params,
    timeout: 600000
  })
}

// 清空知识图谱
export function clearGraphAPI() {
  return request<{ message?: string; success?: boolean; code?: number }>({
    url: '/api/v1/graph/clear',
    method: 'DELETE',
    timeout: 600000
  })
}
