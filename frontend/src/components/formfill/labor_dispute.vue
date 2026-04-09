<template>
  <div class="legal-document-container">
    <h1 class="document-title">民事起诉状</h1>
    <p class="document-subtitle">（劳动争议纠纷）</p>

    <div class="instruction-box">
      <p class="instruction-title">说明：</p>
      <p class="instruction-text">为了方便您更好地参加诉讼，保护您的合法权利，请填写本表。</p>
      <ol class="instruction-list">
        <li>应诉时需向人民法院提交证明您身份的材料，如身份证复印件、营业执照复印件等。</li>
        <li>本表所列内容是您提起诉讼以及人民法院查明案件事实所需，请务必如实填写。</li>
        <li>本表所涉内容系针对一般劳动争议纠纷案件，有些内容可能与您的案件无关，您认为与案件无关的项目可以填"无"或不填；对于本表中勾选项可以在对应项打"√"；您认为另有重要内容需要列明的，可以在本表尾部或者另附页填写。</li>
      </ol>
      <div class="warning-text">
        ★特别提示★
      </div>
      <p class="warning-content">
        《中华人民共和国民事诉讼法》第十三条第一款规定："民事诉讼应当遵循诚信原则。"
        如果诉讼参加人违反上述规定，进行虚假诉讼、恶意诉讼，人民法院将视违法情形依法追究责任。
      </p>
    </div>

    <table class="legal-table">
      <thead>
        <tr class="section-header-main">
          <td colspan="2">当事人信息</td>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="label-cell">原告</td>
          <td class="content-cell">
            <div class="info-line">
              姓名：<editable-field :value="plaintiff.name" field-key="name" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              性别：<editable-field :value="plaintiff.gender" field-key="gender" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              出生日期：<editable-field :value="plaintiff.birthday" field-key="birthday" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              民族：<editable-field :value="plaintiff.ethnicity" field-key="ethnicity" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              工作单位：<editable-field :value="plaintiff.work_unit" field-key="work_unit" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              职务：<editable-field :value="plaintiff.job_title" field-key="job_title" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              联系电话：<editable-field :value="plaintiff.phone" field-key="phone" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              住所地（户籍所在地）：<editable-field :value="plaintiff.domicile" field-key="domicile" block-id="plaintiff" @update="handleUpdate" />
            </div>
            <div class="info-line">
              经常居住地：<editable-field :value="plaintiff.habitual_residence" field-key="habitual_residence" block-id="plaintiff" @update="handleUpdate" />
            </div>
          </td>
        </tr>
        <tr>
          <td class="label-cell">委托诉讼代理人</td>
          <td class="content-cell">
            <div class="checkbox-inline">
              <span class="checkbox-item" @click="handleToggle('agent', 'has_agent', true)">
                有 [ {{ agent.has_agent ? '√' : ' ' }} ]
              </span>
              <span class="checkbox-item" @click="handleToggle('agent', 'has_agent', false)">
                无 [ {{ !agent.has_agent ? '√' : ' ' }} ]
              </span>
            </div>
            <template v-if="agent.has_agent">
              <div class="info-line">
                姓名：<editable-field :value="agent.name || '无'" field-key="name" block-id="agent" @update="handleUpdate" />
              </div>
              <div class="info-line">
                单位：<editable-field :value="agent.work_place || '无'" field-key="work_place" block-id="agent" @update="handleUpdate" />
              </div>
              <div class="info-line">
                职务：<editable-field :value="agent.job || '无'" field-key="job" block-id="agent" @update="handleUpdate" />
              </div>
              <div class="info-line">
                联系电话：<editable-field :value="agent.phone || '无'" field-key="phone" block-id="agent" @update="handleUpdate" />
              </div>
              <div class="info-line">
                <span class="checkbox-item" @click="handleToggle('agent', 'auth', !agent.auth)">
                  代理权限：一般授权 [ {{ !agent.auth ? '√' : ' ' }} ]
                </span>
                <span class="checkbox-item" @click="handleToggle('agent', 'auth', !agent.auth)">
                  特别授权 [ {{ agent.auth ? '√' : ' ' }} ]
                </span>
              </div>
            </template>
          </td>
        </tr>
        <tr>
          <td class="label-cell">送达地址（所填信息除书面特别声明更改外，适用于案件一审、二审、再审所有后续程序）及收件人、电话</td>
          <td class="content-cell">
            <div class="info-line">
              地址：<editable-field :value="service.address" field-key="address" block-id="service" @update="handleUpdate" />
            </div>
            <div class="info-line">
              收件人：<editable-field :value="service.recipient" field-key="recipient" block-id="service" @update="handleUpdate" />
            </div>
            <div class="info-line">
              电话：<editable-field :value="service.phone" field-key="phone" block-id="service" @update="handleUpdate" />
            </div>
          </td>
        </tr>
        <tr>
          <td class="label-cell">是否接受电子送达</td>
          <td class="content-cell">
            <div class="info-line">
              <span class="checkbox-item" @click="handleToggle('service', 'allow_electronic', true)">
                是 [ {{ service.allow_electronic ? '√' : ' ' }} ]
              </span>
               <span class="checkbox-item" @click="handleToggle('service', 'allow_electronic', false)">
                否 [ {{ !service.allow_electronic ? '√' : ' ' }} ]
              </span>
            </div>
             <template v-if="service.allow_electronic">
              <div>方式：</div>
              <div>
                 　　微信: <editable-field :value="service.wechat" field-key="wechat" block-id="service" @update="handleUpdate" class="inline-edit" />
              </div>
              <div>
                 　　邮箱: <editable-field :value="service.mail" field-key="mail" block-id="service" @update="handleUpdate" class="inline-edit" />
              </div>     
                     
              </template>
            <div class="info-line">
             
            </div>
          </td>
        </tr>
        <tr>
          <td class="label-cell">被告</td>
          <td class="content-cell">
            <div class="info-line">
              名称：<editable-field :value="defendant.name" field-key="name" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              住所地（主要办事机构所在地）：<editable-field :value="defendant.address" field-key="address" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              注册地/登记地：<editable-field :value="defendant.company_address" field-key="company_address" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              法定代表人/主要负责人：<editable-field :value="defendant.legal_rep" field-key="legal_rep" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              职务：<editable-field :value="defendant.job" field-key="job" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              联系电话：<editable-field :value="defendant.phone" field-key="phone" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              统一社会信用代码：<editable-field :value="defendant.social_credit_code" field-key="social_credit_code" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              类型：<editable-field :value="defendant.entity_type" field-key="entity_type" block-id="defendant" @update="handleUpdate" />
            </div>
            <div class="info-line">
              <span class="checkbox-item" @click="handleToggle('defendant', 'is_state_owned', !defendant.is_state_owned)">
                企业性质：国有 [ {{ defendant.is_state_owned ? '√' : ' ' }} ]
              </span>
              <span class="checkbox-item" @click="handleToggle('defendant', 'is_state_owned', !defendant.is_state_owned)">
                民营 [ {{ !defendant.is_state_owned ? '√' : ' ' }} ]
              </span>
            </div>
          </td>
        </tr>

        <tr class="section-header-main">
          <td colspan="2">诉讼请求和依据</td>
        </tr>
        
        <tr v-for="(claim, key, index) in claimsList" :key="key">
          <td class="label-cell">{{ index + 1 }}. {{ claim.label }}</td>
          <td class="content-cell">
            <template v-if="claim.isSimple">
              <div class="info-line">
                <editable-field :value="claim.value || '无'" :field-key="key" block-id="claims" @update="handleUpdate" />
              </div>
            </template>
            <template v-else>
              <div class="info-line">
                <span class="checkbox-item" @click="handleToggle('claims', key + '.active', true)">
                  是 [ {{ claim.data.active ? '√' : ' ' }} ]
                </span>
                <span class="checkbox-item" @click="handleToggle('claims', key + '.active', false)">
                  否 [ {{ !claim.data.active ? '√' : ' ' }} ]
                </span>
              </div>
              <div v-if="claim.data.active" class="info-line">
                明细：<editable-field :value="claim.data.details || '无'" :field-key="key + '.details'" block-id="claims" @update="handleUpdate" />
              </div>
            </template>
          </td>
        </tr>

       <tr>
          <td class="label-cell">10. 是否已经申请诉前保全</td>
          <td class="content-cell">
            <div class="info-line">
              <span class="checkbox-item" @click="handleToggle('preservation', 'active', true)">
                是 [ {{ preservation.active ? '√' : ' ' }} ]
              </span>
              <span class="checkbox-item" @click="handleToggle('preservation', 'active', false)">
                否 [ {{ !preservation.active ? '√' : ' ' }} ]
              </span>
            </div>
            <template v-if="preservation.active">
              <div class="info-line">
                法院：<editable-field :value="preservation.court || '无'" field-key="court" block-id="preservation" @update="handleUpdate" />
              </div>
              <div class="info-line">
                案号：<editable-field :value="preservation.document || '无'" field-key="document" block-id="preservation" @update="handleUpdate" />
              </div>
            </template>
          </td>
        </tr>

        <tr class="section-header-main">
          <td colspan="2">事实和理由</td>
        </tr>
        
        <tr>
          <td class="label-cell">1. 劳动合同签订情况</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.contract_signing || '无'" field-key="contract_signing" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">2. 劳动合同履行情况</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.performance_details || '无'" field-key="performance_details" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">3.解除或终止劳动关系情况</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.termination_reason || '无'" field-key="termination_reason" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">4.工伤情况</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.is_migrant_worker || '无'" field-key="is_migrant_worker" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">5.劳动仲裁相关情况</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.work_injury || '无'" field-key="work_injury" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">6.其他相关情况</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.arbitration_details || '无'" field-key="arbitration_details" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">7.诉请依据</td>
          <td class="content-cell tall-cell">
            <editable-field :value="facts.legal_basis || '无'" field-key="legal_basis" block-id="facts" @update="handleUpdate" :multiline="true" />
          </td>
        </tr>
        <tr>
          <td class="label-cell">8.证据清单（可另附页）</td>
          <td class="content-cell tall-cell">
            附页
          </td>
        </tr>
      </tbody>
    </table>

    <div class="footer-section">
      <div class="signature-line">具状人（签字、盖章）：____________________</div>
      <div class="date-line">日期：&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;年&nbsp;&nbsp;&nbsp;&nbsp;月&nbsp;&nbsp;&nbsp;&nbsp;日</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, defineComponent, h } from 'vue'

