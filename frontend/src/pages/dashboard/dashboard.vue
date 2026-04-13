<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <div class="title-wrap">
        <h2>系统配置</h2>
      </div>
      <p class="sub">选择合适的模型并对模型进行测试</p>
    </div>

    <!-- <div class="filters-container">
      <div class="filter-group">
        <label>模型</label>
        <el-select v-model="filters.model" placeholder="全部模型" clearable filterable size="default"
          popper-class="dashboard-select-popper" class="filter-select" @change="handleFilterChange"
          style="width: 250px">
          <el-option label="全部" value="" />
          <el-option v-for="model in modelsList" :key="model" :label="model" :value="model" />
        </el-select>
      </div>

      <div class="filter-group">
        <label>智能体</label>
        <el-select v-model="filters.agent" placeholder="全部智能体" clearable filterable size="default"
          popper-class="dashboard-select-popper" class="filter-select" @change="handleFilterChange"
          style="width: 250px">
          <el-option label="全部" value="" />
          <el-option v-for="agent in agentsList" :key="agent" :label="agent" :value="agent" />
        </el-select>
      </div>

      <div class="filter-group">
        <label>时间范围</label>
        <el-select v-model="filters.delta_days" size="default" popper-class="dashboard-select-popper"
          class="filter-select" @change="handleFilterChange" style="width: 220px">
          <el-option label="周内" :value="7" />
          <el-option label="月内" :value="30" />
          <el-option label="年内" :value="365" />
          <el-option label="全部" :value="10000" />
        </el-select>
      </div>

      <el-button type="primary" class="filter-action" :icon="RefreshRight" @click="handleRefresh" :loading="loading">
        刷新数据
      </el-button>
    </div> -->

    <!-- 系统配置表单 -->
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

    <!-- 模型测试对话框 (自定义 div 实现) -->
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

// 筛选条件
// const filters = ref<UsageStatsRequest>({
//   model: '',
//   agent: '',
//   delta_days: 10000
// })

// // 数据列表
// const modelsList = ref<string[]>([])
// const agentsList = ref<string[]>([])

// // 加载状态
// const loading = ref(false)

// // 图表引用
// const callCountChartRef = ref<HTMLElement | null>(null)
// const tokenUsageChartRef = ref<HTMLElement | null>(null)

// // 图表实例
// let callCountChart: EChartsInstance | null = null
// let tokenUsageChart: EChartsInstance | null = null

// // KPI 与空数据状态
// const totalCalls = ref(0)
// const totalTokens = ref(0)
// const hasCallCountData = ref(true)
// const hasTokenUsageData = ref(true)
// const periodText = computed(() => {
//   const d = Number(filters.value.delta_days || 10000)
//   if (d === 7) return '近 7 天'
//   if (d === 30) return '近 30 天'
//   if (d === 365) return '近一年'
//   return '全部时间'
// })

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
const showTestDialog = ref(false)
const testing = ref(false)
const testResult = ref<{
  success: boolean
  model?: string
  response?: string
  original_message?: string
  error?: string
} | null>(null)

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
      
      // 🎯 显示测试对话框
      showTestDialog.value = true
      testResult.value = null
      console.log("showTestDialog.value",showTestDialog.value)
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

  // // 获取筛选列表
  // await Promise.all([
  //   fetchModelsList(),
  //   fetchAgentsList()
  // ])

  // // 初始化图表
  // initCallCountChart()
  // initTokenUsageChart()

  // // 加载数据
  // await fetchUsageData()

  // // 监听窗口大小变化
  // window.addEventListener('resize', handleResize)
})

// 清理
onBeforeUnmount(() => {
  // window.removeEventListener('resize', handleResize)

  // if (callCountChart) {
  //   callCountChart.dispose()
  //   callCountChart = null
  // }

  // if (tokenUsageChart) {
  //   tokenUsageChart.dispose()
  //   tokenUsageChart = null
  // }
})

// // 获取模型列表
// const fetchModelsList = async () => {
//   try {
//     const res = await getUsageModelsAPI()
//     if (res.data.status_code === 200) {
//       modelsList.value = res.data.data || []
//     }
//   } catch (error) {
//     console.error('获取模型列表失败:', error)
//   }
// }

// // 获取智能体列表
// const fetchAgentsList = async () => {
//   try {
//     const res = await getUsageAgentsAPI()
//     if (res.data.status_code === 200) {
//       agentsList.value = res.data.data || []
//     }
//   } catch (error) {
//     console.error('获取智能体列表失败:', error)
//   }
// }

// // 初始化调用次数折线图
// const initCallCountChart = () => {
//   if (!callCountChartRef.value) return

