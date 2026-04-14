<template>
  <div class="dashboard-container">
    

    <div class="dashboard-content">
      <!-- 左侧配置表单 -->
      <div class="config-form-container" v-loading="configLoading">
      <div class="config-form-header">
        <h3>系统配置</h3>
        <span class="config-desc">配置模型参数和 RAG 检索参数</span>
      </div>

      <el-form :model="configForm" label-width="280px" class="config-form" size="default">
        <!-- API 配置 -->
        <el-divider content-position="left">API 配置</el-divider>
        
        <el-form-item label="OpenAI 基础 URL">
          <el-input 
            v-model="configForm.OPENAI_BASE_URL" 
            placeholder="请输入 OpenAI API 基础 URL"
            @input="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="OpenAI API 密钥">
          <el-input 
            v-model="configForm.OPENAI_API_KEY" 
            type="password"
            show-password
            placeholder="请输入 OpenAI API 密钥"
            @input="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="DashScope API 密钥">
          <el-input 
            v-model="configForm.DASHSCOPE_API_KEY" 
            type="password"
            show-password
            placeholder="请输入 DashScope API 密钥"
            @input="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="Hugging Face 令牌">
          <el-input 
            v-model="configForm.HF_TOKEN" 
            type="password"
            show-password
            placeholder="请输入 Hugging Face API 密钥"
            @input="handleConfigChange"
          />
        </el-form-item>

        <!-- 模型配置 -->
        <el-divider content-position="left">模型配置</el-divider>

        <el-form-item label="模型名称">
          <el-input 
            v-model="configForm.MODEL_NAME" 
            placeholder="请输入模型名称"
            @input="handleConfigChange"
          />
        </el-form-item>

        <!-- 知识图谱配置 -->
         <el-divider content-position="left">知识图谱配置</el-divider>

        <el-form-item label="知识图谱名称">
          <el-input 
            v-model="configForm.GRAPH_MODEL_NAME" 
            placeholder="请输入 GRAPH_MODEL_NAME"
            @input="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="是否启用严格模式">
          <el-switch 
            v-model="configForm.GRAPH_STRICT_MODE" 
            @change="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="知识图谱提取时单个文本块的最大字符数">
          <el-input-number 
            v-model="configForm.GRAPH_MAX_CHUNK_SIZE" 
            :min="0"
            :max="100000000"
            :step="1"
            controls-position="right"
            @change="handleConfigChange"
          />
        </el-form-item>


        <!-- RAG 配置 -->
        <el-divider content-position="left">RAG 检索配置</el-divider>

        <el-form-item label="检索返回文档数量">
          <el-input-number 
            v-model="configForm.RAG_TOP_K" 
            :min="1"
            :max="20"
            :step="1"
            controls-position="right"
            @change="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="检索初始获取文档数量">
          <el-input-number 
            v-model="configForm.RAG_FETCH_K" 
            :min="1"
            :max="50"
            :step="1"
            controls-position="right"
            @change="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="预检索返回文档数量">
          <el-input-number 
            v-model="configForm.PRE_RETRIEVE_TOP_K" 
            :min="1"
            :max="20"
            :step="1"
            controls-position="right"
            @change="handleConfigChange"
          />
        </el-form-item>

        <el-form-item label="对话上下文最大长度">
          <el-input-number 
            v-model="configForm.MAX_HISTORY_LENGTH" 
            :min="0"
            :max="50"
            :step="1"
            controls-position="right"
            @change="handleConfigChange"
          />
        </el-form-item>

        <!-- 保存按钮 -->
        <el-form-item>
          <el-button 
            type="primary" 
            :disabled="!hasChanges" 
            @click="handleSaveConfig"
            :loading="saving"
            class="save-btn"
          >
            保存配置
          </el-button>
          <el-button @click="handleReset" :disabled="!hasChanges">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    </div>

    <!-- 右侧对话测试面板 -->
    <div v-if="showTestPanel" class="test-panel">
      <div class="test-panel-header">
        <span class="panel-title">模型测试</span>
        <el-icon class="close-icon" @click="closeTestPanel"><Close /></el-icon>
      </div>
      
      <div class="test-panel-body">
        <div v-loading="testing" class="test-content">
          <div v-if="!testing && testResult" class="test-result">
            <div class="result-item success" v-if="testResult.success">
              <el-icon class="result-icon" color="#67C23A"><SuccessFilled /></el-icon>
              <span class="result-text">测试成功</span>
            </div>
            <div v-else class="result-item error">
              <el-icon class="result-icon" color="#F56C6C"><CircleCloseFilled /></el-icon>
              <span class="result-text">测试失败</span>
            </div>

          </div>

          <div v-else-if="testing" class="testing-tip">
            <el-icon class="loading-icon"><Loading /></el-icon>
            <span>正在测试模型配置，请稍候...</span>
          </div>

          <div v-else class="initial-tip">
            <el-icon class="tip-icon"><Promotion /></el-icon>
            <span>可以在下方发送消息测试模型</span>
          </div>
        </div>

        <!-- 对话区域 -->
        <div class="chat-area">
          <div class="chat-messages">
            <div 
              v-for="(msg, index) in chatMessages" 
              :key="index" 
              class="chat-message"
              :class="{ 'user': msg.role === 'user', 'assistant': msg.role === 'assistant', 'error': msg.isError }"
            >
              <div class="message-content">{{ msg.content }}</div>
            </div>
          </div>
          <div class="chat-input-area">
            <el-input
              v-model="chatInput"
              placeholder="请输入测试消息..."
              @keyup.enter="handleSendMessage"
              :disabled="chatLoading"
            />
            <el-button 
              type="primary" 
              @click="handleSendMessage" 
              :loading="chatLoading"
              :disabled="!chatInput.trim()"
            >
              发送
            </el-button>
          </div>
        </div>
      </div>

      <div class="test-panel-footer">
        <el-button @click="closeTestPanel" :disabled="testing || chatLoading">
          关闭
        </el-button>
        <el-button type="primary" @click="handleReTest" :loading="testing">
          {{ testing ? '测试中...' : '重新测试' }}
        </el-button>
      </div>
    </div>

    <!-- 模型测试对话框 (保留以备后用) -->
    <div v-if="showTestDialog" class="custom-dialog-overlay" @click.self="showTestDialog = false">
      <div class="custom-dialog">
        <div class="custom-dialog-header">
          <span class="dialog-title">模型测试</span>
          <el-icon class="close-icon" @click="showTestDialog = false"><Close /></el-icon>
        </div>
        
        <div class="custom-dialog-body">
          <div v-loading="testing" class="test-content">
            <div v-if="!testing && testResult" class="test-result">
              <div class="result-item success" v-if="testResult.success">
                <el-icon class="result-icon" color="#67C23A"><SuccessFilled /></el-icon>
                <span class="result-text">测试成功</span>
              </div>
              <div v-else class="result-item error">
                <el-icon class="result-icon" color="#F56C6C"><CircleCloseFilled /></el-icon>
                <span class="result-text">测试失败</span>
              </div>

              <el-divider />

              <div class="result-details">
                <div class="detail-row">
                  <span class="label">模型名称：</span>
                  <span class="value">{{ testResult.model || '未知' }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">测试问题：</span>
                  <span class="value">{{ testResult.original_message || '你好' }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">模型回复：</span>
                  <span class="value response">{{ testResult.response || '无回复' }}</span>
                </div>
              </div>
            </div>

            <div v-else-if="testing" class="testing-tip">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <span>正在测试模型配置，请稍候...</span>
            </div>

            <div v-else class="initial-tip">
              <el-icon class="tip-icon"><Promotion /></el-icon>
              <span>点击下方"开始测试"按钮测试模型配置</span>
            </div>
          </div>
        </div>

        <div class="custom-dialog-footer">
          <el-button @click="showTestDialog = false" :disabled="testing">
            {{ testing ? '测试中...' : '关闭' }}
          </el-button>
          <el-button type="primary" @click="handleTestModel" :loading="testing">
            {{ testing ? '测试中...' : (testResult ? '重新测试' : '开始测试') }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, computed, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, SuccessFilled, CircleCloseFilled, Loading, Close, Promotion } from '@element-plus/icons-vue'
// 按需引入 ECharts，避免打包体积和解析问题
import * as echarts from 'echarts/core'
import type { ECharts as EChartsInstance } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, DatasetComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([TitleComponent, TooltipComponent, LegendComponent, GridComponent, DatasetComponent, DataZoomComponent, LineChart, BarChart, CanvasRenderer])
import {
  getUsageStatsAPI,
  getUsageCountAPI,
  getUsageModelsAPI,
  getUsageAgentsAPI,
  type UsageStatsRequest,
  type UsageDataByDate,
  type UsageCountByDate
} from '../../apis/usage-stats'
import { getConfigAPI, updateConfigAPI, testModelAPI } from '../../apis/configuration'

// ========== 系统配置相关 ==========
// 配置表单数据
interface ConfigForm {
  OPENAI_BASE_URL: string
  OPENAI_API_KEY: string
  DASHSCOPE_API_KEY: string
  HF_TOKEN: string
  MODEL_NAME: string
  RAG_TOP_K: number
  RAG_FETCH_K: number
  PRE_RETRIEVE_TOP_K: number
  MAX_HISTORY_LENGTH: number
  GRAPH_MODEL_NAME: string
  GRAPH_STRICT_MODE: boolean
  GRAPH_MAX_CHUNK_SIZE: number
}

// 配置表单数据
const configForm = reactive<ConfigForm>({
  OPENAI_BASE_URL: '',
  OPENAI_API_KEY: '',
  DASHSCOPE_API_KEY: '',
  HF_TOKEN: '',
  MODEL_NAME: '',
  RAG_TOP_K: 0,
  RAG_FETCH_K: 0,
  PRE_RETRIEVE_TOP_K: 0,
  MAX_HISTORY_LENGTH: 0,
  GRAPH_MODEL_NAME: '',
  GRAPH_STRICT_MODE: false,
  GRAPH_MAX_CHUNK_SIZE: 0
})

// 保存原始配置用于对比
const originalConfig = reactive<ConfigForm>({
  OPENAI_BASE_URL: '',
  OPENAI_API_KEY: '',
  DASHSCOPE_API_KEY: '',
  HF_TOKEN: '',
  MODEL_NAME: '',
  RAG_TOP_K: 0,
  RAG_FETCH_K: 0,
  PRE_RETRIEVE_TOP_K: 0,
  MAX_HISTORY_LENGTH: 0,
  GRAPH_MODEL_NAME: '',
  GRAPH_STRICT_MODE: false,
  GRAPH_MAX_CHUNK_SIZE: 0
})

const configLoading = ref(false)
const saving = ref(false)

// 模型测试对话框控制
const showTestDialog = ref(false) // 是否显示测试对话框
const showTestPanel = ref(false) // 是否显示右侧测试面板
const testing = ref(false) // 是否正在测试
const testResult = ref<{
  success: boolean
  model?: string
  response?: string
  original_message?: string
  error?: string
} | null>(null)

// 对话测试相关
interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  isError?: boolean
}

const chatMessages = ref<ChatMessage[]>([])
const chatInput = ref('')
const chatLoading = ref(false)

// 发送消息测试
const handleSendMessage = async () => {
  const message = chatInput.value.trim()
  if (!message || chatLoading.value) return

  chatMessages.value.push({ role: 'user', content: message })
  chatInput.value = ''
  chatLoading.value = true

  try {
    const response = await testModelAPI({ message })
    
    if (response.data.code === 200) {
      chatMessages.value.push({ 
        role: 'assistant', 
        content: response.data.data.response || '无回复' 
      })
    } else {
      chatMessages.value.push({ 
        role: 'assistant', 
        content: response.data.message || '模型测试失败',
        isError: true 
      })
    }
  } catch (error: any) {
    console.error('模型测试失败:', error)
    const errorMsg = error?.response?.data?.message || error?.message || '模型测试失败'
    chatMessages.value.push({ 
      role: 'assistant', 
      content: errorMsg,
      isError: true 
    })
  } finally {
    chatLoading.value = false
  }
}

// 关闭测试面板
const closeTestPanel = () => {
  showTestPanel.value = false
  chatMessages.value = []
  chatInput.value = ''
  testResult.value = null
  testing.value = false
}

// 重新测试
const handleReTest = async () => {
  chatMessages.value = []
  chatInput.value = ''
  testResult.value = null
  testing.value = true
  testResult.value = null
  
  try {
    const response = await testModelAPI({ message: '你好' })
    
    if (response.data.code === 200) {
      testResult.value = {
        success: true,
        model: response.data.data.model || '未知',
        response: response.data.data.response || '无回复',
        original_message: response.data.data.original_message || '你好'
      }
    } else {
      testResult.value = {
        success: false,
        error: response.data.message || '模型测试失败，请检查配置是否正确'
      }
    }
  } catch (error: any) {
    console.error('模型测试失败:', error)
    const errorMsg = error?.response?.data?.message || error?.message || '模型测试失败，请检查网络和配置'
    testResult.value = {
      success: false,
      error: errorMsg
    }
  } finally {
    testing.value = false
  }
}

// 检测是否有更改
const hasChanges = computed(() => {
  return (
    configForm.OPENAI_BASE_URL !== originalConfig.OPENAI_BASE_URL ||
    configForm.OPENAI_API_KEY !== originalConfig.OPENAI_API_KEY ||
    configForm.DASHSCOPE_API_KEY !== originalConfig.DASHSCOPE_API_KEY ||
    configForm.HF_TOKEN !== originalConfig.HF_TOKEN ||
    configForm.MODEL_NAME !== originalConfig.MODEL_NAME ||
    configForm.RAG_TOP_K !== originalConfig.RAG_TOP_K ||
    configForm.RAG_FETCH_K !== originalConfig.RAG_FETCH_K ||
    configForm.PRE_RETRIEVE_TOP_K !== originalConfig.PRE_RETRIEVE_TOP_K ||
    configForm.MAX_HISTORY_LENGTH !== originalConfig.MAX_HISTORY_LENGTH ||
    configForm.GRAPH_MODEL_NAME !== originalConfig.GRAPH_MODEL_NAME ||
    configForm.GRAPH_STRICT_MODE !== originalConfig.GRAPH_STRICT_MODE ||
    configForm.GRAPH_MAX_CHUNK_SIZE !== originalConfig.GRAPH_MAX_CHUNK_SIZE
  )
})

// 获取系统配置
const fetchConfig = async () => {
  configLoading.value = true
  try {
    const response = await getConfigAPI()
    if (response.data.code === 200 && response.data.data?.config) {
      const config = response.data.data.config
      
      // 填充表单数据
      configForm.OPENAI_BASE_URL = config.OPENAI_BASE_URL?.trim() || ''
      configForm.OPENAI_API_KEY = config.OPENAI_API_KEY?.trim() || ''
      configForm.DASHSCOPE_API_KEY = config.DASHSCOPE_API_KEY?.trim() || ''
      configForm.HF_TOKEN = config.HF_TOKEN?.trim() || ''
      configForm.MODEL_NAME = config.MODEL_NAME?.trim() || ''
      configForm.RAG_TOP_K = parseInt(config.RAG_TOP_K) 
      configForm.RAG_FETCH_K = parseInt(config.RAG_FETCH_K) 
      configForm.PRE_RETRIEVE_TOP_K = parseInt(config.PRE_RETRIEVE_TOP_K) 
      configForm.MAX_HISTORY_LENGTH = parseInt(config.MAX_HISTORY_LENGTH) 
      configForm.GRAPH_MODEL_NAME = config.GRAPH_MODEL_NAME?.trim() || ''
      configForm.GRAPH_STRICT_MODE = config.GRAPH_STRICT_MODE === 'true'
      configForm.GRAPH_MAX_CHUNK_SIZE = parseInt(config.GRAPH_MAX_CHUNK_SIZE) 

      // 保存原始配置用于对比
      Object.assign(originalConfig, configForm)
      
      ElMessage.success('配置加载成功')
    } else {
      ElMessage.warning('未找到配置数据')
    }
  } catch (error: any) {
    console.error('加载配置失败:', error)
    ElMessage.error(error?.response?.data?.message || '加载配置失败')
  } finally {
    configLoading.value = false
  }
}

// 配置更改处理
const handleConfigChange = () => {
  // 这个函数会在每次表单值变化时自动触发 hasChanges 计算
  console.log('配置已更改')
}

// 保存配置
const handleSaveConfig = async () => {
  if (!hasChanges.value) {
    ElMessage.warning('请先修改配置')
    return
  }

  chatMessages.value = []
  chatInput.value = ''
  testResult.value = null
  testing.value = false
  testResult.value = null


  saving.value = true
  try {
    // 构建请求数据（只发送更改的字段）
    const updateData: any = {}
    
    if (configForm.OPENAI_BASE_URL !== originalConfig.OPENAI_BASE_URL) {
      updateData.OPENAI_BASE_URL = configForm.OPENAI_BASE_URL
    }
    if (configForm.OPENAI_API_KEY !== originalConfig.OPENAI_API_KEY) {
      updateData.OPENAI_API_KEY = configForm.OPENAI_API_KEY
    }
    if (configForm.DASHSCOPE_API_KEY !== originalConfig.DASHSCOPE_API_KEY) {
      updateData.DASHSCOPE_API_KEY = configForm.DASHSCOPE_API_KEY
    }
    if (configForm.HF_TOKEN !== originalConfig.HF_TOKEN) {
      updateData.HF_TOKEN = configForm.HF_TOKEN
    }
    if (configForm.MODEL_NAME !== originalConfig.MODEL_NAME) {
      updateData.MODEL_NAME = configForm.MODEL_NAME
    }
    if (configForm.RAG_TOP_K !== originalConfig.RAG_TOP_K) {
      updateData.RAG_TOP_K = String(configForm.RAG_TOP_K)
    }
    if (configForm.RAG_FETCH_K !== originalConfig.RAG_FETCH_K) {
      updateData.RAG_FETCH_K = String(configForm.RAG_FETCH_K)
    }
    if (configForm.PRE_RETRIEVE_TOP_K !== originalConfig.PRE_RETRIEVE_TOP_K) {
      updateData.PRE_RETRIEVE_TOP_K = String(configForm.PRE_RETRIEVE_TOP_K)
    }
    if (configForm.MAX_HISTORY_LENGTH !== originalConfig.MAX_HISTORY_LENGTH) {
      updateData.MAX_HISTORY_LENGTH = String(configForm.MAX_HISTORY_LENGTH)
    }
    if (configForm.GRAPH_MODEL_NAME !== originalConfig.GRAPH_MODEL_NAME) {
      updateData.GRAPH_MODEL_NAME = configForm.GRAPH_MODEL_NAME
    }
    if (configForm.GRAPH_STRICT_MODE !== originalConfig.GRAPH_STRICT_MODE) {
      updateData.GRAPH_STRICT_MODE = configForm.GRAPH_STRICT_MODE ? 'true' : 'false'
    }
    if (configForm.GRAPH_MAX_CHUNK_SIZE !== originalConfig.GRAPH_MAX_CHUNK_SIZE) {
      updateData.GRAPH_MAX_CHUNK_SIZE = String(configForm.GRAPH_MAX_CHUNK_SIZE)
    }

    // 调用更新接口
    const response = await updateConfigAPI(updateData)
    
    if (response.data.code === 200) {
      console.log("保存成功")
      ElMessage.success('配置保存成功')
      
      // 查询更新原始配置
      Object.assign(originalConfig, configForm)
      // fetchConfig()
      
      // 🎯 显示右侧测试面板
      showTestPanel.value = true
      testResult.value = null
      console.log("showTestPanel.value", showTestPanel.value)
    } else {
      ElMessage.error(response.data.message || '保存配置失败')
    }
  } catch (error: any) {
    console.error('保存配置失败:', error)
    ElMessage.error(error?.response?.data?.message || '保存配置失败')
  } finally {
    saving.value = false
  }
}

// 重置配置
const handleReset = () => {
  // 恢复原始配置
  Object.assign(configForm, originalConfig)
  ElMessage.info('已重置为原始配置')
}

// 测试模型配置
const handleTestModel = async () => {
  testing.value = true
  testResult.value = null
  
  try {
    const response = await testModelAPI({ message: '你好' })
    
    if (response.data.code === 200) {
      testResult.value = {
        success: true,
        model: response.data.data.model || '未知',
        response: response.data.data.response || '无回复',
        original_message: response.data.data.original_message || '你好'
      }
    } else {
      testResult.value = {
        success: false,
        error: response.data.message || '模型测试失败，请检查配置是否正确'
      }
    }
  } catch (error: any) {
    console.error('模型测试失败:', error)
    
    const errorMsg = error?.response?.data?.message || error?.message || '模型测试失败，请检查网络和配置'
    
    testResult.value = {
      success: false,
      error: errorMsg
    }
  } finally {
    testing.value = false
  }
}


// 初始化
onMounted(async () => {
  await nextTick()

  // 加载系统配置
  await fetchConfig()

})




</script>

<style scoped lang="scss">
.dashboard-container {
  background-color: #f5f7fa;
  display:flex;
}

 .dashboard-content{
    flex:1
  }

.dashboard-header {
  margin-bottom: 24px;
  .title-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 999px;
    background: #eef2ff;
    color: #4f46e5;
    border: 1px solid #c7d2fe;
  }

  .sub {
    margin-top: 6px;
    color: #7a8395;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: .2px;
    -webkit-font-smoothing: antialiased;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Source Han Sans CN', sans-serif;
  }

  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.filters-container {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  margin-bottom: 28px;
  flex-wrap: wrap;
  border: 1px solid #e4e8f1;
}

.filter-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-width: 220px;

  label {
    font-size: 12px;
    color: #4f5d75;
    white-space: nowrap;
    padding-left: 4px;
    font-weight: 600;
    letter-spacing: .3px;
    -webkit-font-smoothing: antialiased;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Source Han Sans CN', sans-serif;
  }
}

