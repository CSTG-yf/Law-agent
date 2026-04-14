import { request } from '../utils/request'


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

//发送消息进行文书填写
export const sendMessage = async (sessionId: string, message: string, userId: string, file_paths: string[]) => {
  return request({
    url: `/api/v1/cyber-judge/analyze`,
    timeout: 60000,
    method: 'post',
    data: {
      session_id: sessionId,
      message: message,
      user_id: userId,
      file_paths: file_paths
    }
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


