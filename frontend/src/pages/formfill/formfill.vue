<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from "element-plus"
import { Expand, CirclePlusFilled, Fold } from '@element-plus/icons-vue'
import histortCard from '../../components/historyCard/formfillHistortCard.vue'
import { useHistoryChatStore } from "../../store/history_chat_msg"
import { useRouter, useRoute } from 'vue-router'
import "md-editor-v3/lib/style.css"
import { getSessionListAPI, getFormFillSessionInfoAPI, deleteFormFillSessionAPI, startFormFillSessionAPI, getTemplateListAPI, sendMessageForFormFillAPI, getFormFillStatusAPI, updateSlotValueAPI, getFinalDocumentAPI, downloadDocumentAPI } from '../../apis/formfill'
import type { formfillSession, block, formfillSessionDetail, formTemplate } from '../../type/formfill'
import { useUserStore } from '@/store/user'
import { template } from 'lodash'
import labor_dispute from '@/components/formfill/labor_dispute.vue'

const router = useRouter()
const userStore = useUserStore()
const route = useRoute()
const historyChatStore = useHistoryChatStore()
const searchKeyword = ref('') //用于在会话列表中查找会话
const selectedSession = ref('') //选中会话的ID
const inputMessage = ref('') //搜索框输入的内容
const currentSessionId = ref<string>('')  // 当前会话ID
const chatConversationRef = ref<HTMLElement | null>(null)  // 聊天容器引用
const isGenerating = ref(false)  // 是否正在生成回复
const userId = computed(() => userStore.userInfo.user_id) // 用户ID，实际使用中应从用户状态获取
const sessions = ref<formfillSession[]>([])// 会话列表List数据
const sessionsTotal = ref<number>(0) // 会话总数
const loading = ref(false) //加载状态
const messages = ref<formfillSessionDetail[]>([]) //当前会话消息列表
const current_block = ref<string>('') // 当前模块
const completion_rate = ref<number>(0) // 当前的完成度
const blocks = ref<Record<string, any>>({}) // 所有模块的槽位信息
const templates = ref<formTemplate[]>([]) // 模板列表
const document_url = ref<string>('') //下载文档的URl
const success = ref<boolean>(false) //文档是否可以下载 
const showSessionList = ref(true) // 是否显示会话列表
const selectedTemplate = ref<string>('') //选中的模板
const showFormFill = ref<boolean>(false) //是否显示表单填写界面

// 打开创建对话框
const openCreateSession = async () => {
  inputMessage.value = ''
  selectedSession.value = ''
  messages.value = []
  selectedTemplate.value = ''
  showFormFill.value = false
  document_url.value = ''
  success.value = false
  blocks.value = {}
  completion_rate.value = 0
  current_block.value = ''
  isGenerating.value = false
  currentSessionId.value = ''
  await fetchSessions()
  await fetchTemplate()
}

//切换收起会话列表 ok
const toggleSessionList = () => {
  showSessionList.value = !showSessionList.value
}

//切换显示表单填写界面 ok
const toggleFormFill = () => {
  showFormFill.value = !showFormFill.value
}

// 获取对话列表 ok
const fetchSessions = async () => {
  try {
    loading.value = true
    const response = await getSessionListAPI(userId.value)
    if (response.data.code === 200) {
      // 根据新的后端数据结构处理：response.data.data.sessions (数组) 和 response.data.data.total
      console.log('原始对话数据:', response.data.data)
      console.log('总会话数:', response.data.data.total)

      // 直接使用 sessions 数组
      sessions.value = response.data.data.sessions.map((item: any) => ({
        session_id: item.session_id,
        template_type: item.template_type,
        current_block: item.current_block,
        conversation_turn: item.conversation_turn,
        created_at: item.created_at,
        updated_at: item.updated_at,
      }))

      sessionsTotal.value = response.data.total

      console.log('对话列表获取成功:', sessions.value)
    } else {
      ElMessage.error(`获取对话列表失败: ${response.data.status_message}`)
    }
  } catch (error) {
    console.error('获取对话列表出错:', error)
    ElMessage.error('获取对话列表失败，请检查网络连接')
  } finally {
    loading.value = false
  }
}


// 选择会话查询当前会话的详情
const selectSession = async (session_id: string) => {
  try {
    await openCreateSession()
    
    const response = await getFormFillSessionInfoAPI(session_id)
    if (response.data.code === 200) {
      console.log('查询某个会话得到的消息', response.data.data)

      const sessionData = response.data.data
      
      if (sessionData) {
        selectedTemplate.value = sessionData.template_type || ''
        currentSessionId.value = sessionData.session_id || session_id
        
        if (sessionData.messages && Array.isArray(sessionData.messages)) {
          messages.value = sessionData.messages.map((msg: any) => ({
            role: msg.role as 'user' | 'assistant',
            message: msg.message || '',
            timestamp: msg.timestamp,
          }))
        }
        
        console.log('已加载会话历史，消息数量:', messages.value.length)
        console.log('消息详情:', messages.value)
        console.log('当前模板:', selectedTemplate.value)
        
        await fetchFormFillStatus()
        await fetchSessions()
        scrollToBottom()
      }
    }

  } catch (error) {
    console.error('查询会话出错:', error)
    ElMessage.error('查询会话失败，请检查网络连接')
  }
}

// 删除会话 ok
const deleteSession = async (session_id: string) => {
  console.log('删除会话被调用，session_id:', session_id)
  try {
    const response = await deleteFormFillSessionAPI(session_id)
    if (response.data.code === 200) {
      ElMessage({
        message: '会话删除成功',
        type: 'success',
        duration: 3000,
        showClose: false
      })
      // 重新获取对话列表
      await fetchSessions()
      if (selectedSession.value === session_id) {
        selectedSession.value = ''
      }
    } else {
      ElMessage.error(`删除会话失败: ${response.data.status_message}`)
    }
  } catch (error) {
    console.error('删除会话出错:', error)
    ElMessage.error('删除会话失败，请检查网络连接')
  }
}

