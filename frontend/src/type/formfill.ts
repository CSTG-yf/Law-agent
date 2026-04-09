// 文书填充会话列表中的会话项
export interface formfillSession {
  session_id: string;        // 会话 ID，例如：filling-labor_dispute-4d55b923aa65
  template_type: string;     // 模板类型，例如：labor_dispute
  current_block: string;     // 当前块，例如：claims
  conversation_turn: number; // 对话轮数
  created_at: string;        // 创建时间，ISO 8601 格式，例如：2026-03-30T18:30:00
  updated_at: string;        // 更新时间，ISO 8601 格式，例如：2026-03-30T19:00:00
}

//文书填充会话列表中的某个会话详情
export interface formfillSessionDetail{
  role: string;              // 角色，例如：user 或 assistant
  message: string;           // 消息内容，例如：请描述一下你的劳动争议情况。
  timestamp: string;        // 消息时间，ISO 8601 格式，例如：2026-03-30T18:35:00
}

//文书填充会话列表中的某个会话详情响应接口
export interface formfillSessionDetailResponse {
  session_id: string;        // 会话 ID，例如：filling-labor_dispute-4d55b923aa65
  message: string;
  current_block: string;     // 当前块，例如：claims
  completion_rate: number;   // 完成率，例如：0.8
  extracted_slots: Record<string, string>; // 已提取的槽位值，例如：{"claim_description": "我被公司无故解雇了", "claim_amount": "10000"}
  needs_clarification: boolean; // 是否需要澄清，例如：true
  clarification_questions: string[]; // 澄清问题列表，例如：["请提供一下你的工作单位名称。", "请问你是什么时候被解雇的？"]
  suggested_next_action: string; // 建议的下一步行动，例如：请提供一下你的工作单位名称。
}

//文书模板
export interface formTemplate {
  template_type: string; // 模板类型，例如：labor_dispute
  template_name: string; // 模板名称，例如：劳动争议文书
  template_file: string; // 模板文件路径，例如：/templates/labor_dispute.docx
  block_count: number;   // 块数量，例如：5
}

//获取文书填充会话列表
export interface allblock {
  block_id: string;
  display_name: string;
  description: string;
  slots:slotInfo[];
  order: number;
}

//槽位信息
export interface slotInfo {
  slot_name: string;        // 槽位名称，例如：claim_description
  required: boolean;       // 是否必填，例如：true
}


//对话后更新的模块信息
export interface block {
  block_id: string;        // 模块 ID，例如：claims
  display_name: string;    // 模块展示名称，例如：诉求描述
  slots: slot[];  // 模块中的槽位列表
  completion_rate: number; // 模块完成率，例如：0.8
  is_active: boolean; // 是否为当前模块，例如：true
  is_completed: boolean; // 模块是否已完成，例如：false
}

//对话后更新的槽位信息
export interface slot {
  value: string;             // 槽位值，例如：我被公司无故解雇了
  confirmed: boolean;        // 是否已确认，例如：true
  source: string;           // 槽位值来源，例如：user_input、model_extraction、manual_update
  confidence: number;        // 槽位值的置信度，例如：0.9
  turn_filled: number;       // 填充该槽位的对话轮数，例如：2
}