//   if (callCountChart) {
//     callCountChart.dispose()
//   }

//   callCountChart = echarts.init(callCountChartRef.value)

//   const option = {
//     color: ['#5B8FF9', '#61DDAA', '#65789B', '#F6BD16', '#7262fd', '#78D3F8'],
//     tooltip: {
//       trigger: 'axis',
//       axisPointer: {
//         type: 'cross'
//       }
//     },
//     legend: {
//       data: [],
//       top: 10,
//       textStyle: { color: '#606266' }
//     },
//     grid: {
//       left: '3%',
//       right: '3%',
//       bottom: 40,
//       top: 50,
//       containLabel: true
//     },
//     xAxis: {
//       type: 'category',
//       boundaryGap: false,
//       data: [],
//       axisLine: { lineStyle: { color: '#dcdfe6' } },
//       axisLabel: { color: '#606266' }
//     },
//     yAxis: {
//       type: 'value',
//       name: '调用次数',
//       nameTextStyle: { color: '#606266' },
//       splitLine: { lineStyle: { color: '#eee' } },
//       axisLabel: { color: '#606266' }
//     },
//     dataZoom: [{ type: 'inside' }],
//     series: []
//   }

//   callCountChart.setOption(option)
// }

// // 初始化 Token 使用量柱状图
// const initTokenUsageChart = () => {
//   if (!tokenUsageChartRef.value) return

//   if (tokenUsageChart) {
//     tokenUsageChart.dispose()
//   }

//   tokenUsageChart = echarts.init(tokenUsageChartRef.value)

//   const option = {
//     color: ['#5AD8A6', '#5B8FF9'],
//     tooltip: {
//       trigger: 'axis',
//       axisPointer: {
//         type: 'shadow'
//       },
//       formatter: (params: any) => {
//         const list = Array.isArray(params) ? params : []
//         const input = list.find((p: any) => p?.seriesName === '输入 Token')?.value || 0
//         const output = list.find((p: any) => p?.seriesName === '输出 Token')?.value || 0
//         const total = Number(input || 0) + Number(output || 0)
//         const date = list[0]?.axisValueLabel || ''
//         return `${date}<br/>输入 Token：${input}<br/>输出 Token：${output}<br/><b>总 Token：${total}</b>`
//       }
//     },
//     legend: {
//       data: ['输入 Token', '输出 Token'],
//       top: 10,
//       textStyle: { color: '#606266' }
//     },
//     grid: {
//       left: '3%',
//       right: '3%',
//       bottom: 40,
//       top: 50,
//       containLabel: true
//     },
//     xAxis: {
//       type: 'category',
//       data: [],
//       axisLine: { lineStyle: { color: '#dcdfe6' } },
//       axisLabel: { color: '#606266' }
//     },
//     yAxis: {
//       type: 'value',
//       name: 'Token 数量',
//       nameTextStyle: { color: '#606266' },
//       splitLine: { lineStyle: { color: '#eee' } },
//       axisLabel: { color: '#606266' }
//     },
//     series: [
//       {
//         name: '输入 Token',
//         type: 'bar',
//         stack: 'tokens',
//         data: [],
//         barMaxWidth: 20,
//         itemStyle: {}
//       },
//       {
//         name: '输出 Token',
//         type: 'bar',
//         stack: 'tokens',
//         data: [],
//         barMaxWidth: 20,
//         itemStyle: {},
//         label: {
//           show: true,
//           position: 'top',
//           color: '#606266',
//           fontWeight: 600,
//           formatter: (p: any) => {
//             const idx = p.dataIndex
//             // 输出柱顶端显示 总 Token = 输入 + 输出
//             const inputVal = (tokenUsageChart?.getOption()?.series?.[0] as any)?.data?.[idx] || 0
//             const outputVal = (tokenUsageChart?.getOption()?.series?.[1] as any)?.data?.[idx] || 0
//             return `${Number(inputVal || 0) + Number(outputVal || 0)}`
//           }
//         }
//       }
//     ]
//   }

//   tokenUsageChart.setOption(option)
// }

// // 更新调用次数折线图
// const updateCallCountChart = (data: UsageCountByDate) => {
//   if (!callCountChart) return

//   const dates = Object.keys(data).sort()
//   const seriesMap = new Map<string, number[]>()

//   // 根据筛选条件确定数据来源（agent 或 model）
//   const dataKey = filters.value.agent ? 'agent' : 'model'

//   // 收集所有系列数据
//   dates.forEach(date => {
//     const dayData = data[date][dataKey]
//     Object.entries(dayData).forEach(([name, count]) => {
//       if (!seriesMap.has(name)) {
//         seriesMap.set(name, new Array(dates.length).fill(0))
//       }
//       const index = dates.indexOf(date)
//       seriesMap.get(name)![index] = count
//     })
//   })