const props = defineProps({
  blocks: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['updateSlotValue'])

const plaintiff = ref({
  name: '',
  gender: '',
  birthday: '',
  ethnicity: '',
  work_unit: '',
  job_title: '',
  phone: '',
  domicile: '',
  habitual_residence: ''
})

const agent = ref({
  has_agent: false,
  name: '',
  work_place: '',
  job: '',
  phone: '',
  auth: ''
})

const defendant = ref({
  name: '',
  address: '',
  legal_rep: '',
  phone: '',
  social_credit_code: '',
  company_address: '',
  entity_type: '',
  is_state_owned: false,
  job: ''
})

const service = ref({
  address: '',
  recipient: '',
  phone: '',
  allow_electronic: false,
  wechat: '',
  mail: ''
})

const claims = ref({
  salary: { active: false, details: '' },
  double_salary: { active: false, details: '' },
  overtime: { active: false, details: '' },
  annual_leave: { active: false, details: '' },
  social_loss: { active: false, details: '' },
  termination_compensation: { active: false, details: '' },
  illegal_termination_damages: { active: false, details: '' },
  other_requests: '',
  litigation_cost_burden: ''
})

const preservation = ref({
  active: false,
  court: '',
  document: ''
})

const facts = ref({
  contract_signing: '',
  performance_details: '',
  arbitration_details: '',
  is_migrant_worker: '',
  legal_basis: '',
  termination_reason: '',
  work_injury: ''
})

const claimsList = computed(() => ({
  salary: { label: '是否主张工资支付', data: claims.value.salary },
  double_salary: { label: '是否主张未签订书面劳动合同双倍工资', data: claims.value.double_salary },
  overtime: { label: '是否主张加班费', data: claims.value.overtime },
  annual_leave: { label: '是否主张未休年休假工资', data: claims.value.annual_leave },
  social_loss: { label: '是否主张未依法缴纳社会保险费造成的经济损失', data: claims.value.social_loss },
  termination_compensation: { label: '是否主张解除劳动合同经济补偿', data: claims.value.termination_compensation },
  illegal_termination_damages: { label: '是否主张违法解除劳动合同赔偿金', data: claims.value.illegal_termination_damages },
  other_requests: { label: '本表未列明的其他请求', value: claims.value.other_requests, isSimple: true },
  litigation_cost: { label: '诉讼费用承担', value: claims.value.litigation_cost_burden, isSimple: true }
}))

const getSlotValue = (blockSlots, slotName) => {
  if (blockSlots && blockSlots[slotName]) {
    return blockSlots[slotName].value || ''
  }
  return ''
}

const handleUpdate = (blockId, slotName, newValue) => {
  console.log('更新槽位:', blockId, slotName, newValue)
  emit('updateSlotValue', blockId, slotName, newValue)
}

const handleToggle = (blockId, slotName, newValue) => {
  console.log('切换布尔值:', blockId, slotName, '->', newValue)
  emit('updateSlotValue', blockId, slotName, newValue)
}

const EditableField = defineComponent({
  name: 'EditableField',
  props: {
    value: { type: String, default: '' },
    fieldKey: { type: String, required: true },
    blockId: { type: String, required: true },
    multiline: { type: Boolean, default: false }
  },
  emits: ['update'],
  setup(props, { emit }) {
    const isEditing = ref(false)
    const editValue = ref('')

    const startEdit = () => {
      editValue.value = props.value || ''
      isEditing.value = true
    }

    const saveEdit = () => {
      if (editValue.value !== props.value) {
        emit('update', props.blockId, props.fieldKey, editValue.value)
      }
      isEditing.value = false
    }

    const cancelEdit = () => {
      editValue.value = props.value || ''
      isEditing.value = false
    }

    return () => {
      if (isEditing.value) {
        if (props.multiline) {
          return h('div', { class: 'edit-container' }, [
            h('textarea', {
              class: 'edit-textarea',
              value: editValue.value,
              onInput: (e) => { editValue.value = e.target.value },
              rows: 4
            }),
            h('div', { class: 'edit-buttons' }, [
              h('button', { class: 'edit-btn save-btn', onClick: saveEdit }, '保存'),
              h('button', { class: 'edit-btn cancel-btn', onClick: cancelEdit }, '取消')
            ])
          ])
        } else {
          return h('div', { class: 'edit-container' }, [
            h('input', {
              class: 'edit-input',
              type: 'text',
              value: editValue.value,
              onInput: (e) => { editValue.value = e.target.value },
              onKeyup: (e) => { if (e.key === 'Enter') saveEdit() }
            }),
            h('button', { class: 'edit-btn save-btn', onClick: saveEdit }, '✓'),
            h('button', { class: 'edit-btn cancel-btn', onClick: cancelEdit }, '✗')
          ])
        }
      } else {
        return h('span', {
          class: 'editable-field',
          onClick: startEdit,
          title: '点击编辑'
        }, props.value || '点击填写')
      }
    }
  }
})

watch(() => props.blocks, (newBlocks) => {
  console.log('blocks 数据更新:', newBlocks)
  
  if (newBlocks.plaintiff) {
    const slots = newBlocks.plaintiff.slots
    plaintiff.value = {
      name: getSlotValue(slots, 'name'),
      gender: getSlotValue(slots, 'gender'),
      birthday: getSlotValue(slots, 'birthday'),
      ethnicity: getSlotValue(slots, 'ethnicity'),
      work_unit: getSlotValue(slots, 'work_unit'),
      job_title: getSlotValue(slots, 'job_title'),
      phone: getSlotValue(slots, 'phone'),
      domicile: getSlotValue(slots, 'domicile'),
      habitual_residence: getSlotValue(slots, 'habitual_residence')
    }
  }

  if (newBlocks.agent) {
    const slots = newBlocks.agent.slots
    agent.value = {
      has_agent: getSlotValue(slots, 'has_agent') === true || getSlotValue(slots, 'has_agent') === 'true',
      name: getSlotValue(slots, 'name'),
      work_place: getSlotValue(slots, 'work_place'),
      job: getSlotValue(slots, 'job'),
      phone: getSlotValue(slots, 'phone'),
      auth: getSlotValue(slots, 'auth')
    }
  }

  if (newBlocks.defendant) {
    const slots = newBlocks.defendant.slots
    defendant.value = {
      name: getSlotValue(slots, 'name'),
      address: getSlotValue(slots, 'address'),
      legal_rep: getSlotValue(slots, 'legal_rep'),
      job: getSlotValue(slots, 'job'),
      phone: getSlotValue(slots, 'phone'),
      social_credit_code: getSlotValue(slots, 'social_credit_code'),
      company_address: getSlotValue(slots, 'company_address'),
      entity_type: getSlotValue(slots, 'entity_type'),
      is_state_owned: getSlotValue(slots, 'is_state_owned') === true || getSlotValue(slots, 'is_state_owned') === 'true'
    }
  }

  if (newBlocks.service) {
    const slots = newBlocks.service.slots
    service.value = {
      address: getSlotValue(slots, 'address'),
      recipient: getSlotValue(slots, 'recipient'),
      phone: getSlotValue(slots, 'phone'),
      allow_electronic: getSlotValue(slots, 'allow_electronic') === true || getSlotValue(slots, 'allow_electronic') === 'true',
      wechat: getSlotValue(slots, 'wechat'),
      mail: getSlotValue(slots, 'mail')
    }
  }

  if (newBlocks.claims) {
    const slots = newBlocks.claims.slots
    claims.value = {
      salary: {
        active: getSlotValue(slots, 'salary.active') === true || getSlotValue(slots, 'salary.active') === 'true',
        details: getSlotValue(slots, 'salary.details')
      },
      double_salary: {
        active: getSlotValue(slots, 'double_salary.active') === true || getSlotValue(slots, 'double_salary.active') === 'true',
        details: getSlotValue(slots, 'double_salary.details')
      },
      overtime: {
        active: getSlotValue(slots, 'overtime.active') === true || getSlotValue(slots, 'overtime.active') === 'true',
        details: getSlotValue(slots, 'overtime.details')
      },
      annual_leave: {
        active: getSlotValue(slots, 'annual_leave.active') === true || getSlotValue(slots, 'annual_leave.active') === 'true',
        details: getSlotValue(slots, 'annual_leave.details')
      },
      social_loss: {
        active: getSlotValue(slots, 'social_loss.active') === true || getSlotValue(slots, 'social_loss.active') === 'true',
        details: getSlotValue(slots, 'social_loss.details')
      },
      termination_compensation: {
        active: getSlotValue(slots, 'termination_compensation.active') === true || getSlotValue(slots, 'termination_compensation.active') === 'true',
        details: getSlotValue(slots, 'termination_compensation.details')
      },
      illegal_termination_damages: {
        active: getSlotValue(slots, 'illegal_termination_damages.active') === true || getSlotValue(slots, 'illegal_termination_damages.active') === 'true',
        details: getSlotValue(slots, 'illegal_termination_damages.details')
      },
      other_requests: getSlotValue(slots, 'other_requests'),
      litigation_cost_burden: getSlotValue(slots, 'litigation_cost_burden')
    }
  }

  if (newBlocks.preservation) {
    const slots = newBlocks.preservation.slots
    preservation.value = {
      active: getSlotValue(slots, 'active') === true || getSlotValue(slots, 'active') === 'true',
      court: getSlotValue(slots, 'court') || '',
      document: getSlotValue(slots, 'document') || ''
    }
  }

  if (newBlocks.facts) {
    const slots = newBlocks.facts.slots
    facts.value = {
      contract_signing: getSlotValue(slots, 'contract_signing'), //1.劳动合同签订情况
      performance_details: getSlotValue(slots, 'performance_details'),  //2.劳动合同履行情况
      arbitration_details: getSlotValue(slots, 'arbitration_details'), //5.劳动仲裁相关情况
      is_migrant_worker: getSlotValue(slots, 'is_migrant_worker') , //6.其他相关情况
      legal_basis: getSlotValue(slots, 'legal_basis'), //7.诉请依据
      termination_reason: getSlotValue(slots, 'termination_reason'),  //3.解除或终止劳动关系情况
      work_injury: getSlotValue(slots, 'work_injury') //4.工伤情况
    }
  }
}, { deep: true, immediate: true })
</script>

<style scoped>
.legal-document-container {
  width: 210mm;
  min-height: 297mm;
  margin: 0 auto;
  padding: 15mm 20mm;
  background: white;
  font-family: "SimSun", "STSong", serif;
  color: #000;
  line-height: 1.6;
  font-size: 14px;
}

.document-title {
  text-align: center;
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 8px;
  letter-spacing: 2px;
}

.document-subtitle {
  text-align: center;
  font-size: 20px;
  margin-bottom: 25px;
  font-weight: bold;
}

.instruction-box {
  border: 1px solid #000;
  padding: 15px;
  font-size: 13px;
  margin-bottom: 0;
  background: #fafafa;
}

.instruction-title {
  font-weight: bold;
  margin-bottom: 8px;
  font-size: 14px;
}

.instruction-text {
  margin-bottom: 8px;
}

.instruction-list {
  margin: 10px 0;
  padding-left: 25px;
}

.instruction-list li {
  margin-bottom: 5px;
  line-height: 1.6;
}

.warning-text {
  font-weight: bold;
  text-align: center;
  margin: 12px 0 8px 0;
  font-size: 14px;
}

.warning-content {
  line-height: 1.6;
  text-indent: 2em;
}

.legal-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0;
}

