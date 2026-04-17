import { request } from '../utils/request'
import { fetchEventSource } from '@microsoft/fetch-event-source'

//获取文书填写会话列表
export function getSessionListAPI(user_id: string) {
  return request({
    url: '/api/v1/form-filling/sessions',
    method: 'GET',
    params: {
      user_id
    }
  })
}


// 获取文书填写会话列表中的某个会话
export const getFormFillSessionInfoAPI = async (sessionId: string) => {
  return request({
    url: `/api/v1/form-filling/history`,
    method: 'post',
    data: {
      session_id: sessionId,
      limit: 50
    }
  })
}

// 删除文书填写会话列表中的某个会话 
export const deleteFormFillSessionAPI = async (sessionId: string) => {
  return request({
    url: `/api/v1/form-filling/session/${sessionId}`,
    method: 'delete'
  })
}

//开启新的文书填写会话
export const startFormFillSessionAPI = async (userId: string, templateType: string) => {
  return request({
    url: `/api/v1/form-filling/start`,
    method: 'post',
    data: {
      user_id: userId,
      template_type: templateType
    }
  })
}

//获取可用文档模板列表
export const getTemplateListAPI = async () => {
  return request({
    url: `/api/v1/form-filling/templates`,
    method: 'get'
  })
}

//发送消息进行文书填写
export const sendMessageForFormFillAPI = async (sessionId: string, message: string, userId: string) => {
  return request({
    url: `/api/v1/form-filling/message`,
    method: 'post',
    data: {
      session_id: sessionId,
      message: message,
      user_id: userId
    }
  })
}

// 获取当前填写状态
export const getFormFillStatusAPI = async (sessionId: string) => {
  return request({
    url: `/api/v1/form-filling/state`,
    method: 'post',
    data: {
      session_id: sessionId
    }
  })
}

// 手动更新槽位值
export const updateSlotValueAPI = async (sessionId: string, blockId: string, slotName: string, slotValue: string) => {
  return request({
    url: `/api/v1/form-filling/update-slot`,
    method: 'post',
    data: {
      session_id: sessionId,
      block_id: blockId,
      slot_name: slotName,
      value: slotValue,
      confirmed: true
    }
  })
}

//获取最终生成的文档
export const getFinalDocumentAPI = async (sessionId: string) => {
  return request({
    url: `/api/v1/form-filling/generate`,
    method: 'post',
    data: {
      session_id: sessionId
    }
  })
}

//下载生成的文档
export const downloadDocumentAPI = async (filename: string) => {
  return request({
    url: `/api/v1/form-filling/download/${filename}`,
    method: 'GET',
    responseType: 'blob'
  })
}