//获取文书模板 ok
const fetchTemplate = async () => {
  try {
    const response = await getTemplateListAPI()
    if (response.data.code === 200) {
      console.log('获取模板列表成功:', response.data.data.templates)

      templates.value = response.data.data.templates.map((item: any) => ({
        template_type: item.template_type,
        template_name: item.template_name,
        template_file: item.template_file,
        block_count: item.block_count,
      }))

    } else {
      ElMessage.error(`获取模板列表失败: ${response.data.status_message}`)
      return []
    }
  } catch (error) {
    console.error('获取模板列表出错:', error)
    ElMessage.error('获取模板列表失败，请检查网络连接')
    return []
  }
}

//选取文书模板开启对话 ok
const selectTemplate = async (template_type: string, template_name?: string) => {
  console.log('选择文书模板被调用，template_type:', template_type, 'template_name:', template_name)
  try {
    // if (template_name) {
    //   await ElMessageBox.confirm(`确定要使用「${template_name}」模板吗？`, '确认选择模板', {
    //     confirmButtonText: '确定',
    //     cancelButtonText: '取消',
    //     type: 'info',
    //     customClass: 'template-confirm-dialog'
    //   })
    // }

    const response = await startFormFillSessionAPI( userId.value,template_type)
    if (response.data.code === 200) {
      currentSessionId.value = response.data.data.session_id
      selectedTemplate.value = template_type
      messages.value.push({ role: 'assistant' as const, message: response.data.data.message || '', timestamp: new Date().toISOString() })
      await fetchSessions()
      console.log('messages:', messages.value)
      ElMessage.success('模板选择成功，开始填写文档')
    } else {
      ElMessage.error(`获取模板列表失败: ${response.data.status_message}`)
    }
  } catch (error) {
    if (template_name) {
      console.log('用户取消了模板选择')
    } else {
      console.error('获取模板列表出错:', error)
      ElMessage.error('获取模板列表失败，请检查网络连接')
    }
  }
}

//根据选取的文档模板计算出文档模板组件名 ok
const formfillComponent = computed(() => {
  // 映射表：将后端的 template_type 字符串映射为 Vue 组件对象
  const templateMap: Record<string, any> = {
    'labor_dispute': labor_dispute,
    // 'divorce': divorce_dispute, // 预留扩展
  }

  // 获取当前的模板标识符
  // 优先取选中的模板，如果没有（比如刷新页面），则看当前会话的模板类型
  const type = selectedTemplate.value || ''

  // 返回对应的组件，如果没有匹配到，默认返回 labor_dispute 或 null
  if (templateMap[type]) {
    return templateMap[type]
  }

  // 回退逻辑：如果没有任何匹配，可以返回一个默认组件防止页面白屏
  console.warn(`未找到类型为 [${type}] 的模板组件，已回退到默认模板`)
  return labor_dispute 
})

// 发送消息 ok
const handleSend = async () => {
  if (!inputMessage.value.trim()) {
    ElMessage.warning('请输入消息内容')
    return
  }

  if (isGenerating.value) {
    ElMessage.warning('请等待当前回复完成')
    return
  }

  const question = inputMessage.value.trim()

  console.log('query:', question)
  console.log('session_id:', currentSessionId.value)

  isGenerating.value = true

  console.log('将用户消息加入 messages')
  messages.value.push({ role: 'user' as const, message: question, timestamp: new Date().toISOString() })

  await nextTick()
  scrollToBottom()

  try {
    const response = await sendMessageForFormFillAPI(currentSessionId.value, question, userId.value)
    console.log('API 完整响应:', response)
    console.log('response.data:', response.data)
    console.log('response.data.data:', response.data.data)
    
    if (response.data.code === 200) {
      console.log('消息发送成功，后端响应:', response.data.data)
      
      const aiMessage = response.data.data.answer || response.data.data.message || response.data.data.response || ''
      console.log('AI 回复内容:', aiMessage)

      messages.value.push({ 
        role: 'assistant' as const, 
        message: aiMessage, 
        timestamp: new Date().toISOString() 
      })

      console.log('添加 AI 消息后的 messages:', messages.value)
      console.log('messages 长度:', messages.value.length)

      await nextTick()

      await fetchFormFillStatus()
      await fetchSessions()

      scrollToBottom()
      isGenerating.value = false
    } else {
      isGenerating.value = false
      ElMessage.error(`消息发送失败: ${response.data.status_message}`)
    }

    inputMessage.value = ''

  } catch (e) {
    console.error('RAG 模式对话异常', e)
    ElMessage.error('对话异常')
    isGenerating.value = false
  }
}

//获取当前填写状态
const fetchFormFillStatus = async () => {
  try {
    const response = await getFormFillStatusAPI(currentSessionId.value)
    if (response.data.code === 200) {
      console.log('获取当前填写状态成功:', response.data.data)
      const data = response.data.data
      blocks.value = data.blocks || {}
      completion_rate.value = data.overall_completion_rate || 0
      current_block.value = data.current_block || ''
    } else {
      ElMessage.error(`获取当前填写状态失败: ${response.data.status_message}`)
    }
  } catch (error) {
    console.error('获取当前填写状态出错:', error)
    ElMessage.error('获取当前填写状态失败，请检查网络连接')
  }
}
//手动更新槽位值 ok
const updateSlotValue = async (block_id:string,slot_name:string,slot_value:string) =>{
  blocks.value[slot_name] = slot_value
  await nextTick()
  try {
    await updateSlotValueAPI(currentSessionId.value,block_id,slot_name,slot_value)
    await fetchFormFillStatus()
  } catch (error) {
    console.error('更新槽位值出错:', error)
    ElMessage.error('更新槽位值失败，请检查网络连接')
  }
}



//生成最终文档
const generateForm = async () => {
  try {
    const response = await getFinalDocumentAPI(currentSessionId.value)
    if (response.data.code === 200) {
      if (response.data.data.success) {
        success.value = true
        document_url.value = response.data.data.document_url
        ElMessage.success('文书生成成功')
      } else {
        ElMessage.error('文书生成失败，请稍后重试')
      }

    }
  } catch (error) {
    ElMessage.error('获取文书状态失败，请检查网络连接')
  }
}