/* Select 美化 */
.filter-select :deep(.el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1px #dbe1ed inset;
  transition: all .2s ease;
  background: #fff;
  padding: 2px 14px;
}

.filter-select :deep(.el-input__inner::placeholder) {
  color: #a0a6b5;
}

.filter-select :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #9eb6ff inset;
}

.filter-select :deep(.is-focus .el-input__wrapper),
.filter-select :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #9aa8ff inset, 0 8px 18px rgba(99, 102, 241, .16);
}

.filter-select :deep(.el-select__caret) {
  color: #6975ff;
}

.filter-select :deep(.el-input__suffix-inner) {
  transition: transform .2s ease;
}

.filter-select :deep(.is-focus .el-input__suffix-inner) {
  transform: rotate(-180deg);
}

/* 下拉项美化 */
.dashboard-select-popper {
  border-radius: 12px !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, .08) !important;
  border: 1px solid #eef0f4 !important;
}

.dashboard-select-popper :deep(.el-select-dropdown__item) {
  padding: 8px 12px;
  border-radius: 8px;
  margin: 4px 8px;
}

.dashboard-select-popper :deep(.el-select-dropdown__item.hover) {
  background: #f5f7ff;
}

.dashboard-select-popper :deep(.el-select-dropdown__item.selected) {
  background: linear-gradient(180deg, #eef2ff, #f5f7ff);
  color: #4f46e5;
  font-weight: 600;
}

.filter-action {
  align-self: center;
  margin-left: auto;
  padding: 0 20px;
  border-radius: 12px;
  font-weight: 600;
  letter-spacing: .3px;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.2);
}

