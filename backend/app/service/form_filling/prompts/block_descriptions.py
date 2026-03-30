BLOCK_DESCRIPTIONS = {
    "plaintiff": """
当前业务块：原告信息
需要提取的槽位：
- plaintiff.name: 原告姓名
- plaintiff.gender: 性别（男/女）
- plaintiff.birthday: 出生日期（YYYY-MM-DD格式）
- plaintiff.ethnicity: 民族（如：汉族、回族等）
- plaintiff.work_unit: 工作单位
- plaintiff.job_title: 职位
- plaintiff.phone: 手机号码
- plaintiff.domicile: 户籍地址
- plaintiff.habitual_residence: 现住址
""",
    "agent": """
当前业务块：代理人信息
需要提取的槽位：
- agent.has_agent: 是否有委托代理人（true/false）
- agent.name: 代理人姓名
- agent.work_place: 代理人工作单位
- agent.job: 代理人职务
- agent.phone: 代理人电话
- agent.auth: 授权类型（一般/特别）

重要提示：
- 如果用户说"没有"、"不"、"无"、"不需要"等否定词,agent.has_agent 应该设置为 false
- 如果用户明确说"有"或提供了代理人信息,agent.has_agent 应该设置为 true
- agent.has_agent 是一个布尔值槽位,如果提取到该值,置信度应该为 1.0
- 对于 agent.has_agent 槽位,一旦提取到值,应该视为已确认(confirmed=true)
""",
    "service": """
当前业务块：送达地址
需要提取的槽位：
- service.address: 送达地址
- service.recipient: 收件人
- service.phone: 联系电话
- service.allow_electronic: 是否接受电子送达（true/false）
- service.wechat: 微信号
- service.mail: 电子邮箱

重要提示：
- 如果已知信息中 service.allow_electronic 为 false，则 service.wechat 和 service.mail 不需要填写，不要为这两个槽位生成澄清问题
- 如果已知信息中 service.allow_electronic 为 true 或未填写，才需要询问微信号和电子邮箱
""",
    "defendant": """
当前业务块：被告信息
需要提取的槽位：
- defendant.name: 被告公司名称
- defendant.address: 公司地址
- defendant.Company_address: 公司注册地址
- defendant.legal_rep: 法定代表人
- defendant.job: 法定代表人职务
- defendant.phone: 法定代表人电话
- defendant.social_credit_code: 统一社会信用代码
- defendant.entity_type: 企业类型（如：有限责任公司、股份有限公司等）
- defendant.is_state_owned: 是否国有企业（true/false）
""",
    "claims": """
当前业务块：诉讼请求
需要提取的槽位：
- claims.salary.active: 是否主张工资（true/false）
- claims.salary.details: 工资详情描述
- claims.double_salary.active: 是否主张未签劳动合同双倍工资（true/false）
- claims.double_salary.details: 双倍工资详情描述
- claims.overtime.active: 是否主张加班费（true/false）
- claims.overtime.details: 加班费详情描述
- claims.annual_leave.active: 是否主张年休假工资（true/false）
- claims.annual_leave.details: 年休假工资详情描述
- claims.social_loss.active: 是否主张社保损失（true/false）
- claims.social_loss.details: 社保损失详情描述
- claims.termination_compensation.active: 是否主张经济补偿金（true/false）
- claims.termination_compensation.details: 经济补偿金详情描述
- claims.illegal_termination_damages.active: 是否主张违法解除劳动合同赔偿金（true/false）
- claims.illegal_termination_damages.details: 违法解除赔偿金详情描述
- claims.other_requests: 其他诉讼请求
- claims.litigation_cost_burden: 诉讼费用承担（默认：由被告承担）
""",
    "preservation": """
当前业务块：财产保全
需要提取的槽位：
- preservation.active: 是否申请财产保全（true/false）
- preservation.court: 保全法院
- preservation.document: 保全文书
""",
    "facts": """
当前业务块：事实与理由
需要提取的槽位：
- facts.contract_signing: 合同签订情况描述
- facts.performance_details: 劳动合同履行情况详情
- facts.termination_reason: 离职原因详情
- facts.work_injury: 工伤情况（如有）
- facts.arbitration_details: 劳动仲裁情况详情
- facts.is_migrant_worker: 是否农民工（true/false）
- facts.legal_basis: 法律依据
"""
}


def get_block_description(block_id: str) -> str:
    return BLOCK_DESCRIPTIONS.get(block_id, "当前业务块：通用信息提取")
