import { request } from '../utils/request'

export interface analyzepayload {
  session_id?: string
  message: string
  user_id: string
  file_paths?: string[]
  stream?: boolean
  max_history?: number
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

//发送消息进行分析
export const sendMessage = (paylad:analyzepayload) => {
  return request({
    url: `/api/v1/cyber-judge/analyze`,
    method: 'post',
    data: paylad,
    responseType: 'stream'
  })
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


