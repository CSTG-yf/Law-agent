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
- claims.salary.details: 工资详情描述（专业化法律文书语言）
- claims.double_salary.active: 是否主张未签劳动合同双倍工资（true/false）
- claims.double_salary.details: 双倍工资详情描述（专业化法律文书语言）
- claims.overtime.active: 是否主张加班费（true/false）
- claims.overtime.details: 加班费详情描述（专业化法律文书语言）
- claims.annual_leave.active: 是否主张年休假工资（true/false）
- claims.annual_leave.details: 年休假工资详情描述（专业化法律文书语言）
- claims.social_loss.active: 是否主张社保损失（true/false）
- claims.social_loss.details: 社保损失详情描述（专业化法律文书语言）
- claims.termination_compensation.active: 是否主张经济补偿金（true/false）
- claims.termination_compensation.details: 经济补偿金详情描述（专业化法律文书语言）
- claims.illegal_termination_damages.active: 是否主张违法解除劳动合同赔偿金（true/false）
- claims.illegal_termination_damages.details: 违法解除赔偿金详情描述（专业化法律文书语言）
- claims.other_requests: 其他诉讼请求
- claims.litigation_cost_burden: 诉讼费用承担（默认：由被告承担）

重要提示（诉讼请求块专属规则）：
1. **两阶段提取规则**：
   - 第一阶段：当用户首次提到某项诉讼请求时，只提取对应的 active 槽位（设为 true），**不要**同时填写 details 槽位
   - 第二阶段：当用户补充了具体金额、时间段等明细信息后，才将用户的口语化描述**专业化改写**后填入 details 槽位

2. **details 槽位的专业化改写规则**：
   - details 必须使用法律文书的专业化语言，不能直接使用用户的口语化表述
   - 改写示例：
     * 用户说"公司没付给我加班费" → details 应为"被告未依法支付原告加班工资，原告主张被告支付加班费"
     * 用户说"没给我交社保" → details 应为"被告未依法为原告缴纳社会保险费，原告主张被告赔偿社保损失"
     * 用户说"公司违法开除我" → details 应为"被告违法解除与原告的劳动合同，原告主张被告支付违法解除劳动合同赔偿金"
     * 用户说"没签劳动合同" → details 应为"被告未与原告签订书面劳动合同，原告主张被告支付未签订书面劳动合同的二倍工资差额"
     * 用户说"拖欠我三个月工资" → details 应为"被告拖欠原告工资共计三个月，原告主张被告支付拖欠的工资"

3. **提问规则**：
   - 当某个 active 槽位被设为 true 但对应的 details 尚未填写时，clarification_questions 中应引导用户提供具体明细
   - 提问应自然地询问金额、时间段等关键信息，例如："关于加班费，您能告诉我具体的加班时间段和主张的金额吗？"
   - 如果多个 active 为 true 但 details 未填写，合并提问，例如："您提到了加班费和社保损失，能分别说说具体的金额和时间段吗？"

4. **不要直接复制用户原话到 details 中**：details 必须经过专业化改写，使用法律文书的规范表述
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
需要提取的槽位（每个槽位对应法律文书中的一个段落，需包含对应维度的完整信息）：

1. facts.contract_signing - 劳动合同签订情况
   需要包含的维度：合同主体（原告与被告）、签订时间、签订地点、合同名称/类型
   改写示例：
   * 用户说"去年2024年入的职，没签合同" → "原告于2024年入职被告处工作，被告未与原告签订书面劳动合同"
   * 用户说"签了三年合同" → "原被告签订了期限为三年的书面劳动合同"
   * 用户说"2024年3月入职的" → "原告于2024年3月入职被告处工作"

2. facts.performance_details - 劳动合同履行情况
   需要包含的维度：入职时间、用人单位、工作岗位、工作地点、合同约定的每月工资数额及工资构成、办理社会保险的时间及险种、劳动者实际领取的每月工资数额及工资构成、加班工资计算基数及计算方法、原告加班时间及加班费、年休假等
   改写示例：
   * 用户说"工作内容是教书，每月5000" → "原告在被告处从事教学工作，月工资标准为5000元"
   * 用户说"是雇佣关系，没交社保" → "原被告之间存在劳动关系，被告未依法为原告缴纳社会保险"
   * 用户说"每月工资6000，但实际只发4500" → "原告月工资标准为6000元，被告实际每月支付原告工资4500元"

3. facts.termination_reason - 解除或终止劳动关系情况
   需要包含的维度：解除或终止劳动关系的原因、经济补偿/赔偿金数额等
   改写示例：
   * 用户说"受不了加班离职的" → "原告因被告安排过度加班被迫离职"
   * 用户说"公司开除我，没给补偿" → "被告单方解除与原告的劳动关系，未支付经济补偿金"
   * 用户说"公司倒闭了" → "因被告经营困难导致劳动合同无法继续履行"

4. facts.work_injury - 工伤情况
   需要包含的维度：发生工伤时间、工伤认定情况、工伤伤残等级、工伤费用等
   改写示例：
   * 用户说"2024年5月在车间受伤了，评了十级伤残" → "原告于2024年5月在工作期间受伤，经认定为工伤，伤残等级为十级"

5. facts.arbitration_details - 劳动仲裁相关情况
   需要包含的维度：仲裁裁决书编号、仲裁请求、仲裁结果等
   改写示例：
   * 用户说"仲裁判了公司赔我3万" → "经劳动仲裁，裁决被告支付原告30000元"

6. facts.is_migrant_worker - 是否农民工（true/false）

7. facts.legal_basis - 诉请依据
   需要包含的维度：法律及司法解释的具体条文
   改写示例：
   * 用户说"加班费和社保" → "根据《中华人民共和国劳动法》第四十四条及《中华人民共和国社会保险法》相关规定"

重要提示（事实与理由块专属规则）：
1. **专业化改写**：所有描述类槽位必须使用法律文书的专业化语言，以"原告...被告..."的规范表述呈现
2. **禁止元描述**：绝对不能输出"用户提到..."、"未明确说明..."、"用户未提及..."等分析性文字，槽位值必须是直接可用于法律文书的事实陈述句
3. **不确定则留空**：如果用户没有提到某个槽位的信息，不要填写该槽位，直接留空即可，不要写任何"不确定"的描述
4. **信息逐步积累**：用户可能在多轮对话中逐步提供信息，每次提取时只填写用户已明确提到的内容，不要臆测或编造
"""
}


def get_block_description(block_id: str) -> str:
    return BLOCK_DESCRIPTIONS.get(block_id, "当前业务块：通用信息提取")