.filter-action :deep(.el-icon) {
  font-size: 16px;
}

.filter-action:hover:not(.is-disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.25);
}

.filter-action:active:not(.is-disabled) {
  transform: translateY(0);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.22);
}

.kpi-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.kpi-card {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
  position: relative;

  .kpi-title {
    font-size: 12px;
    color: #909399;
    margin-bottom: 6px;
  }

  .kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #303133;
    line-height: 1.2;
  }

  .kpi-desc {
    margin-top: 8px;
    font-size: 12px;
    color: #a0a3ad;
  }

  .kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .kpi-icon {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #eef2ff;
    color: #4f46e5;
    font-weight: 800;
    box-shadow: inset 0 0 0 1px #c7d2fe;
  }
}

.kpi-card--primary {
  background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%);
}

.kpi-card--warning {
  background: linear-gradient(180deg, #ffffff 0%, #fff9f3 100%);
}

.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
  gap: 24px;
}

.chart-wrapper {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.06);
  padding: 20px;
  min-height: 400px;
  position: relative;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.chart-content {
  width: 100%;
  height: 350px;
}

.empty {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a8abb2;
  font-size: 13px;
  pointer-events: none;
}

/* ========== 系统配置表单样式 ========== */
.config-form-container {
  background-color: #fff;
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  padding: 24px;
  
  border: 1px solid #e4e8f1;

  .config-form-header {
    margin-bottom: 24px;

    h3 {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 8px 0;
    }

    .config-desc {
      font-size: 13px;
      color: #909399;
    }
  }

  .config-form {
    max-width: 900px;

    :deep(.el-form-item) {
      margin-bottom: 24px;
    }

    :deep(.el-form-item__label) {
      font-weight: 500;
      color: #606266;
      font-size: 14px;
    }

    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px #dcdfe6 inset;
      transition: all 0.2s ease;
      padding: 0 14px;

      &:hover {
        box-shadow: 0 0 0 1px #c0c4cc inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #409eff inset;
      }
    }

    :deep(.el-input-number) {
      width: 100%;
      
      .el-input__wrapper {
        padding: 0 14px;
      }
    }

    :deep(.el-divider) {
      margin: 32px 0 24px;
      background-color: #e4e7ed;

      .el-divider__text {
        font-weight: 600;
        color: #606266;
        font-size: 15px;
      }
    }
  }

  .save-btn {
    padding: 12px 32px;
    font-weight: 600;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
    
    &:hover:not(.is-disabled) {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
    }

    &:active:not(.is-disabled) {
      transform: translateY(0);
    }

    &.is-disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

@media (max-width: 1400px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
}

// 右侧测试面板样式
.test-panel {
  width: 30%;
  height: auto;
  background: #fff;
  display: flex;
  flex-direction: column;
  position: sticky;
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  padding: 24px;
  
  border: 1px solid #e4e8f1;

  .test-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid #ebeef5;
    flex-shrink: 0;

    .panel-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }

    .close-icon {
      font-size: 18px;
      color: #909399;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        color: #606266;
      }
    }
  }

  .test-panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;

    .test-content {
      .test-result {
        .result-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 12px;

          &.success {
            background-color: #f0f9ff;
            border: 1px solid #e6ffed;
          }

          &.error {
            background-color: #fef0f0;
            border: 1px solid #ffe6e6;
          }

          .result-icon {
            font-size: 20px;
            flex-shrink: 0;
          }

          .result-text {
            font-size: 14px;
            font-weight: 600;
          }
        }

        .result-details {
          .detail-row {
            display: flex;
            margin-bottom: 8px;
            font-size: 13px;
            line-height: 1.5;

            .label {
              width: 80px;
              color: #909399;
              flex-shrink: 0;
            }

            .value {
              flex: 1;
              color: #303133;
              word-break: break-word;

              &.response {
                white-space: pre-wrap;
                max-height: 150px;
                overflow-y: auto;
              }
            }
          }
        }
      }

      .testing-tip {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 30px 0;
        color: #909399;

        .loading-icon {
          font-size: 28px;
          animation: rotating 2s linear infinite;
        }
      }

      .initial-tip {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 30px 0;
        color: #909399;

        .tip-icon {
          font-size: 28px;
          color: #409EFF;
        }
      }
    }

    .chat-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      border: 1px solid #e4e7ed;
      border-radius: 8px;
      overflow: hidden;
      min-height: 200px;

      .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 12px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        background-color: #fafafa;

        .chat-message {
          max-width: 85%;
          padding: 10px 14px;
          border-radius: 12px;
          font-size: 13px;
          line-height: 1.5;

          &.user {
            align-self: flex-end;
            background-color: #409EFF;
            color: #fff;
            border-bottom-right-radius: 4px;
          }

          &.assistant {
            align-self: flex-start;
            background-color: #fff;
            border: 1px solid #e4e7ed;
            border-bottom-left-radius: 4px;
            color: #303133;

            &.error {
              background-color: #fef0f0;
              border-color: #ffe6e6;
              color: #F56C6C;
            }
          }

          .message-content {
            white-space: pre-wrap;
            word-break: break-word;
          }
        }
      }

      .chat-input-area {
        display: flex;
        gap: 8px;
        padding: 10px;
        border-top: 1px solid #e4e7ed;
        background-color: #fff;

        .el-input {
          flex: 1;
        }
      }
    }
  }

  .test-panel-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 12px 20px;
    border-top: 1px solid #ebeef5;
    background-color: #f5f7fa;
    flex-shrink: 0;
  }
}

