// 封装跟历史对话记录的接口函数
import { request } from "../utils/request"
import { SessionCreateType, MsgLikeType } from '../type'
import { linkEmits } from "element-plus"

// 主要创建对话窗口的信息  json 格式
export function createSessionAPI(data: SessionCreateType) {
  return request({
    url: '/api/v1/session',
    method: 'POST',
    data: {
      name: data.name,
      agent_id: data.agent_id,
      agent_type: data.agent_type
    }
  })
}




// 获取历史消息记录 - 根据对话ID
export function getHistoryMsgAPI(sessionId: string, limit: number = 20) {
  return request({
    url: `/api/v1/chat/sessions/${sessionId}/history`,
    method: 'GET',
    params: {
      limit
    }
  })
}

// 点赞-拉踩用户点击点赞功能，需要前端将userInput和agentOutput 返回给后端进行存入数据库  json 格式
export function MsgLikeCreateAPI(data: MsgLikeType) {
  return request({
    url: '/api/v1/message/like',
    method: 'POST',
    data
  })
}

// 用户点击拉踩功能，需要前端将userInput和agentOutput 返回给后端进行存入数据库   json 格式
export function MsgDisLikeAPI(data: MsgLikeType) {
  return request({
    url: '/api/v1/message/down',
    method: 'POST',
    data
  })
}
