BLOCK_GREETINGS = {
    "plaintiff": "您好！让我们开始填写法律文书。首先，我需要了解您的基本信息，请告诉我您的姓名、联系方式和住址。",
    "agent": "好的，原告信息已经填写完成。接下来，请问您是否有委托代理人？如果有，请告诉我代理人的相关信息。",
    "service": "很好！原告和代理人信息都已确认。现在让我们来填写法律文书送达地址，这是法院向您送达法律文书的重要信息。",
    "defendant": "送达地址已记录。接下来请告诉我被告公司的信息，包括公司名称、地址等。",
    "claims": "好的，被告信息已填写完成。现在请告诉我您的诉讼请求，比如您是否主张拖欠工资、加班费、未签劳动合同双倍工资或经济补偿金等。",
    "preservation": "了解了。请问您是否需要申请诉前财产保全？",
    "facts": "好的，诉讼请求已记录。最后，请详细描述一下您和被告之间的劳动关系情况，包括入职时间、工作内容、离职原因等。"
}

BLOCK_COMPLETION_MESSAGES = {
    "plaintiff": "好的，原告信息已填写完成。",
    "agent": "明白了，代理人信息已确认。",
    "service": "好的，送达地址已填写完成。",
    "defendant": "好的，被告信息已填写完成。",
    "claims": "好的，诉讼请求已填写完成。",
    "preservation": "好的，财产保全信息已填写完成。",
    "facts": "好的，事实与理由已填写完成。"
}

SLOT_QUESTIONS = {
    "plaintiff.name": "请问您的姓名是什么？",
    "plaintiff.gender": "请问您的性别是？",
    "plaintiff.birthday": "请问您的出生日期是？（格式：YYYY-MM-DD）",
    "plaintiff.ethnicity": "请问您的民族是？",
    "plaintiff.work_unit": "请问您的工作单位是？",
    "plaintiff.job_title": "请问您的职位是？",
    "plaintiff.phone": "请问您的联系电话是？",
    "plaintiff.domicile": "请问您的户籍地址是？",
    "plaintiff.habitual_residence": "请问您的现住址是？",
    "agent.has_agent": "请问您是否有委托代理人？",
    "agent.name": "请问代理人的姓名是？",
    "agent.work_place": "请问代理人的工作单位是？",
    "agent.job": "请问代理人的职务是？",
    "agent.phone": "请问代理人的联系电话是？",
    "agent.auth": "请问代理人的授权类型是？（一般授权/特别授权）",
    "service.address": "请问法律文书的送达地址是？",
    "service.recipient": "请问收件人是谁？",
    "service.phone": "请问收件人的联系电话是？",
    "service.allow_electronic": "请问是否接受电子送达？",
    "service.wechat": "请问微信号是？",
    "service.mail": "请问电子邮箱是？",
    "defendant.name": "请问被告公司的名称是？",
    "defendant.address": "请问被告公司的地址是？",
    "defendant.Company_address": "请问被告公司的注册地址是？",
    "defendant.legal_rep": "请问被告公司的法定代表人是谁？",
    "defendant.job": "请问法定代表人的职务是？",
    "defendant.phone": "请问法定代表人的电话是？",
    "defendant.social_credit_code": "请问被告公司的统一社会信用代码是？",
    "defendant.entity_type": "请问被告公司的企业类型是？（如：有限责任公司、股份有限公司等）",
    "defendant.is_state_owned": "请问被告公司是否为国有企业？",
    "claims.salary.active": "请问是否主张工资？",
    "claims.salary.details": "请详细说明工资诉求。",
    "claims.double_salary.active": "请问是否主张未签劳动合同双倍工资？",
    "claims.double_salary.details": "请详细说明双倍工资诉求。",
    "claims.overtime.active": "请问是否主张加班费？",
    "claims.overtime.details": "请详细说明加班费诉求。",
    "claims.annual_leave.active": "请问是否主张年休假工资？",
    "claims.annual_leave.details": "请详细说明年休假工资诉求。",
    "claims.social_loss.active": "请问是否主张社保损失？",
    "claims.social_loss.details": "请详细说明社保损失诉求。",
    "claims.termination_compensation.active": "请问是否主张经济补偿金？",
    "claims.termination_compensation.details": "请详细说明经济补偿金诉求。",
    "claims.illegal_termination_damages.active": "请问是否主张违法解除劳动合同赔偿金？",
    "claims.illegal_termination_damages.details": "请详细说明违法解除赔偿金诉求。",
    "claims.other_requests": "请问还有其他诉讼请求吗？",
    "claims.litigation_cost_burden": "请问诉讼费用由谁承担？",
    "preservation.active": "请问是否申请诉前财产保全？",
    "preservation.court": "请问保全法院是？",
    "preservation.document": "请问保全文书是？",
    "facts.contract_signing": "请问劳动合同签订情况如何？",
    "facts.performance_details": "请详细描述劳动合同履行情况。",
    "facts.termination_reason": "请问离职原因是什么？",
    "facts.work_injury": "请问是否有工伤情况？",
    "facts.arbitration_details": "请问是否申请过劳动仲裁？如有，请说明仲裁情况。",
    "facts.is_migrant_worker": "请问您是否为农民工？"
}

SLOT_CONFIRMATIONS = {
    "plaintiff.name": "请确认一下，您的姓名是{value}吗？",
    "plaintiff.phone": "请确认一下，您的联系电话是{value}吗？",
    "defendant.name": "请确认一下，被告公司的名称是{value}吗？",
    "facts.performance_details": "请确认一下，劳动合同履行情况是否正确？",
    "facts.termination_reason": "请确认一下，离职原因是否正确？"
}

ALL_COMPLETE_MESSAGE = "太好了！所有信息都已填写完成。您可以点击生成文档按钮，生成法律文书。"

DEFAULT_GREETING = "请继续填写相关信息。"
DEFAULT_COMPLETION = "该部分信息已填写完成。"
DEFAULT_SLOT_QUESTION = "请填写{slot_name}的信息"
DEFAULT_SLOT_CONFIRMATION = "请确认一下，{slot_name}的信息是否正确？"


def get_greeting(block_id: str) -> str:
    return BLOCK_GREETINGS.get(block_id, DEFAULT_GREETING)


def get_completion(block_id: str) -> str:
    return BLOCK_COMPLETION_MESSAGES.get(block_id, DEFAULT_COMPLETION)


def get_slot_question(slot_name: str) -> str:
    return SLOT_QUESTIONS.get(slot_name, DEFAULT_SLOT_QUESTION.format(slot_name=slot_name))


def get_slot_confirmation(slot_name: str) -> str:
    return SLOT_CONFIRMATIONS.get(slot_name, DEFAULT_SLOT_CONFIRMATION.format(slot_name=slot_name))