// 自定义对话框样式
.custom-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease;

  .custom-dialog {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
    width: 500px;
    max-width: 90vw;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    animation: slideIn 0.3s ease;

    .custom-dialog-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      border-bottom: 1px solid #ebeef5;

      .dialog-title {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
      }

      .close-icon {
        font-size: 20px;
        color: #909399;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          color: #606266;
          transform: rotate(90deg);
        }
      }
    }

    .custom-dialog-body {
      padding: 24px;
      overflow-y: auto;
      flex: 1;
      min-height: 200px;

      .test-content {
        .test-result {
          .result-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 16px;

            &.success {
              background-color: #f0f9ff;
              border: 1px solid #e6ffed;
            }

            &.error {
              background-color: #fef0f0;
              border: 1px solid #ffe6e6;
            }

            .result-icon {
              font-size: 24px;
              flex-shrink: 0;
            }

            .result-text {
              font-size: 16px;
              font-weight: 600;
            }
          }

          .result-details {
            margin-top: 20px;

            .detail-row {
              display: flex;
              margin-bottom: 16px;
              line-height: 1.6;

              &:last-child {
                margin-bottom: 0;
              }

              .label {
                width: 100px;
                color: #909399;
                flex-shrink: 0;
                font-weight: 500;
              }

              .value {
                flex: 1;
                color: #303133;

                &.response {
                  white-space: pre-wrap;
                  word-break: break-word;
                }
              }
            }
          }
        }

        .testing-tip {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          padding: 40px 0;
          color: #909399;

          .loading-icon {
            font-size: 32px;
            animation: rotating 2s linear infinite;
          }
        }

        .initial-tip {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          padding: 40px 0;
          color: #909399;

          .tip-icon {
            font-size: 32px;
            color: #409EFF;
          }
        }
      }
    }

    .custom-dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 16px 24px;
      border-top: 1px solid #ebeef5;
      background-color: #f5f7fa;
      border-radius: 0 0 12px 12px;
    }
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>