//下载生成的文档
const downloadDocument = async () => {
  if (!success.value || !document_url.value) {
    ElMessage.warning('文书尚未生成，请稍后')
    return
  }

  try {
    const response = await downloadDocumentAPI(currentSessionId.value)
    if (response.data.code === 200) {
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `generated_document_${currentSessionId.value}.docx`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } else {
      ElMessage.error(`下载文书失败: ${response.data.status_message}`)
    }
  } catch (error) {
    console.error('下载文书出错:', error)
    ElMessage.error('下载文书失败，请检查网络连接')
  }
}

// 键盘事件处理 ok
const handleKeydown = (event: KeyboardEvent) => {
  // 直接回车发送，Shift+Enter 换行
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    // 如果正在生成，不响应回车
    if (!isGenerating.value) {
      handleSend()
    }
  }
}

// 自动滚动到底部 ok
const scrollToBottom = () => {
  if (chatConversationRef.value) {
    setTimeout(() => {
      if (chatConversationRef.value) {
        chatConversationRef.value.scrollTop = chatConversationRef.value.scrollHeight
      }
    }, 100)
  }
}

// 头像加载错误处理 ok
const handleAvatarError = (event: Event) => {
  const target = event.target as HTMLImageElement
  if (target) {
    target.src = '/src/assets/user.svg'
  }
}


onMounted(async () => {
  await fetchSessions()
  await fetchTemplate()
  // 检查是否有 session_id 参数，如果有则加载会话历史
  const sessionId = route.query.session_id as string
  if (sessionId) {
    console.log('加载已有会话:', sessionId)
    currentSessionId.value = sessionId  // 设置当前会话ID
    await selectSession(sessionId)
  }
})


// 监听路由参数变化
watch(
  () => route.query.session_id,
  async (newSessionId, oldSessionId) => {
    if (newSessionId && newSessionId !== oldSessionId) {
      console.log('检测到会话ID变化:', oldSessionId, '->', newSessionId)
      // 更新当前会话ID
      currentSessionId.value = newSessionId as string
      // 清空当前消息
      messages.value = []
      // 加载新会话的历史
      await fetchSessions()
    }
  }
)

</script>

