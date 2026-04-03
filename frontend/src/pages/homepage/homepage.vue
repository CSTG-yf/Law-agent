<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from "element-plus"
import { getAgentsAPI } from "../../apis/agent"
import type { AgentResponse, ApiResponse } from "../../apis/agent"
import histortCard from '../../components/historyCard/histortCard.vue'
import { useHistoryChatStore } from "../../store/history_chat_msg"
import { useRouter, useRoute } from 'vue-router'
import { MdPreview } from "md-editor-v3"
import "md-editor-v3/lib/style.css"
import { getSessionListAPI, getSessionAPI, deleteSessionAPI, workspaceSimpleChatStreamAPI } from '../../apis/workspace'
import type { ChatRequest,  session } from '../../type'
import { useUserStore } from '../../store/user'

const router = useRouter()
const userStore = useUserStore()
const route = useRoute()
const historyChatStore = useHistoryChatStore()
const searchKeyword = ref('') //用于在会话列表中查找会话
const selectedSession = ref('') //选中会话的ID
const inputMessage = ref('') //搜索框输入的内容
const selectedMode = ref('')//查找方式选择（智能搜索、rag）
const selectedStrategy = ref<string>('')//rag检索模式
const showToolSelector = ref(false) //rag选择下拉框
const showMcpSelector = ref(false) //提供API选择下拉框
const selectedMcpServers = ref<string[]>([])
const mcpServers = ref<any[]>([])
const toolDropdownRef = ref<HTMLElement | null>(null)
const mcpDropdownRef = ref<HTMLElement | null>(null)
const currentSessionId = ref<string>('')  // 当前会话ID
const chatConversationRef = ref<HTMLElement | null>(null)  // 聊天容器引用
const isGenerating = ref(false)  // 是否正在生成回复
const rerank = ref(false)
const userId = ref<string>('testUserId')
// 真实数据
const sessions = ref<session[]>([])
const sessionsTotal = ref<number>(0)
const loading = ref(false)
// 切换 rerank 开关
const toggleRerank = () => {
  rerank.value = !rerank.value
}

// 四种rag 搜素策略
const strategys = ref<any[]>([
  { name: 'vector', image: '/src/assets/plugin.svg' },
  { name: 'hybrid', image: '/src/assets/plugin.svg' },
  { name: 'mmr', image: '/src/assets/plugin.svg' },
  { name: 'multi_query', image: '/src/assets/plugin.svg' }
])

// 定义来源元数据接口
interface SourceMetadata {
  file_name?: string        // 文件名，如：劳动法.pdf
  chunk_index?: number      // 块索引
  distance?: number         // 向量距离
  rerank_score?: number     // 重排序分数
  file_hash?: string        // 文件哈希
  split_strategy?: string   // 分块策略
  file_type?: string        // 文件类型
  total_chunks?: number     // 总块数
  chunk_size?: number       // 块大小
  source?: string           // 来源类型
  category?: string         // 分类
  author?: string           // 作者
}

// 定义引用来源接口
interface Source {
  content?: string          // 文档内容摘要
  metadata?: SourceMetadata // 元数据
}

// 定义消息元数据接口（对应 ChatResponse）
interface MessageMetadata {
  message_id?: string       // 消息 ID（对应后端 message_id）
  session_id?: string       // 会话 ID（对应后端 session_id）
  role?: 'user' | 'assistant'  // 消息角色
  content?: string          // 回复内容或者提问内容
  timestamp?: string        // 回复时间戳
  sources?: Source[]        // 引用来源（如果使用 RAG）
  rag_used?: boolean        // 是否使用了 RAG
  retrieval_strategy?: string  // 使用的检索策略
  tools_used?: any          // 使用的工具列表
  tool_results?: any        // 工具执行结果
}

// 本页对话消息（用户在上，AI 在下）
const messages = ref<Array<MessageMetadata>>([])