.legal-table td {
  border: 1px solid #000;
  padding: 10px 8px;
  vertical-align: top;
  font-size: 14px;
  line-height: 1.8;
}

.label-cell {
  width: 25%;
  text-align: left;
  font-weight: bold;
  background-color: #f5f5f5;
  padding-left: 15px;
}

.content-cell {
  width: 75%;
  padding-left: 15px;
}

.section-header-main {
  background-color: #f0f0f0;
  text-align: center;
  font-weight: bold;
  font-size: 16px;
  padding: 12px 8px;
}

.info-line {
  margin-bottom: 6px;
  line-height: 1.8;
}

.checkbox-inline {
  margin-bottom: 8px;
  font-weight: bold;
  display: inline-flex;
  gap: 10px;
}

.checkbox-item {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 3px;
  transition: background-color 0.2s;
  display: inline-block;
}

.checkbox-item:hover {
  background-color: #e8f4ff;
}

.underline {
  border-bottom: 1px solid #000;
  display: inline-block;
  min-width: 100px;
  text-align: center;
}

.footer-section {
  margin-top: 60px;
  text-align: right;
  padding-right: 20px;
}

.signature-line, .date-line {
  margin-bottom: 20px;
  font-size: 15px;
  line-height: 2;
}

.ml-4 {
  margin-left: 1rem;
}

.tall-cell {
  min-height: 80px;
  white-space: pre-wrap;
}

.editable-field {
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 3px;
  transition: background-color 0.2s;
  display: inline-block;
  min-width: 50px;
}

.editable-field:hover {
  background-color: #e8f4ff;
  border: 1px dashed #409eff;
  padding: 1px 5px;
}

.edit-container {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.edit-input {
  padding: 4px 8px;
  border: 1px solid #409eff;
  border-radius: 4px;
  font-size: 14px;
  font-family: inherit;
  min-width: 150px;
}

.edit-textarea {
  padding: 8px;
  border: 1px solid #409eff;
  border-radius: 4px;
  font-size: 14px;
  font-family: inherit;
  width: 100%;
  resize: vertical;
}

.edit-buttons {
  display: flex;
  gap: 5px;
  margin-top: 5px;
}

.edit-btn {
  padding: 2px 8px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}

.save-btn {
  background-color: #409eff;
  color: white;
}

.save-btn:hover {
  background-color: #66b1ff;
}

.cancel-btn {
  background-color: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
}

.cancel-btn:hover {
  background-color: #e6e6e6;
}

.inline-edit {
  display: inline-block;
}
</style>
