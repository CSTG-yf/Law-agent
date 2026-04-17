<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from "element-plus"
import { Expand, CirclePlusFilled, Fold } from '@element-plus/icons-vue'
import { getAgentsAPI } from "../../apis/agent"
import histortCard from '../../components/historyCard/cyberJudgeHistoryCard.vue'
import { useRouter, useRoute } from 'vue-router'
import { MdPreview } from "md-editor-v3"
import "md-editor-v3/lib/style.css"
import { getSessionListAPI, getSessionAPI, deleteSessionAPI, sendMessageStream, uploadFile } from '../../apis/cyberJudge'
import { useUserStore } from '../../store/user'
import type { analyzepayload } from '../../apis/cyberJudge'

const router = useRouter()
const userStore = useUserStore()
const route = useRoute()
const searchKeyword = ref('') //用于在会话列表中查找会话
const inputMessage = ref('') //搜索框输入的内容
const currentSessionId = ref<string>('')  // 当前会话ID
const chatConversationRef = ref<HTMLElement | null>(null)  // 聊天容器引用
const fileInputRef = ref<HTMLInputElement | null>(null)  // 文件输入引用
const isGenerating = ref(false)  // 是否正在生成回复
const rerank = ref(false) // 是否启用重排序
const userId = computed(() => userStore.userInfo.user_id) // 用户ID，实际使用中应从用户状态获取
const sessions = ref<session[]>([]) // 会话列表，类型根据后端返回的数据结构定义
const sessionsTotal = ref<number>(0) // 会话总数
const loading = ref(false) // 是否正在加载会话列表
const messages = ref<Array<message>>([]) // 消息列表，包含用户消息和AI回复，类型根据后端返回的数据结构定义
const showSessionList = ref(true) // 是否显示会话列表
const currentProgress = ref('')
const currentFactsSummary = ref('')
//当前的sources列表
const currentSources = ref<file[]>([])
//需要上传的文件列表
const Files = ref<File[]>([])


interface session {
  session_id: string
  user_id: string
  created_at: string
  message_count: number
  title: string
}

interface lawItem {
  title: string
  publisher?: string
  publish_date?: string
  timeliness?: string
  law_id?: string
  content_preview?: string
}

interface caseItem {
  title: string
  case_number?: string
  court?: string
  judgement_date?: string
  cause?: string
  content_preview?: string
}

interface message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  sources?: file[]
  related_laws?: lawItem[]
  related_cases?: caseItem[]
}

interface file {
  file_id: string
  file_name: string
  file_type: string
  file_path: string
  file_size: number
  upload_time: string
}

interface request{
  message:string
  session_id?:string
  user_id:string
  file_paths:string[]
  stream:boolean
  max_history:number
}

//切换收起会话列表
const toggleSessionList = () => {
  showSessionList.value = !showSessionList.value
}


// 打开创建对话框
const openCreateSession = async () => {
  inputMessage.value = ''              // 清空输入框
  messages.value = []
  currentSessionId.value = ''
  currentProgress.value = ''
  currentFactsSummary.value = ''
  currentSources.value = [] // 清空当前文件 sources
  Files.value = [] // 清空上传文件列表
  fetchSessions()
}

// 获取对话列表
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
        user_id: item.user_id, // 使用 session_id 作为显示名称
        created_at: item.created_at,
        message_count: item.message_count,
        title: item.title
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

// 删除会话
const deleteSession = async (session_id: string) => {
  console.log('删除会话被调用，session_id:', session_id)
  try {
    const response = await deleteSessionAPI(session_id)
    if (response.data.code === 200) {
      ElMessage({
        message: '会话删除成功',
        type: 'success',
        duration: 3000,
        showClose: false
      })
      // 重新获取对话列表
      await fetchSessions()
      if (currentSessionId.value === session_id) {
        currentSessionId.value = ''
      }
    } else {
      ElMessage.error(`删除会话失败: ${response.data.status_message}`)
    }
  } catch (error) {
    console.error('删除会话出错:', error)
    ElMessage.error('删除会话失败，请检查网络连接')
  }
}