// 打开创建对话框
const openCreateSession = async () => {
  // 重置所有相关状态到初始值
  selectedMode.value = ''           // 默认使用 RAG 模式
  selectedStrategy.value = ''    // 默认使用 vector 检索策略

  selectedMcpServers.value = []        // 清空 MCP 服务器选择
  inputMessage.value = ''              // 清空输入框
  // 关闭下拉选择器
  showToolSelector.value = false
  showMcpSelector.value = false
  selectedSession.value = ''
  messages.value = []
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
        rag_enabled: item.rag_enabled,
        session_title: item.title
      }))

      sessionsTotal.value = response.data.total

      console.log('对话列表获取成功:', sessions.value)

      // // 如果会话列表不为空且当前路由是默认页面，立即自动打开第一个会话
      // if (sessions.value.length > 0 && router.currentRoute.value.name === 'defaultPage') {
      //   const firstSession = sessions.value[0]
      //   console.log('立即自动打开第一个会话:', firstSession.sessionId, firstSession.name)

      //   // 设置选中的会话
      //   selectedSession.value = firstSession.sessionId

      //   // 设置聊天store的状态
      //   historyChatStore.sessionId = firstSession.sessionId
      //   historyChatStore.name = firstSession.name
      //   historyChatStore.logo = firstSession.logo

      //   // 立即跳转到聊天页面
      //   router.push({
      //     path: '/conversation/chatPage',
      //     query: {
      //       session_id: firstSession.sessionId
      //     }
      //   })
      // }
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