//   // 构建图表配置
//   const series = Array.from(seriesMap.entries()).map(([name, data]) => ({
//     name,
//     type: 'line',
//     data,
//     smooth: true,
//     symbol: 'circle',
//     symbolSize: 6,
//     lineStyle: { width: 2 },
//     areaStyle: {
//       opacity: 0.08
//     }
//   }))

//   callCountChart.setOption({
//     xAxis: {
//       data: dates
//     },
//     legend: {
//       data: Array.from(seriesMap.keys())
//     },
//     series
//   })

//   hasCallCountData.value = dates.length > 0 && series.length > 0 && series.some(s => (s.data as number[]).some(v => v > 0))
// }

// // 更新 Token 使用量柱状图
// const updateTokenUsageChart = (data: UsageDataByDate) => {
//   if (!tokenUsageChart) return

//   const dates = Object.keys(data).sort()

//   // 根据筛选条件确定数据来源（agent 或 model）
//   const dataKey = filters.value.agent ? 'agent' : 'model'

//   const inputTokens: number[] = []
//   const outputTokens: number[] = []
//   const totalTokens: number[] = []

//   // 聚合每天的 Token 数据
//   dates.forEach(date => {
//     const dayData = data[date][dataKey]
//     let dayInputTotal = 0
//     let dayOutputTotal = 0
//     let dayTotal = 0

//     Object.values(dayData).forEach((tokenData: any) => {
//       dayInputTotal += tokenData.input_tokens || 0
//       dayOutputTotal += tokenData.output_tokens || 0
//       dayTotal += tokenData.total_tokens || 0
//     })

//     inputTokens.push(dayInputTotal)
//     outputTokens.push(dayOutputTotal)
//     totalTokens.push(dayTotal)
//   })

//   tokenUsageChart.setOption({
//     xAxis: {
//       data: dates
//     },
//     series: [
//       {
//         name: '输入 Token',
//         data: inputTokens
//       },
//       {
//         name: '输出 Token',
//         data: outputTokens
//       }
//     ]
//   })

//   hasTokenUsageData.value = dates.length > 0 && (inputTokens.some(v => v > 0) || outputTokens.some(v => v > 0))
// }

// // 获取使用统计数据
// const fetchUsageData = async () => {
//   loading.value = true

//   try {
//     const params: UsageStatsRequest = {
//       agent: filters.value.agent || undefined,
//       model: filters.value.model || undefined,
//       delta_days: filters.value.delta_days
//     }

//     // 获取调用次数数据
//     const countRes = await getUsageCountAPI(params)
//     if (countRes.data.status_code === 200) {
//       updateCallCountChart(countRes.data.data)
//       // 累计调用次数（使用显式遍历避免 unknown 类型问题）
//       const dk: 'agent' | 'model' = (filters.value.agent ? 'agent' : 'model')
//       let calls = 0
//       const dayList = Object.values(countRes.data.data || {}) as Array<any>
//       for (const day of dayList) {
//         const map = (day?.[dk] || {}) as Record<string, number>
//         for (const v of Object.values(map)) calls += Number(v || 0)
//       }
//       totalCalls.value = calls
//     }

//     // 获取 Token 使用量数据
//     const statsRes = await getUsageStatsAPI(params)
//     if (statsRes.data.status_code === 200) {
//       updateTokenUsageChart(statsRes.data.data)
//       // 累计 Token（使用显式遍历避免 unknown 类型问题）
//       const dk: 'agent' | 'model' = (filters.value.agent ? 'agent' : 'model')
//       let tokens = 0
//       const dayList = Object.values(statsRes.data.data || {}) as Array<any>
//       for (const day of dayList) {
//         const map = (day?.[dk] || {}) as Record<string, { total_tokens?: number }>
//         for (const obj of Object.values(map)) tokens += Number(obj?.total_tokens || 0)
//       }
//       totalTokens.value = tokens
//     }

//     ElMessage.success('数据刷新成功')
//   } catch (error) {
//     console.error('获取使用统计数据失败:', error)
//     ElMessage.error('获取数据失败')
//   } finally {
//     loading.value = false
//   }
// }

// // 筛选条件变化
// const handleFilterChange = () => {
//   fetchUsageData()
// }

// // 刷新数据
// const handleRefresh = () => {
//   fetchUsageData()
// }

// // 窗口大小变化处理
// const handleResize = () => {
//   callCountChart?.resize()
//   tokenUsageChart?.resize()
// }


</script>

<style scoped lang="scss">
.dashboard-container {
  padding: 24px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
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
  margin-top: 24px;
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