// 选择会话列表中的会话
const selectSession = async (session_id: string) => {
  // 更新当前会话ID
  currentSessionId.value = session_id
  try {
    const response = await getSessionAPI(session_id)
    if (response.data.code === 200) {
      console.log('查询某个会话得到的消息', response.data.data)

      // 替换当前 messages 内容为查询到的会话历史
      if (response.data.data && response.data.data.messages && Array.isArray(response.data.data.messages)) {
        // 直接使用后端返回的 messages 数组，保持完整的数据结构（包括 sources）
        messages.value = response.data.data.messages.map((msg: any) => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content || '',
          timestamp: msg.timestamp,
          sources: msg.sources || [], //TODO: 处理 sources 字段
          related_laws: msg.related_laws || [],
          related_cases: msg.related_cases || [],
        }))

        console.log('已加载会话历史，消息数量:', messages.value.length)
        console.log('消息详情:', messages.value)

        //处理返回的sources信息 TODO: 处理 sources 字段
        // currentSources.value = response.data.data.messages.sources.map((file:any) => ({
        //   file_id: file.file_id,
        //   file_name: file.file_name,
        //   file_type: file.file_type,
        //   file_path: file.file_path,
        //   file_size: file.file_size,
        //   upload_time: file.upload_time,
        // }))

        // 重新获取会话列表
        await fetchSessions()

        // 自动滚动到底部
        scrollToBottom()
      }
    }

  } catch (error) {
    console.error('查询会话出错:', error)
    ElMessage.error('查询会话失败，请检查网络连接')
  }
}

// 发送消息
const handleSend = () => {
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

  currentProgress.value = ''
  currentFactsSummary.value = ''
  inputMessage.value = ''
  isGenerating.value = true
  messages.value.push({ role: 'user' as const, content: question })

  scrollToBottom()

  const assistantMessage = { role: 'assistant' as const, content: '', timestamp: '' }
  messages.value.push(assistantMessage)

  const payload: analyzepayload = {
    message: question,
    user_id: userId.value,
    file_paths: currentSources.value.map((file:any) => file.file_path),
    max_history: 20,
    stream: true,
  }

  if (currentSessionId.value) {
    payload.session_id = currentSessionId.value
  }

  console.log('准备调用 sendMessage，payload:', payload)

  sendMessageStream(payload, {
    onMetadata(data: any) {
      if (data?.session_id) {
        currentSessionId.value = data.session_id
      }
    },
    onProgress(data: any) {
      currentProgress.value = data?.message || ''
    },
    onFactsSummary(data: any) {
      currentFactsSummary.value = data?.summary || ''
      scrollToBottom()
    },
    onToken(data: any) {
      currentProgress.value = '正在输出分析结果...'
      if (data?.content) {
        assistantMessage.content += data.content
        scrollToBottom()
      }
    },
    onTitle(data: any) {
      if (data?.title) {
        fetchSessions()
      }
    },
    onComplete(data: any) {
      currentProgress.value = ''
      if (data?.content) {
        assistantMessage.content = data.content
      }
      assistantMessage.related_laws = data?.related_laws || []
      assistantMessage.related_cases = data?.related_cases || []
      scrollToBottom()
    },
    onError(data: any) {
      console.error('流式响应错误', data)
      ElMessage.error(data?.message || '对话异常')
      currentProgress.value = ''
      isGenerating.value = false
    },
    onDone() {
      currentProgress.value = ''
      isGenerating.value = false
      fetchSessions()
    }
  }).catch((e: any) => {
    console.error('赛博判官对话异常', e)
    ElMessage.error('对话异常')
    currentProgress.value = ''
    isGenerating.value = false
  })
}

//上传多个文件
const uploadFiles = async (files: File[]) => {
  console.log('开始上传文件:', files)
  for (const file of files) {
    console.log('上传文件:', file)
    const response = await uploadFile(file)
    if (response.data.code === 200) {
      console.log('文件上传成功:', response.data.data)
      // 将上传后的文件信息添加到 currentSources
      currentSources.value.push({
        file_id: response.data.data.file_id,
        file_name: response.data.data.filename,
        file_type: response.data.data.file_type,
        file_path: response.data.data.file_path,
        file_size: response.data.data.file_size,
        upload_time: response.data.data.upload_time,
      })
      console.log('currentSources:', currentSources.value)
    } else {
      ElMessage.error(`文件上传失败: ${response.data.status_message}`)
    }
  }
  console.log('currentSources:', currentSources.value)
  ElMessage.success('所有文件上传成功')
  // 上传文件完成之后，清空上传文件列表
  Files.value = []
} 

// 文件选择变化处理，用户选择文件后， onFileChange 事件被触发，调用 uploadFiles 开始上传
const onFileChange = (event: Event) => {
  console.log('文件选择变化:', event)
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const filesArray = Array.from(target.files)
    Files.value = filesArray
    console.log('上传文件:', filesArray)
    uploadFiles(filesArray)
    // 清空input值，允许重复选择同一文件
    target.value = ''
  }
}