// 选择会话
const selectSession = async (session_id: string) => {
  try {
    const response = await getSessionAPI(session_id)
    if (response.data.code === 200) {
      console.log('查询某个会话得到的消息', response.data.data)
      
      // 替换当前 messages 内容为查询到的会话历史
      if (response.data.data && response.data.data.messages && Array.isArray(response.data.data.messages)) {
        // 直接使用后端返回的 messages 数组，保持完整的数据结构（包括 sources）
        messages.value = response.data.data.messages.map((msg: any) => ({
          message_id: msg.message_id,
          session_id: msg.session_id,
          role: msg.role as 'user' | 'assistant',
          content: msg.content || '',
          timestamp: msg.timestamp,
          sources: msg.sources || [],
          rag_used: msg.rag_used,
          retrieval_strategy: msg.retrieval_strategy,
          tools_used: msg.tools_used,
          tool_results: msg.tool_results
        }))
        
        console.log('已加载会话历史，消息数量:', messages.value.length)
        console.log('消息详情:', messages.value)
        
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

// 切换 rag 选择
const selectStrategy = (strategy: string) => {
  // 如果已经选择了当前策略，再次点击则取消选择
  if (selectedStrategy.value === strategy && selectedMode.value === 'rag') {
    selectedStrategy.value = ''
    selectedMode.value = ''
  } else {
    // 选择新的 RAG 策略
    selectedStrategy.value = strategy
    selectedMode.value = 'rag'
  }
}

// 切换智能搜索
const toggleWebSearch = () => {
  // 如果当前已经是 normal 模式，再次点击则取消选择
  if (selectedMode.value === 'normal') {
    selectedMode.value = ''
    selectedStrategy.value = ''
  } else {
    // 切换到 normal 模式
    selectedMode.value = 'normal'
    selectedStrategy.value = ''  // 清空 RAG 策略选择
  }
  console.log(selectedMode.value)
}

//切换Rag搜索
const toggleRagSearch = () => {
  // 如果当前已经是 rag 模式，再次点击则取消选择
  if (selectedMode.value === 'rag') {
    selectedMode.value = ''
    selectedStrategy.value = ''
  } else {
    // 切换到 rag 模式
    selectedMode.value = 'rag'
    // 如果没有选择策略，默认选择第一个
    if (!selectedStrategy.value && strategys.value.length > 0) {
      selectedStrategy.value = strategys.value[0].name
    }
  }
  console.log(selectedMode.value)
}

// 发送消息
const handleSend = async () => {
  if (!inputMessage.value.trim()) {
    ElMessage.warning('请输入消息内容')
    return
  }

  // 如果正在生成回复，不允许发送新消息
  if (isGenerating.value) {
    ElMessage.warning('请等待当前回复完成')
    return
  }

  const question = inputMessage.value.trim()

  console.log('=== RAG 模式发送消息 ===')
  console.log('selectedStrategy:', selectedStrategy.value)
  console.log('query:', question)
  console.log('session_id:', currentSessionId.value)


  // 如果还没有 session_id，生成一个新的

  // 立即清空输入框，提升用户体验
  inputMessage.value = ''

  // 设置正在生成状态（转圈）
  isGenerating.value = true

  // 将用户消息加入消息列表
  console.log('将用户消息加入 messages')
  messages.value.push({ role: 'user' as const, content: question })

  // 自动滚动到底部
  scrollToBottom()

  // 预置一条 AI 消息用于流式累加（先添加到数组，然后通过索引更新以触发响应式）
  const aiMsgIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })
  console.log('当前 messages 长度:', messages.value.length)

  try {
    // 根据新的接口规范构建 payload
    const payload: ChatRequest = {
      message: question,
      user_id: "user-456",
      use_rag: selectedMode.value === 'rag' ? true : false,  // 当选中 RAG 模式时启用 RAG 检索
      retrieval_strategy: selectedStrategy.value,
      enable_rerank: rerank.value === true ? true : false,
      max_history: 20,
      stream: true,
      enable_tools: selectedMode.value === 'normal' ? true : false
    }

    // 如果 currentSessionId 不为空，才添加 session_id 字段
    if (currentSessionId.value) {
      payload.session_id = currentSessionId.value;
    }

    console.log('准备调用 workspaceSimpleChatStreamAPI，payload:', payload)

    // 用于存储完整的消息对象
    let fullMessageData: MessageMetadata | null = null
    let lastMessageId: string = ''  // 记录最后一条消息 ID，用于去重

    await workspaceSimpleChatStreamAPI(
      payload,
      (messageData: MessageMetadata) => {
        console.log('📨 收到消息数据:', messageData)

        // 🎯 阶段 1：接收 metadata 元数据
        if (messageData.message_id || messageData.session_id) {
          console.log('📋 设置 metadata:', messageData)

          // 更新 lastMessageId
          if (messageData.message_id) {
            lastMessageId = messageData.message_id
            messages.value[aiMsgIndex].message_id = messageData.message_id
          }

          // 更新 session_id
          if (messageData.session_id) {
            currentSessionId.value = messageData.session_id
            messages.value[aiMsgIndex].session_id = messageData.session_id
            console.log('🔄 更新 session_id:', messageData.session_id)
          }

          // 更新 role
          if (messageData.role) {
            messages.value[aiMsgIndex].role = messageData.role
          }

          return
        }

        // 🎯 阶段 2：接收流式 chunk 数据（只有 content 字段）
        if (messageData.content && !messageData.message_id && !messageData.sources) {
          console.log('📝 累加 chunk:', messageData.content)
          messages.value[aiMsgIndex].content += messageData.content

          // 每次收到新内容时自动滚动到底部
          scrollToBottom()
          return
        }

        // 🎯 阶段 3：接收完整的 sources
        if (messageData.sources && messageData.sources.length > 0) {
          console.log('📚 设置 sources:', messageData.sources)
          messages.value[aiMsgIndex].sources = messageData.sources

          // 更新其他元数据
          if (messageData.rag_used !== undefined) {
            messages.value[aiMsgIndex].rag_used = messageData.rag_used
          }
          if (messageData.retrieval_strategy) {
            messages.value[aiMsgIndex].retrieval_strategy = messageData.retrieval_strategy
          }
          if (messageData.tools_used !== undefined) {
            messages.value[aiMsgIndex].tools_used = messageData.tools_used
          }
          if (messageData.tool_results !== undefined) {
            messages.value[aiMsgIndex].tool_results = messageData.tool_results
          }
          if (messageData.timestamp) {
            messages.value[aiMsgIndex].timestamp = messageData.timestamp
          }

          // 保存完整的消息数据
          fullMessageData = messageData

          // 滚动到底部
          scrollToBottom()
          return
        }
      },
      (err) => {
        console.error('❌ 出错', err)
        ElMessage.error('对话失败，请稍后重试')
        isGenerating.value = false  // 出错时解除生成状态
      },
      () => {
        console.log('✅ SSE 连接结束')
        console.log('📦 完整消息数据:', fullMessageData)
        isGenerating.value = false  // 完成时解除生成状态
      }
    )
  } catch (e) {
    console.error('RAG 模式对话异常', e)
    ElMessage.error('对话异常')
    isGenerating.value = false  // 异常时解除生成状态
  }

}

// 加载会话历史
const loadSessionHistory = async (sessionId: string) => {
  try {
    // 导入 API
    const { getWorkspaceSessionsAPI } = await import('../../apis/workspace')
    const response = await getWorkspaceSessionsAPI()

    if (response.data.status_code === 200) {
      const session = response.data.data.find((s: any) => s.session_id === sessionId)

      if (session && session.contexts && Array.isArray(session.contexts)) {
        // 将 contexts 转换为 messages 格式
        messages.value = session.contexts.map((ctx: any) => [
          { role: 'user' as const, content: ctx.query || '' },
          { role: 'assistant' as const, content: ctx.answer || '' }
        ]).flat().filter((msg: any) => msg.content) // 过滤掉空内容

        console.log('已加载会话历史，消息数量:', messages.value.length)

        // 加载历史后滚动到底部
        scrollToBottom()
      }
    }
  } catch (error) {
    console.error('加载会话历史失败:', error)
    ElMessage.error('加载会话历史失败')
  }
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

// 点击空白处关闭rag/MCP下拉
const handleClickOutside = (e: MouseEvent) => {
  const target = e.target as Node
  if (showToolSelector.value && toolDropdownRef.value && !toolDropdownRef.value.contains(target)) {
    showToolSelector.value = false
  }
  if (showMcpSelector.value && mcpDropdownRef.value && !mcpDropdownRef.value.contains(target)) {
    showMcpSelector.value = false
  }
}

// 生成UUID（模拟Python的uuid4().hex）
const generateSessionId = (): string => {
  // 使用crypto.randomUUID()生成UUID，然后移除横杠
  return crypto.randomUUID().replace(/-/g, '')
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
    await loadSessionHistory(sessionId)
  }

  // 懒加载 MCP 列表（用于选择）
  // import('../../apis/mcp-server').then(async ({ getMCPServersAPI }) => {
  //   try {
  //     const res = await getMCPServersAPI()
  //     if (res.data && res.data.status_code === 200 && Array.isArray(res.data.data)) {
  //       mcpServers.value = res.data.data
  //     }
  //   } catch (e) {
  //     console.error('加载 MCP 服务器失败', e)
  //   }
  // })
  // document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
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
      await loadSessionHistory(newSessionId as string)
    } 
    // else if (!newSessionId && oldSessionId) {
    //   // 如果从有session_id变为没有，生成新的session_id
    //   currentSessionId.value = generateSessionId()
    //   console.log('生成新会话ID:', currentSessionId.value)
    //   messages.value = []
    // }
  }
)