<template>
  <div class="homepage">

    <!-- 左侧边栏 -->
    <div class="sidebar" v-if="showSessionList">
      <div class="create-section">
        <button @click="openCreateSession" class="create-btn-native">
          <div class="btn-content">
            <span class="icon">+</span>
            <span>新建会话</span>
          </div>
        </button>

        <button @click="toggleSessionList" class="collapse-btn-native">
          <div class="btn-content">
            <el-icon>
              <Fold />
            </el-icon>
          </div>
        </button>
      </div>

      <!-- 会话列表标题 -->
      <div class="list-header">
        <span class="title">会话列表</span>
        <span class="count">({{ sessions.length }})</span>
      </div>

      <!-- 会话列表 -->
      <div class="session-list">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <div class="loading-icon">⏳</div>
          <div class="loading-text">正在加载会话列表...</div>
        </div>
        <!-- 空状态 -->
        <div v-else-if="sessions.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <div class="empty-text">
            {{ searchKeyword ? '没有找到相关会话' : '暂无会话记录' }}
          </div>
          <div v-if="!searchKeyword" class="empty-hint">
            点击上方按钮开始新的对话
          </div>
        </div>
        <!-- 用 histortCard 渲染会话卡片 -->
        <histortCard v-for="formfillSession in sessions" :key="formfillSession.session_id" :item="formfillSession"
          :class="{ active: selectedSession === formfillSession.session_id }"
          @select="selectSession(formfillSession.session_id)" @delete="deleteSession(formfillSession.session_id)" />
      </div>
    </div>

    <!-- 右侧主体区域 -->
    <div class="content">
      <div class="chat-page" :class="{ 'chat-active': messages.length > 0 }">
        <!-- 顶部操作按钮区域 -->
        <div v-if="!showSessionList" class="expand-create-section">
          <button @click="toggleSessionList" class="expand-btn-native">
            <div class="btn-content">
              <el-icon>
                <Expand />
              </el-icon>
            </div>
          </button>
          <button @click="openCreateSession" class="create-btn-native">
            <div class="btn-content">
              <el-icon>
                <CirclePlusFilled />
              </el-icon>
            </div>
          </button>
        </div>

        <div class="main-content">

          <!-- 对话区 -->
          <div class="main-content-left">
            <div v-if="selectedTemplate" class="show-form-button">
            <!-- <div class="show-form-button"> -->
              <el-button @click="toggleFormFill" class="form-button">{{ showFormFill ? '收起文档' : '查看文档' }}</el-button>
            </div>
            <!-- 对话内容容器 - 占据剩余空间并支持滚动 -->
            <div v-if="messages.length > 0" class="chat-conversation-container">
              <div class="chat-conversation" ref="chatConversationRef">
                <div v-for="(msg, idx) in messages" :key="idx" class="message-group">
                  <!-- User Message -->
                  <div v-if="msg.role === 'user'" class="user-message">
                    <div class="message-content">
                      <span>{{ msg.message }}</span>
                    </div>
                    <img :src="userStore.userInfo?.avatar || '/src/assets/user.svg'" alt="User Avatar" class="avatar"
                      @error="handleAvatarError" />
                  </div>

                  <div v-if="msg.role === 'assistant'" class="ai-message">
                    <img src="/src/assets/robot.svg" alt="AI Avatar" class="avatar" />
                    <div class="message-content">
                      <span>{{ msg.message }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 底部区域（包含欢迎界面和输入框） -->
            <div class="bottom-section">
              <!-- 欢迎界面（无对话时显示） -->
              <div v-if="!selectedTemplate" class="welcome-section">
                <div class="avatar-wrapper">
                  <img src="../../assets/robot.svg" alt="智言" class="avatar" />
                </div>
                <h1 class="welcome-title">在文档生成前请先选择模板</h1>

                <!-- 展示各种模板 -->
                <div class="template-list" v-if="!selectedTemplate">
                  <div v-for="template in templates" :key="template.template_name" class="template-item"
                    @click="selectTemplate(template.template_type, template.template_name)">
                    <h3>{{ template.template_name }}</h3>
                  </div>
                </div>

              </div>

              <!-- 输入区域（始终在底部） -->
              <div class="input-section">
                <div class="input-wrapper">
                  <textarea v-model="inputMessage" placeholder="给智言发消息，让智言帮你完成任务~" class="message-input" rows="4"
                    @keydown="handleKeydown"></textarea>

                  <!-- 底部控制栏 -->
                  <div class="input-footer">
                    <div class="footer-left">
                    </div>

                    <div class="footer-right">
                      <!-- 发送按钮 -->
                      <button class="send-btn" :class="{ 'btn-disabled': isGenerating }" :disabled="isGenerating"
                        @click="handleSend">
                        <span v-if="!isGenerating && selectedTemplate">➤</span>
                        <span v-else class="loading-spinner"></span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 文档展示区 -->
          <div class="main-content-right" v-if="showFormFill && formfillComponent">
            <div class="document-section">
              <!-- 动态调用模板组件 -->
              <component :is="formfillComponent" :blocks="blocks"  @updateSlotValue="updateSlotValue"/>
            </div>

            <!-- <div class="document-download-section" v-if="success"> -->
            <div class="document-download-section">
              <div class="demo-progress">
                <span class="current-progress">当前进度:</span>
                <el-progress :text-inside="true" :stroke-width="26" :percentage="completion_rate*100"
                  style="display: inline-block; vertical-align: middle; width: calc(100% - 80px);" />
              </div>
              <button class="download-btn" @click="generateForm">生成文书</button>
              <!-- 在生成成功后显示包含 URL 的下载按钮 -->
              <button 
                v-if="success && document_url" 
                class="download-url-btn" 
                @click="downloadDocument">
                {{ document_url }}
              </button>
            </div>
          </div>
        </div>


      </div>
    </div>

  </div>
</template>

<style lang="scss" scoped>
.homepage {
  display: flex;
  height: calc(100vh - 60px);
  background-color: #ffffff;

  /* 禁止根节点产生全局滚动，滚动仅在对话内容区出现 */
  overflow: hidden;

  .sidebar {
    height: 100%;
    width: 280px;
    background-color: #ffffff;
    border-right: 1px solid #e9ecef;
    display: flex;
    flex-direction: column;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);

    .create-section {
      display: flex;
      flex-direction: row;
      justify-content: space-between;
      align-items: center;
      padding: 20px 16px 16px;
      border-bottom: 1px solid #f0f0f0;

      .create-btn-native {
        width: 150px;
        height: 48px;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #74c0fc 0%, #4b9fe2 100%);
        color: white;
        border: none;
        cursor: pointer;
        font-size: 14px;

        &:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(116, 192, 252, 0.4);
        }

        &:active {
          transform: translateY(0);
        }

        .btn-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;

          .icon {
            font-size: 18px;
            font-weight: bold;
          }
        }
      }

      .collapse-btn-native {
        width: 50px;
        height: 48px;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #74c0fc 0%, #4b9fe2 100%);
        color: white;
        border: none;
        cursor: pointer;
        font-size: 14px;

        &:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(116, 192, 252, 0.4);
        }

        &:active {
          transform: translateY(0);
        }

        .btn-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;

          .icon {
            font-size: 18px;
            font-weight: bold;
          }

          .el-icon {
            font-size: 24px;
          }
        }
      }

    }

    .search-section {
      padding: 16px;
      border-bottom: 1px solid #f0f0f0;

      .search-input-wrapper {
        position: relative;
        display: flex;
        align-items: center;

        .search-icon {
          position: absolute;
          left: 12px;
          color: #9ca3af;
          font-size: 14px;
          z-index: 1;
        }

        .search-input {
          width: 100%;
          padding: 8px 12px 8px 36px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          font-size: 14px;
          background: #f9fafb;
          transition: all 0.2s ease;

          &:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
          }

          &::placeholder {
            color: #9ca3af;
          }
        }
      }
    }

    .list-header {
      padding: 16px 16px 8px;
      display: flex;
      align-items: center;
      gap: 4px;

      .title {
        font-size: 14px;
        font-weight: 600;
        color: #1f2937;
      }

      .count {
        font-size: 12px;
        color: #6b7280;
      }
    }

    .session-list {
      flex: 1;
      padding: 0 8px;
      overflow-y: auto;

      .loading-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        color: #3b82f6;

        .loading-icon {
          font-size: 48px;
          margin-bottom: 16px;
          animation: spin 1s linear infinite;
        }

        .loading-text {
          font-size: 14px;
          color: #6b7280;
        }
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        color: #9ca3af;

        .empty-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }

        .empty-text {
          font-size: 14px;
          margin-bottom: 8px;
        }

        .empty-hint {
          font-size: 12px;
          color: #d1d5db;
        }
      }

      .session-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        min-height: 80px;
        position: relative;

        &:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
          transform: translateY(-2px);
        }

        &.active {
          border-color: #3b82f6;
          background-color: #eff6ff;
        }

        .avatar {
          position: absolute;
          top: 16px;
          left: 16px;
          width: 40px;
          height: 40px;
          border-radius: 8px;
          overflow: hidden;

          img {
            width: 100%;
            height: 100%;
            object-fit: cover;
          }
        }

        .title {
          position: absolute;
          top: 16px;
          left: 68px;
          right: 60px;
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .delete-btn {
          position: absolute;
          top: 16px;
          right: 16px;
          width: 32px;
          height: 32px;
          padding: 4px;
          background: rgba(255, 255, 255, 0.9);
          border: 1px solid #e5e7eb;
          cursor: pointer;
          border-radius: 4px;
          transition: all 0.2s ease;
          font-size: 14px;
          opacity: 0;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          user-select: none;
          pointer-events: auto;
          outline: none;

          &:hover {
            background: #fee2e2;
            color: #dc2626;
            border-color: #dc2626;
            opacity: 1;
          }

          &:active {
            transform: scale(0.95);
          }
        }

        &:hover .delete-btn {
          opacity: 1 !important;
          background: #fee2e2 !important;
          color: #dc2626 !important;
          border-color: #dc2626 !important;
        }

        .time {
          position: absolute;
          bottom: 8px;
          right: 16px;
          font-size: 11px;
          color: #9ca3af;
        }
      }
    }
  }

  .content {
    flex: 1;
    height: 100%;
    background-color: #ffffff;
    border-radius: 0;
    margin: 0;
    box-shadow: none;
    border-left: 1px solid #e9ecef;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    .chat-page {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: white;
      overflow: hidden;
      flex: 1;

      // &.chat-active {
      //   background: linear-gradient(135deg, #f0f4ff 0%, #d9e8ff 100%);
      // }

      .expand-create-section {
        display: flex;
        flex-direction: row;
        justify-content: flex-start;
        align-items: center;
        padding: 16px;
        gap: 12px;

        // 展开按钮样式优化
        .expand-btn-native {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          transition: all 0.2s ease;
          background: linear-gradient(135deg, #74c0fc 0%, #4b9fe2 100%);
          color: white;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          margin-right: 8px;

          &:hover {
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(116, 192, 252, 0.4);
          }

          &:active {
            transform: scale(0.95);
          }

          .btn-content {
            display: flex;
            align-items: center;
            justify-content: center;

            :deep(.el-icon) {
              font-size: 18px;
              color: white;
            }
          }
        }

        // 创建按钮样式
        .create-btn-native {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          transition: all 0.2s ease;
          background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
          color: white;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;

          &:hover {
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(103, 194, 58, 0.4);
          }

          &:active {
            transform: scale(0.95);
          }

          .btn-content {
            display: flex;
            align-items: center;
            justify-content: center;

            :deep(.el-icon) {
              font-size: 18px;
              color: white;
            }
          }
        }

      }

      .main-content {
        display: flex;
        flex: 1;
        overflow: hidden;

        .main-content-left {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          position: relative;
          border-radius: 10px;
          background-color: linear-gradient(135deg, #f0f4ff 0%, #d9e8ff 100%);

          .show-form-button {
            position: absolute;
            top: 16px;
            right: 16px;
            z-index: 10;

            .form-button {
              /* 基础定位与尺寸 */
              align-self: flex-start;
              min-width: 90px;
              /* 稍微增加一点宽度，让文字不那么拥挤 */
              height: 36px;
              padding: 0 16px;

              /* 核心样式 */
              background-color: #3b82f6;
              /* 经典的克莱因蓝，很有科技感 */
              color: #ffffff;
              border: none;
              border-radius: 8px;
              /* 圆角是现代感的灵魂 */

              /* 字体样式 */
              font-size: 14px;
              font-weight: 500;
              cursor: pointer;

              /* 动画过渡 */
              transition: all 0.3s ease;

              /* 微微的投影，增加层级感 */
              box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);

              /* 悬停效果 (Hover) */
              &:hover {
                background-color: #2563eb;
                /* 颜色加深 */
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                transform: translateY(-1px);
                /* 轻轻向上浮动 */
              }

              /* 点击效果 (Active) */
              &:active {
                transform: translateY(0);
                box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
              }
            }
          }

        }

        .main-content-right {
          position: relative;
          width: 50%;
          height: 100%;
          border-left: 1px solid #e9ecef;
          padding: 0 20px;
          display: flex;
          flex-direction: column;

          .document-section {
            flex: 1;
            overflow: auto;
            background-color: #f5f5f5;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 80px;

            &::-webkit-scrollbar {
              width: 8px;
              height: 8px;
            }

            &::-webkit-scrollbar-track {
              background: #f1f1f1;
              border-radius: 4px;
            }

            &::-webkit-scrollbar-thumb {
              background: #888;
              border-radius: 4px;

              &:hover {
                background: #555;
              }
            }
          }

          .document-download-section {
            flex-shrink: 0;
            padding: 15px 0;
            display: flex;
            flex-direction: column;
            gap: 10px;

            .demo-progress {
              display: flex;
              justify-content: flex-start;
              align-items: center;
              width: 100%;

              .current-progress {
                width: 100px;
              }
            }

            .download-btn {
              /* 基础定位与尺寸 */
              align-self: flex-start;
              min-width: 90px;
              /* 稍微增加一点宽度，让文字不那么拥挤 */
              height: 36px;
              padding: 0 16px;

              /* 核心样式 */
              background-color: #3b82f6;
              /* 经典的克莱因蓝，很有科技感 */
              color: #ffffff;
              border: none;
              border-radius: 8px;
              /* 圆角是现代感的灵魂 */

              /* 字体样式 */
              font-size: 14px;
              font-weight: 500;
              cursor: pointer;

              /* 动画过渡 */
              transition: all 0.3s ease;

              /* 微微的投影，增加层级感 */
              box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);

              /* 悬停效果 (Hover) */
              &:hover {
                background-color: #2563eb;
                /* 颜色加深 */
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                transform: translateY(-1px);
                /* 轻轻向上浮动 */
              }

              /* 点击效果 (Active) */
              &:active {
                transform: translateY(0);
                box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
              }
            }

            .download-url-btn {
              /* 基础定位与尺寸 */
              align-self: flex-start;
              min-width: 200px;
              max-width: 100%;
              height: 36px;
              padding: 0 16px;

              /* 核心样式 - 成功绿色 */
              background-color: #10b981;
              color: #ffffff;
              border: none;
              border-radius: 8px;

              /* 字体样式 */
              font-size: 13px;
              font-weight: 500;
              cursor: pointer;
              text-overflow: ellipsis;
              overflow: hidden;
              white-space: nowrap;

              /* 动画过渡 */
              transition: all 0.3s ease;

              /* 微微的投影，增加层级感 */
              box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);

              margin-top: 8px;

              /* 悬停效果 (Hover) */
              &:hover {
                background-color: #059669;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                transform: translateY(-1px);
              }

              /* 点击效果 (Active) */
              &:active {
                transform: translateY(0);
                box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
              }
            }
          }
        }
      }
    }

    .chat-conversation-container {
      flex: 1;
      min-height: 0;
      /* 只在对话区域出现滚动条 */
      overflow-y: auto;
      overflow-x: hidden;
      // background-color: #f7f8fa;
      /* 为左右两侧保留空隙，且使用 box-sizing 避免宽度溢出 */
      padding: 18px 16px;
      box-sizing: border-box;
      top:40px;

      &::-webkit-scrollbar {
        width: 6px;
        position: absolute;
        right: 0;
      }

      &::-webkit-scrollbar-track {
        background: transparent;
        margin: 4px 0;
      }

      // &::-webkit-scrollbar-thumb {
      //   background: rgba(193, 199, 208, 0.6);
      //   border-radius: 3px;

      //   &:hover {
      //     background: rgba(168, 176, 188, 0.8);
      //   }
      // }
    }

    .chat-conversation {
      width: 100%;
      max-width: 100%;
      margin: 0;
      /* 消息内容由外层容器提供左右间距，这里保持较小内边距以避免重复 */
      padding: 0 8px 10px;

      @media (min-width: 769px) {
        max-width: 1100px;
        margin: 0 auto;
        padding: 0 12px 15px;
      }
    }

    .bottom-section {
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      padding: 0;
      border-top: 1px solid #e9ecef;
      flex-shrink: 0;
      width: 100%;
    }

    .welcome-section {
      text-align: center;
      padding: 60px 20px;
      animation: fadeInUp 0.6s ease;

      .avatar-wrapper {
        margin-bottom: 20px;
        display: flex;
        justify-content: center;
        position: relative;

        .avatar {
          width: 120px;
          height: 120px;
          object-fit: contain;
          transition: all 0.3s ease;
          filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.08));

          &:hover {
            transform: scale(1.05);
            filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.12));
          }
        }
      }

      .welcome-title {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #1f2937 0%, #4b5563 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 12px 0;
        letter-spacing: -0.5px;
      }

      .welcome-subtitle {
        font-size: 15px;
        color: #6b7280;
        margin: 0;
        line-height: 1.7;
        max-width: 500px;
        margin: 0 auto;
      }

      .template-list {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        max-width: 800px;
        margin: 30px auto 0;
        padding: 0 20px;
        justify-content: center;

        .template-item {
          background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
          border: 1px solid #e5e7eb;
          border-radius: 24px;
          padding: 10px 20px;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
          text-align: center;
          font-size: 14px;
          color: #4b5563;
          font-weight: 500;
          white-space: nowrap;

          &:hover {
            border-color: #667eea;
            color: #667eea;
            background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
          }

          &:active {
            transform: translateY(0);
          }
        }
      }
    }

    .mode-selector {
      display: flex;
      gap: 14px;
      margin-bottom: 36px;
      animation: fadeInUp 0.6s ease 0.1s both;

      .mode-btn {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 24px;
        border: 2px solid #e5e7eb;
        border-radius: 24px;
        background: white;
        color: #6b7280;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);

        .mode-icon {
          font-size: 18px;
          transition: transform 0.3s ease;
        }

        .mode-label {
          font-weight: 600;
        }

        &:hover {
          border-color: #667eea;
          background: #f8f9ff;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);

          .mode-icon {
            transform: scale(1.1);
          }
        }

        &.active {
          border-color: #667eea;
          background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          color: #667eea;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
          transform: translateY(-2px);

          .mode-icon {
            transform: scale(1.15);
          }
        }
      }
    }

    // 动画
    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }

      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes rotate {
      from {
        transform: translate(-50%, -50%) rotate(0deg);
      }

      to {
        transform: translate(-50%, -50%) rotate(360deg);
      }
    }

    @keyframes bounce {

      0%,
      80%,
      100% {
        transform: scale(0) translateY(0);
        opacity: 0.5;
      }

      40% {
        transform: scale(1.2) translateY(-8px);
        opacity: 1;
      }
    }

    // 灵寻模式输入框外发光“呼吸”动画（淡蓝色，颜色不变，仅强弱变化）
    @keyframes lingseek-breath {

      0%,
      100% {
        box-shadow:
          0 0 0 2px rgba(102, 126, 234, 0.12),
          0 0 24px 10px rgba(102, 126, 234, 0.14);
      }

      50% {
        box-shadow:
          0 0 0 3px rgba(102, 126, 234, 0.22),
          0 0 44px 18px rgba(102, 126, 234, 0.22);
      }
    }

    @keyframes lingseek-breath-strong {

      0%,
      100% {
        box-shadow:
          0 0 0 3px rgba(102, 126, 234, 0.20),
          0 0 36px 14px rgba(102, 126, 234, 0.24);
      }

      50% {
        box-shadow:
          0 0 0 4px rgba(102, 126, 234, 0.30),
          0 0 60px 24px rgba(102, 126, 234, 0.30);
      }
    }

    // 移除彩虹动画（不再需要）

    .input-section {
      width: 100%;
      max-width: 100%;
      margin: 0;
      padding: 10px;
      animation: fadeInUp 0.6s ease 0.2s both;

      // 响应式适配
      @media (min-width: 769px) {
        max-width: 1200px;
        margin: 0 auto;
        padding: 15px;
      }

      .input-wrapper {
        background: #ffffff;
        border: 2px solid #e5e7eb;
        border-radius: 16px;
        margin: 12px 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        position: relative;
        z-index: 1;

        // 响应式适配
        @media (max-width: 768px) {
          margin: 10px 12px;
          border-radius: 12px;
        }

        &:focus-within {
          border-color: #667eea;
          box-shadow: 0 6px 24px rgba(102, 126, 234, 0.15);
        }

        .message-input {
          position: relative;
          top: 5px;
          left: 5px;
          width: 100%;
          border: none;
          background: transparent;
          font-size: 15px;
          line-height: 1.6;
          color: #1f2937;
          resize: none;
          outline: none;
          font-family: inherit;
          min-height: 45px;
          margin-bottom: 12px;

          &::placeholder {
            color: #9ca3af;
          }
        }

        .input-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .footer-left {
            display: flex;
            gap: 10px;

            .selector-dropdown {
              position: relative;

              .selector-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 14px;
                background: #f8f9fa;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                font-size: 13px;
                color: #4b5563;
                cursor: pointer;
                transition: all 0.2s ease;
                user-select: none;

                .selector-icon {
                  font-size: 16px;
                }

                .selector-icon-img {
                  width: 20px;
                  height: 20px;
                  object-fit: contain;
                  display: inline-block;
                }

                .selector-text {
                  font-weight: 500;
                }

                .selector-arrow {
                  font-size: 10px;
                  opacity: 0.5;
                  transition: transform 0.2s ease;
                }

                &.open {
                  .selector-arrow {
                    transform: rotate(180deg);
                  }
                }

                .selector-check {
                  font-size: 14px;
                  color: #667eea;
                  font-weight: 600;
                }

                &:hover {
                  border-color: #667eea;
                  background: #f0f4ff;
                  color: #667eea;
                }

                &.active {
                  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                  border-color: #667eea;
                  color: #667eea;
                  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.15);
                }

                &:active {
                  transform: scale(0.98);
                }
              }

              .dropdown-menu {
                position: absolute;
                bottom: calc(100% + 8px);
                left: 0;
                min-width: 200px;
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                max-height: 320px;
                overflow: hidden;
                display: flex;
                flex-direction: column;

                &.tool-menu {
                  min-width: 360px;
                  max-height: 450px;
                }

                // 模型下拉尺寸与rag列表保持一致
                &.model-menu {
                  min-width: 180px;
                  max-height: 450px;

                  .dropdown-item {
                    .item-content {
                      .item-text {
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                      }
                    }
                  }
                }

                .dropdown-header {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  padding: 12px 16px;
                  background: linear-gradient(135deg, #f8f9fa 0%, #f0f2f5 100%);
                  border-bottom: 1px solid #e5e7eb;

                  .header-title {
                    font-size: 14px;
                    font-weight: 600;
                    color: #1f2937;
                  }

                  .header-count {
                    font-size: 12px;
                    color: #6b7280;
                    background: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    border: 1px solid #e5e7eb;
                  }
                }

                .dropdown-list {
                  flex: 1;
                  overflow-y: auto;
                  padding: 8px;

                  &::-webkit-scrollbar {
                    width: 8px;
                  }

                  &::-webkit-scrollbar-track {
                    background: transparent;
                  }

                  &::-webkit-scrollbar-thumb {
                    background: #e0e0e0;
                    border-radius: 4px;

                    &:hover {
                      background: #bdbdbd;
                    }
                  }
                }

                .dropdown-empty {
                  padding: 48px 20px;
                  text-align: center;
                  color: #9ca3af;
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  gap: 12px;

                  .empty-icon {
                    font-size: 48px;
                    opacity: 0.3;
                  }

                  .empty-icon-img {
                    width: 48px;
                    height: 48px;
                    opacity: 0.35;
                    object-fit: contain;
                  }

                  .empty-text {
                    font-size: 14px;
                    color: #6b7280;
                  }
                }

                .dropdown-item {
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  gap: 12px;
                  padding: 14px 12px;
                  border-radius: 10px;
                  cursor: pointer;
                  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                  margin-bottom: 4px;
                  border: 2px solid transparent;
                  background: #fafafa;

                  .item-left {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    flex: 1;
                    min-width: 0;
                  }

                  .item-icon-wrapper {
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
                    border-radius: 10px;
                    flex-shrink: 0;
                    transition: all 0.3s ease;
                    overflow: hidden;

                    .item-icon-img {
                      width: 100%;
                      height: 100%;
                      object-fit: cover;
                    }

                    .item-icon {
                      font-size: 20px;
                    }
                  }

                  .item-content {
                    flex: 1;
                    min-width: 0;

                    .item-text {
                      font-size: 15px;
                      font-weight: 600;
                      color: #1f2937;
                      margin-bottom: 4px;
                      line-height: 1.3;
                    }

                    .item-desc {
                      font-size: 12px;
                      color: #6b7280;
                      overflow: hidden;
                      text-overflow: ellipsis;
                      display: -webkit-box;
                      -webkit-line-clamp: 2;
                      line-clamp: 2;
                      -webkit-box-orient: vertical;
                      line-height: 1.5;
                    }
                  }

                  .item-check-wrapper {
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 50%;
                    flex-shrink: 0;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);

                    .item-check {
                      font-size: 16px;
                      color: white;
                      font-weight: 700;
                    }
                  }

                  &:hover {
                    background: #f5f7fa;
                    transform: translateX(2px);
                    border-color: #e5e7eb;

                    .item-icon-wrapper {
                      background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
                      transform: scale(1.05);
                    }
                  }

                  &.selected {
                    background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%);
                    border-color: #667eea;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.12);

                    .item-icon-wrapper {
                      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);

                      .item-icon-img {
                        filter: brightness(1.2);
                      }

                      .item-icon {
                        filter: brightness(0) invert(1);
                      }
                    }

                    .item-text {
                      color: #667eea;
                    }
                  }

                  &:active {
                    transform: scale(0.98) translateX(2px);
                  }
                }

                .dropdown-footer {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  padding: 12px 16px;
                  border-top: 2px solid #f0f0f0;
                  background: linear-gradient(135deg, #fafbfc 0%, #f5f7fa 100%);

                  .clear-btn {
                    padding: 8px 16px;
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    font-size: 13px;
                    color: #6b7280;
                    cursor: pointer;
                    transition: all 0.25s ease;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                    gap: 6px;

                    &:hover {
                      background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                      border-color: #ef4444;
                      color: #dc2626;
                      transform: translateY(-1px);
                      box-shadow: 0 2px 6px rgba(239, 68, 68, 0.2);
                    }

                    &:active {
                      transform: translateY(0);
                    }
                  }

                  .selected-info {
                    display: flex;
                    align-items: center;
                    gap: 8px;

                    .selected-count {
                      font-size: 13px;
                      color: #667eea;
                      font-weight: 600;
                      padding: 4px 12px;
                      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                      border-radius: 12px;
                      border: 1px solid #667eea;
                    }
                  }
                }
              }
            }
          }

          .footer-right {
            display: flex;
            gap: 10px;
            align-items: center;

            .icon-btn {
              width: 36px;
              height: 36px;
              display: flex;
              align-items: center;
              justify-content: center;
              background: #f8f9fa;
              border: 1px solid #e5e7eb;
              border-radius: 8px;
              cursor: pointer;
              transition: all 0.2s ease;
              font-size: 18px;

              &:hover {
                border-color: #667eea;
                background: #f0f4ff;
                transform: translateY(-1px);
              }

              &:active {
                transform: translateY(0);
              }
            }

            .hidden-file-input {
              display: none;
            }

            .upload-icon {
              width: 18px;
              height: 18px;
              object-fit: contain;
              display: block;
            }

            .send-btn {
              position: relative;
              right: 4px;
              bottom: 4px;
              width: 36px;
              height: 36px;
              display: flex;
              align-items: center;
              justify-content: center;
              background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
              border: none;
              border-radius: 8px;
              color: white;
              cursor: pointer;
              transition: all 0.2s ease;
              font-size: 16px;
              box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);

              &:hover:not(.btn-disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(59, 130, 246, 0.35);
              }

              &:active:not(.btn-disabled) {
                transform: translateY(0);
              }

              &.btn-disabled {
                background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
                cursor: not-allowed;
                opacity: 0.6;
              }

              .loading-spinner {
                animation: spin 1s linear infinite;
              }
            }

            @keyframes spin {
              from {
                transform: rotate(0deg);
              }

              to {
                transform: rotate(360deg);
              }
            }
          }
        }
      }
    }

    .chat-conversation {
      width: 100%;
      scroll-behavior: smooth; // 平滑滚动

      .message-group {
        width: 100%;
        margin-bottom: 20px;
        /* 移除单独的宽边距，使用父容器的 padding 保持统一间距 */
        padding: 0;

        &:first-child {
          padding-top: 6px;
        }
      }

      .ai-message {
        display: flex;
        align-items: flex-start;
        justify-content: flex-start;

        .avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          margin-right: 15px;
          flex-shrink: 0;
          border: 1px solid #eee;
        }

        .message-content {
          background-color: #ffffff;
          border-radius: 18px;
          padding: 12px 18px;
          max-width: 70%;
          color: #333;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
          word-break: break-word;

          // 加载转圈器样式
          .loading-spinner-container {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 4px 0;
            color: #6b7280;
            font-size: 14px;

            .loading-spinner {
              width: 16px;
              height: 16px;
              border: 2px solid #d1d5db;
              border-top: 2px solid transparent;
              border-radius: 50%;
              animation: spin 1s linear infinite;
            }

            .loading-text {
              font-weight: 500;
              color: #9ca3af;
            }
          }
        }
      }

      .user-message {
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;

        .avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          margin-left: 12px;
          flex-shrink: 0;
          border: 1px solid #eee;
        }

        .message-content {
          display: flex;
          align-items: center;
          background: linear-gradient(135deg, #6e8efb, #a777e3);
          color: white;
          border-radius: 18px;
          padding: 12px 18px;
          max-width: 70%;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
      }
    }

    // 下拉菜单动画（向上展开）
    .dropdown-enter-active,
    .dropdown-leave-active {
      transition: all 0.2s ease;
    }

    .dropdown-enter-from {
      opacity: 0;
      transform: translateY(8px);
    }

    .dropdown-leave-to {
      opacity: 0;
      transform: translateY(4px);
    }

    // Override MdPreview background
    :deep(.md-editor-preview-wrapper) {
      background-color: transparent !important;
    }

    // 引用来源样式
    .sources-section {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid #e5e7eb;

      .sources-title {
        font-size: 13px;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .source-item {
        background-color: #f9fafb;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;

        &:hover {
          border-color: #d1d5db;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .source-content {
          margin-bottom: 8px;

          .source-text {
            font-size: 14px;
            line-height: 1.6;
            color: #374151;
            display: block;
          }
        }

        .source-metadata {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;

          .meta-item {
            display: inline-flex;
            align-items: center;
            font-size: 12px;
            padding: 3px 8px;
            background-color: #ffffff;
            border-radius: 4px;
            border: 1px solid #e5e7eb;

            .meta-label {
              color: #9ca3af;
              font-weight: 500;
              margin-right: 4px;
            }

            .meta-value {
              color: #4b5563;
              font-weight: 500;
            }
          }
        }
      }
    }

    /* Rerank 开关样式（可通过 aria-checked="true" 或 .active/.on 切换样式） */
    switch {
      display: inline-block;
      width: 44px;
      height: 24px;
      border-radius: 12px;
      background: #eef2ff;
      position: relative;
      cursor: pointer;
      vertical-align: middle;
      transition: background 0.18s ease, box-shadow 0.18s ease;
      box-shadow: inset 0 1px 2px rgba(16, 24, 40, 0.04);
    }

    switch::after {
      content: '';
      position: absolute;
      left: 2px;
      top: 2px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #ffffff;
      box-shadow: 0 2px 6px rgba(2, 6, 23, 0.12);
      transition: left 0.18s ease, transform 0.18s ease;
    }

    /* 激活态样式（支持 aria-checked 或类名） */
    switch[aria-checked="true"],
    switch.active,
    switch.on {
      background: linear-gradient(90deg, #4b9fe2, #6e8efb);
    }

    switch[aria-checked="true"]::after,
    switch.active::after,
    switch.on::after {
      left: 22px;
      transform: translateX(0);
    }

    switch:focus {
      outline: none;
      box-shadow: 0 0 0 4px rgba(74, 144, 226, 0.12);
    }

    /* 小尺寸变种 */
    switch.small {
      width: 36px;
      height: 20px;
      border-radius: 10px;
    }

    switch.small::after {
      width: 16px;
      height: 16px;
      left: 2px;
      top: 2px;
    }
  }
}
</style>

<style lang="scss">
.template-confirm-dialog {
  .el-message-box {
    border-radius: 12px !important;
    padding: 20px !important;

    .el-message-box__header {
      padding-bottom: 15px;

      .el-message-box__title {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #1f2937 !important;
      }
    }

    .el-message-box__content {
      padding: 15px 0;

      .el-message-box__message {
        font-size: 15px !important;
        color: #4b5563 !important;
        line-height: 1.6 !important;
      }
    }

    .el-message-box__btns {
      padding-top: 15px;

      .el-button--primary {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;

        &:hover {
          background-color: #2563eb !important;
          border-color: #2563eb !important;
        }
      }

      .el-button--default {
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
      }
    }
  }
}
</style>