// 触发文件选择，浏览器弹出文件选择对话框
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 移除已上传的文件
const removeFile = (index: number) => {
  currentSources.value.splice(index, 1)
}


// 键盘事件处理
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

// 自动滚动到底部
const scrollToBottom = () => {
  if (chatConversationRef.value) {
    setTimeout(() => {
      if (chatConversationRef.value) {
        chatConversationRef.value.scrollTop = chatConversationRef.value.scrollHeight
      }
    }, 100)
  }
}

// 头像加载错误处理
const handleAvatarError = (event: Event) => {
  const target = event.target as HTMLImageElement
  if (target) {
    target.src = '/src/assets/user.svg'
  }
}


onMounted(async () => {
  fetchSessions()
  // 检查是否有 session_id 参数，如果有则加载会话历史
  const sessionId = route.query.session_id as string
  if (sessionId) {
    console.log('加载已有会话:', sessionId)
    currentSessionId.value = sessionId  // 设置当前会话ID
    await getSessionAPI(sessionId)
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
      await getSessionAPI(newSessionId as string)
    }
  }
)

</script>

<template>
  <div class="homepage">

    <!-- 左侧边栏 -->
    <div class="sidebar" v-if="showSessionList">
      <!-- 新建会话按钮 -->
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
        <histortCard v-for="session in sessions" :key="session.session_id" :item="session"
          :class="{ active: currentSessionId === session.session_id }" @select="selectSession(session.session_id)"
          @delete="deleteSession(session.session_id)" />
      </div>
    </div>

    <!-- 右侧主体区域 -->
    <div class="content">
      <div class="chat-page" :class="{ 'chat-active': messages.length > 0 }">
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

        <!-- 对话内容容器 - 占据剩余空间并支持滚动 -->
        <div v-if="messages.length > 0" class="chat-conversation-container">
          <div class="chat-conversation" ref="chatConversationRef">
            <div v-for="(msg, idx) in messages" :key="idx" class="message-group">
              <!-- User Message -->
              <div v-if="msg.role === 'user'" class="user-message">
                <div class="message-content">
                  <span>{{ msg.content }}</span>
                </div>
                <img :src="userStore.userInfo?.avatar || '/src/assets/user.svg'" alt="User Avatar" class="avatar"
                  @error="handleAvatarError" />
              </div>

              <!-- AI Message -->
              <div v-if="msg.role === 'assistant'" class="ai-message">
                <img src="/src/assets/robot.svg" alt="AI Avatar" class="avatar" />
                <div class="message-content">
                  <!-- 加载转圈器 - 仅在内容为空且正在生成时显示 -->
                  <div v-if="!msg.content && isGenerating && idx === messages.length - 1"
                    class="loading-spinner-container">
                    <div class="loading-spinner"></div>
                    <span class="loading-text">{{ currentProgress || 'AI 正在思考中...' }}</span>
                  </div>
                  <div v-if="currentFactsSummary && idx === messages.length - 1" class="facts-summary-card">
                    <div class="facts-summary-title">已识别文件事实</div>
                    <div class="facts-summary-content">{{ currentFactsSummary }}</div>
                  </div>
                  <div v-if="msg.related_laws?.length" class="result-card laws-card">
                    <div class="result-card-title">相关法律法规</div>
                    <div v-for="(law, lawIndex) in msg.related_laws" :key="`${idx}-law-${lawIndex}`" class="result-item">
                      <div class="result-item-name">{{ law.title }}</div>
                      <div class="result-item-meta">
                        <span v-if="law.publisher">{{ law.publisher }}</span>
                        <span v-if="law.publish_date">{{ law.publish_date }}</span>
                        <span v-if="law.timeliness">{{ law.timeliness }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-if="msg.related_cases?.length" class="result-card cases-card">
                    <div class="result-card-title">相关案例</div>
                    <div v-for="(legalCase, caseIndex) in msg.related_cases" :key="`${idx}-case-${caseIndex}`" class="result-item">
                      <div class="result-item-name">{{ legalCase.title }}</div>
                      <div class="result-item-meta">
                        <span v-if="legalCase.case_number">{{ legalCase.case_number }}</span>
                        <span v-if="legalCase.court">{{ legalCase.court }}</span>
                        <span v-if="legalCase.judgement_date">{{ legalCase.judgement_date }}</span>
                      </div>
                      <div v-if="legalCase.cause" class="result-item-extra">案由：{{ legalCase.cause }}</div>
                    </div>
                  </div>
                  <div v-if="msg.content && isGenerating && idx === messages.length - 1" class="streaming-text">{{ msg.content }}</div>
                  <!-- 实际内容 - 有内容时显示 -->
                  <MdPreview v-else-if="msg.content" :editorId="'workspace-ai-' + idx" :modelValue="msg.content" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部区域（包含欢迎界面和输入框） -->
        <div class="bottom-section">
          <!-- 欢迎界面（无对话时显示） -->
          <div v-if="messages.length === 0" class="welcome-section">
            <div class="avatar-wrapper">
              <img src="../../assets/robot.svg" alt="智言" class="avatar" />
            </div>
            <h1 class="welcome-title">我是智言小助手，很高兴见到你！</h1>
            <p class="welcome-subtitle">
              欢迎体验智言灵寻 LingSeek，一位懂得完成复杂任务的 Agent 助理~
            </p>
          </div>

          <!-- 输入区域（始终在底部） -->
          <div class="input-section">
            <!-- 已上传文件展示区域 -->
            <div v-if="currentSources.length > 0" class="uploaded-files">
              <div v-for="(file, index) in currentSources" :key="file.file_id" class="file-tag">
                <span class="file-name">{{ file.file_name }}</span>
                <span class="file-remove" @click="removeFile(index)">×</span>
              </div>
            </div>
            <div class="input-wrapper">
              <textarea v-model="inputMessage" placeholder="给智言发消息，让智言帮你完成任务~" class="message-input" rows="4"
                @keydown="handleKeydown"></textarea>

              <!-- 底部控制栏 -->
              <div class="input-footer">
                <div class="footer-left">

                </div>

                <div class="footer-right">
                  <!-- 附件按钮 -->
                  <button class="icon-btn" title="上传附件" @click="triggerFileInput">
                    <img src="../../assets/upload.svg" alt="上传" class="upload-icon" />
                  </button>
                  <input type="file" ref="fileInputRef" class="hidden-file-input" multiple @change="onFileChange" />

                  <!-- 发送按钮 -->
                  <button class="send-btn" :class="{ 'btn-disabled': isGenerating }" :disabled="isGenerating"
                    @click="handleSend">
                    <span v-if="!isGenerating">➤</span>
                    <span v-else class="loading-spinner"></span>
                  </button>
                </div>
              </div>
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

      &.chat-active {
        background: white;
      }

      .expand-create-section {
        display: flex;
        flex-direction: row;
        justify-content: flex-start;
        align-items: center;
        padding: 16px;
        gap: 12px;

        // 展开按钮样式
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
    }




    .chat-conversation-container {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 18px 16px;
      box-sizing: border-box;

      &::-webkit-scrollbar {
        width: 6px;
        position: absolute;
        right: 0;
      }

      &::-webkit-scrollbar-track {
        background: transparent;
        margin: 4px 0;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(193, 199, 208, 0.6);
        border-radius: 3px;

        &:hover {
          background: rgba(168, 176, 188, 0.8);
        }
      }
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
      background: white;
    }

    .welcome-section {
      flex: 1;
      text-align: center;
      padding: 60px 20px;
      animation: fadeInUp 0.6s ease;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;

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
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 16px;
        max-width: 800px;
        margin: 30px auto 0;
        padding: 0 20px;

        .template-item {
          background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          padding: 24px 20px;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
          text-align: center;

          &:hover {
            border-color: #3b82f6;
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2);
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          }

          &:active {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
          }

          .template-icon {
            font-size: 40px;
            margin-bottom: 12px;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
          }

          h3 {
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
            margin: 0 0 8px 0;
            line-height: 1.4;
          }

          .template-desc {
            font-size: 13px;
            color: #6b7280;
            margin: 0;
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
      margin: 0 auto;
      padding: 10px;
      animation: fadeInUp 0.6s ease 0.2s both;
      box-sizing: border-box;

      .uploaded-files {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 8px 16px;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;

        .file-tag {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          background-color: #e8f4ff;
          border: 1px solid #4B8EE6;
          border-radius: 6px;
          font-size: 12px;
          color: #4B8EE6;

          .file-name {
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .file-remove {
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            color: #4B8EE6;
            line-height: 1;

            &:hover {
              color: #2563eb;
            }
          }
        }
      }

      .input-wrapper {
        background: #ffffff;
        border: 2px solid #e5e7eb;
        border-radius: 16px;
        margin: 12px 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
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
          top:5px;
          left:5px;
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
            gap: 12px;
            align-items: center;

            .selector-dropdown {
              position: relative;
            }

            .rerank-btn {
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 6px 12px;
              background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
              border: 1px solid #e5e7eb;
              border-radius: 20px;
              font-size: 12px;
              color: #6b7280;
              cursor: pointer;
              transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
              box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

              .rerank-icon {
                font-size: 14px;
              }

              .rerank-text {
                font-weight: 500;
                font-size: 12px;
                white-space: nowrap;
                user-select: none;
              }

              &:hover {
                border-color: #667eea;
                background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
                color: #667eea;
                transform: translateY(-1px);
                box-shadow: 0 3px 8px rgba(102, 126, 234, 0.15);
              }

              &:active {
                transform: scale(0.98);
              }

              &.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-color: #667eea;
                color: white;
                box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
                transform: translateY(-1px);

                .rerank-icon {
                  animation: spin 1s linear infinite;
                }
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

            .selector-dropdown {

              .selector-item {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                border: 1px solid #e5e7eb;
                border-radius: 20px;
                font-size: 13px;
                color: #6b7280;
                cursor: pointer;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                user-select: none;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

                .selector-icon {
                  font-size: 14px;
                }

                .selector-icon-img {
                  width: 16px;
                  height: 16px;
                  object-fit: contain;
                  display: inline-block;
                }

                .selector-text {
                  font-weight: 500;
                  font-size: 12px;
                }

                .selector-arrow {
                  font-size: 10px;
                  opacity: 0.4;
                  transition: transform 0.2s ease;
                  margin-left: 2px;
                }

                &.open {
                  .selector-arrow {
                    transform: rotate(180deg);
                  }
                }

                .selector-check {
                  font-size: 12px;
                  color: #667eea;
                  font-weight: 600;
                }

                &:hover {
                  border-color: #667eea;
                  background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
                  color: #667eea;
                  transform: translateY(-1px);
                  box-shadow: 0 3px 8px rgba(102, 126, 234, 0.15);
                }

                &.active {
                  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  border-color: #667eea;
                  color: white;
                  box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
                  transform: translateY(-1px);

                  .selector-arrow {
                    opacity: 0.7;
                    color: white;
                  }
                }

                &:active {
                  transform: scale(0.98);
                }
              }

              .dropdown-menu {
                position: absolute;
                bottom: calc(100% + 10px);
                left: 50%;
                transform: translateX(-50%);
                min-width: 200px;
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.12);
                z-index: 1000;
                max-height: 320px;
                overflow: hidden;
                display: flex;
                flex-direction: column;

                &.tool-menu {
                  min-width: 320px;
                  max-height: 400px;
                }

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
                  padding: 14px 16px;
                  background: linear-gradient(135deg, #f8f9fa 0%, #f0f2f5 100%);
                  border-bottom: 1px solid #e5e7eb;
                  border-radius: 14px 14px 0 0;

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
              position:relative;
              right:4px;
              bottom:4px;
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

          .facts-summary-card {
            margin-bottom: 16px;
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid #b6e3ff;
            background: linear-gradient(135deg, #f3fbff 0%, #e8f7ff 100%);

            .facts-summary-title {
              font-size: 14px;
              font-weight: 600;
              color: #1677ff;
              margin-bottom: 8px;
            }

            .facts-summary-content {
              font-size: 14px;
              line-height: 1.8;
              color: #334155;
              white-space: pre-wrap;
            }
          }

          .streaming-text {
            font-size: 15px;
            line-height: 1.9;
            color: #334155;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .result-card {
            margin-bottom: 14px;
            padding: 12px 14px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            background: #f8fafc;

            &.laws-card {
              border-color: #c7e0ff;
              background: linear-gradient(135deg, #f7fbff 0%, #eef6ff 100%);
            }

            &.cases-card {
              border-color: #d9f0d0;
              background: linear-gradient(135deg, #f8fff5 0%, #f1faec 100%);
            }

            .result-card-title {
              font-size: 12px;
              font-weight: 600;
              color: #475569;
              margin-bottom: 10px;
            }

            .result-item {
              padding: 8px 0;
              border-top: 1px dashed rgba(148, 163, 184, 0.35);

              &:first-of-type {
                border-top: none;
                padding-top: 0;
              }

              &:last-of-type {
                padding-bottom: 0;
              }
            }

            .result-item-name {
              font-size: 12px;
              font-weight: 600;
              line-height: 1.6;
              color: #1e293b;
              margin-bottom: 4px;
            }

            .result-item-meta {
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
              font-size: 11px;
              line-height: 1.6;
              color: #64748b;
            }

            .result-item-extra {
              margin-top: 4px;
              font-size: 11px;
              line-height: 1.6;
              color: #475569;
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