</script>

<template>
  <div class="homepage">

    <!-- 左侧边栏 -->
    <div class="sidebar">
      <!-- 新建会话按钮 -->
      <div class="create-section">
        <button @click="openCreateSession" class="create-btn-native">
          <div class="btn-content">
            <span class="icon">+</span>
            <span>新建会话</span>
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
          :class="{ active: selectedSession === session.session_id }" @select="selectSession(session.session_id)"
          @delete="deleteSession(session.session_id)" />
      </div>
    </div>

    <!-- 右侧主体区域 -->
    <div class="content">
      <div class="chat-page" :class="{ 'chat-active': messages.length > 0 }">
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
                    <span class="loading-text">AI 正在思考中...</span>
                  </div>
                  <!-- 实际内容 - 有内容时显示 -->
                  <MdPreview v-if="msg.content" :editorId="'workspace-ai-' + idx" :modelValue="msg.content" />

                  <!-- 引用来源展示 - 当 sources 不为空时显示 -->
                  <div v-if="msg.sources && msg.sources.length > 0" class="sources-section">
                    <div class="sources-title">引用来源</div>
                    <div v-for="(source, sIdx) in msg.sources" :key="sIdx" class="source-item">
                      <div class="source-content">
                        <span class="source-text">{{ source.content }}</span>
                      </div>
                      <div class="source-metadata">
                        <span v-if="source.metadata?.file_name" class="meta-item">
                          <span class="meta-label">文件：</span>
                          <span class="meta-value">{{ source.metadata.file_name }}</span>
                        </span>
                        <span v-if="source.metadata?.category" class="meta-item">
                          <span class="meta-label">分类：</span>
                          <span class="meta-value">{{ source.metadata.category }}</span>
                        </span>
                        <span v-if="source.metadata?.author" class="meta-item">
                          <span class="meta-label">作者：</span>
                          <span class="meta-value">{{ source.metadata.author }}</span>
                        </span>
                        <span v-if="source.metadata?.source" class="meta-item">
                          <span class="meta-label">来源：</span>
                          <span class="meta-value">{{ source.metadata.source }}</span>
                        </span>
                        <span v-if="source.metadata?.rerank_score !== undefined" class="meta-item">
                          <span class="meta-label">重排序分数：</span>
                          <span class="meta-value">{{ source.metadata.rerank_score }}</span>
                        </span>
                      </div>
                    </div>
                  </div>
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
            <h1 class="welcome-title">我是律动AI助手，很高兴见到你！</h1>
            <p class="welcome-subtitle">
              吾心吾行澄如明镜,所作所为皆为正义！
            </p>
          </div>

          <!-- 输入区域（始终在底部） -->
          <div class="input-section">
            <div class="input-wrapper">
              <textarea v-model="inputMessage" placeholder="给智言发消息，让智言帮你完成任务~" class="message-input" rows="4"
                @keydown="handleKeydown"></textarea>

              <!-- 底部控制栏 -->
              <div class="input-footer">
                <div class="footer-left">

                  <!-- 智能搜索（normal 模式时高亮） -->
                  <div class="selector-dropdown">
                    <div :class="['selector-item', { active: selectedMode === 'normal' }]" @click="toggleWebSearch">
                      <span class="selector-icon">🌐</span>
                      <span class="selector-text">智能搜索</span>
                    </div>
                  </div>

                  <!-- rag 搜素选择（rag 模式时高亮） -->
                  <div class="selector-dropdown" ref="toolDropdownRef">
                    <div :class="['selector-item', { active: selectedMode === 'rag' }]" @click="toggleRagSearch">
                      <img src="/src/assets/plugin.svg" alt="rag" class="selector-icon-img" />
                      <span class="selector-text">
                        {{ selectedStrategy ? `已选 ${selectedStrategy} ` : '选择 rag' }}
                      </span>
                      <span class="selector-arrow" @click="showToolSelector = !showToolSelector">▲</span>
                    </div>

                    <!-- rag 下拉菜单 -->
                    <transition name="dropdown">
                      <div v-if="showToolSelector" class="dropdown-menu tool-menu">
                        <!-- 标题 -->
                        <div class="dropdown-header">
                          <span class="header-title">选择 rag 方式</span>
                          <span class="header-count">{{ strategys.length }} 个可用</span>
                        </div>

                        <!-- rag 列表 -->
                        <div class="dropdown-list">
                          <div v-if="strategys.length === 0" class="dropdown-empty">
                            <img src="/src/assets/plugin.svg" alt="rag" class="empty-icon-img" />
                            <span class="empty-text">暂无可用 rag 方式</span>
                          </div>
                          <div v-for="strategy in strategys" :key="strategy.name"
                            :class="['dropdown-item', { selected: selectedStrategy === strategy.name }]"
                            @click="selectStrategy(strategy.name)">
                            <div class="item-left">
                              <div class="item-icon-wrapper">
                                <img :src="strategy.image" alt="rag" class="item-icon-img" />
                              </div>
                              <div class="item-content">
                                <div class="item-text">{{ strategy.name }}</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </transition>
                  </div>

                  <!-- rerank 开关（绑定 rerank） -->
                  <div>
                    <switch :aria-checked="rerank" :class="{ active: rerank }" @click="toggleRerank"></switch>
                  </div>

                </div>

                <div class="footer-right">
                  <!-- 附件按钮 -->
                  <!-- <button class="icon-btn" title="上传附件" @click="triggerFileInput">
                    <img src="../../assets/upload.svg" alt="上传" class="upload-icon" />
                  </button>
                  <input type="file" ref="fileInputRef" class="hidden-file-input" multiple @change="onFileChange" /> -->

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
          <p class="disclaimer-text">内容均为AI生成，想要获取专业且正规的回答，请咨询相关人士</p>
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
      padding: 20px 16px 16px;
      border-bottom: 1px solid #f0f0f0;

      .create-btn-native {
        width: 100%;
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
      background: linear-gradient(180deg, #fafbfc 0%, #ffffff 100%);
      overflow: hidden;
      flex: 1;

      &.chat-active {
        background-color: #f7f8fa;
      }
    }

    .chat-conversation-container {
      flex: 1;
      min-height: 0;
      /* 只在对话区域出现滚动条 */
      overflow-y: auto;
      overflow-x: hidden;
      background-color: #f7f8fa;
      /* 为左右两侧保留空隙，且使用 box-sizing 避免宽度溢出 */
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
      background-color: #f7f8fa;
      padding: 0;
      border-top: 1px solid #e9ecef;
      flex-shrink: 0;
      width: 100%;

      .disclaimer-text {
        font-size: 12px;
        color: #9ca3af;
        text-align: center;
        padding: 8px;
      }
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
        padding: 12px 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        position: relative;
        z-index: 1;
        
        // 响应式适配
        @media (max-width: 768px) {
          padding: 10px 12px;
          border-radius: 12px;
        }

        &:focus-within {
          border-color: #667eea;
          box-shadow: 0 6px 24px rgba(102, 126, 234, 0.15);
        }

        .message-input {
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