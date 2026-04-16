<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import knowledgeIcon from '../../assets/exported_image.svg'
import {
  getGraphDocumentInfoAPI,
  getGraphDocumentsAPI,
  uploadGraphDocumentAPI,
  deleteGraphDocumentAPI,
  clearGraphAPI,
  getGraphTaskStatusAPI,
  type GraphDocumentResponse,
  getGraphVisualizationAPI,
  type GraphVisualizationRequest
} from '../../apis/knowledge-graph'

type GraphNode = {
  id: string
  name: string
  category?: number
  value?: number
  symbolSize?: number
  itemStyle?: {
    color?: string
  }
  x?: number
  y?: number
  fixed?: boolean
}

type GraphLink = {
  source: string
  target: string
  name?: string
}

const CATEGORY_DEFINITIONS = [
  { name: '法律文书', color: '#3b82f6' },
  { name: '法条', color: '#a3e635' },
  { name: '法律主体', color: '#ef4444' },
  { name: '法律概念', color: '#4b5563' },
  { name: '其他', color: '#38bdf8' }
] as const

const documents = ref<GraphDocumentResponse[]>([])
const documentsLoading = ref(false)
const selectedDocument = ref<GraphDocumentResponse | null>(null)
const graphLoading = ref(false)
const graphRawData = ref<Record<string, any> | null>(null)
const graphSourceData = ref<Record<string, any> | null>(null)
const searchVisible = ref(false)
const searchKeyword = ref('')
const uploading = ref(false)
const deleting = ref(false)
const clearing = ref(false)
const uploadInputRef = ref<HTMLInputElement | null>(null)

// Last build task id from upload response.
const lastTaskId = ref('')

const uploadResultVisible = ref(false)
const uploadResultTitle = ref('')
const uploadResultMessage = ref('')

const deleteDialogVisible = ref(false)
const clearDialogVisible = ref(false)

const taskStatusDialogVisible = ref(false)
const taskStatusLoading = ref(false)
const taskStatusId = ref('')
const taskStatusResult = ref<Record<string, any> | null>(null)

const queryNodeTypes = ref<string[]>([])
const queryRelationTypes = ref<string[]>([])
const querySearchTerm = ref('')
const queryDepth = ref<number>(3)
const queryNodeLimit = ref<number>(10)
const querying = ref(false)

const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const getDisplayFileName = (fileName?: string | null) => {
  if (!fileName) return ''
  const lower = fileName.toLowerCase()

  const extensions = ['.doc', '.docx', '.pdf', '.txt']
  const matchedExt = extensions.find((ext) => lower.endsWith(ext))

  if (!matchedExt) return fileName

  return fileName.slice(0, fileName.length - matchedExt.length)
}

const getVisualizationPayload = (payload: Record<string, any> | null | undefined) => {
  return payload?.graph || payload?.data || payload || null
}

const extractGraphTypeOptions = (payload: Record<string, any> | null | undefined, kind: 'node' | 'relation') => {
  const graphPayload = getVisualizationPayload(payload)
  if (!graphPayload) return [] as string[]

  const items = kind === 'node' ? graphPayload.nodes : graphPayload.relationships
  if (!Array.isArray(items)) return [] as string[]

  const typeSet = new Set<string>()
  items.forEach((item: any) => {
    const typeValue = kind === 'node' ? item?.properties?.type : item?.type
    const normalized = String(typeValue || '').trim()
    if (normalized) {
      typeSet.add(normalized)
    }
  })

  return Array.from(typeSet).sort((left, right) => left.localeCompare(right, 'zh-Hans-CN'))
}

const nodeTypeOptions = computed(() => extractGraphTypeOptions(graphSourceData.value || graphRawData.value, 'node'))
const relationTypeOptions = computed(() => extractGraphTypeOptions(graphSourceData.value || graphRawData.value, 'relation'))

const handleClickUpload = () => {
  uploadInputRef.value?.click()
}
const handleToggleSearch = () => {
  searchVisible.value = !searchVisible.value
}

const handleSearchConfirm = () => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入要查询的文档名称')
    return
  }

  const matchCount = filteredDocuments.value.length
  if (matchCount === 0) {
    ElMessage.info('未找到匹配的文档')
  } else {
    ElMessage.success(`共找到 ${matchCount} 个匹配文档`)
  }
}

// 打开“查询任务状态”弹框
const handleOpenTaskStatusDialog = () => {
  taskStatusDialogVisible.value = true
  taskStatusResult.value = null
  // 默认使用最近一次上传返回的任务 ID
  if (lastTaskId.value) {
    taskStatusId.value = lastTaskId.value
  }
}

// 在弹框中根据 task_id 查询任务状态
const handleQueryTaskStatus = async () => {
  const id = taskStatusId.value.trim()
  if (!id) {
    ElMessage.warning('请先输入任务 ID')
    return
  }

  taskStatusLoading.value = true
  taskStatusResult.value = null

  try {
    const res = await getGraphTaskStatusAPI(id)
    taskStatusResult.value = res.data || null
  } catch (error) {
    console.error('查询知识图谱构建任务状态失败:', error)
    const errMsg =
      (error as any)?.response?.data?.message ||
      (error as any)?.message ||
      '查询任务状态失败'
    ElMessage.error(errMsg)
  } finally {
    taskStatusLoading.value = false
  }
}

// 点击删除按钮 -> 打开自定义确认弹框
const handleDeleteDocument = () => {
  if (!selectedDocument.value) {
    ElMessage.warning('请先在左侧选择要删除的文档')
    return
  }
  deleteDialogVisible.value = true
}

// 在删除确认弹框中点击“确认删除”后执行真正删除
const handleConfirmDelete = async () => {
  if (!selectedDocument.value) {
    deleteDialogVisible.value = false
    return
  }

  deleteDialogVisible.value = false
  deleting.value = true
  try {
    const res = await deleteGraphDocumentAPI(selectedDocument.value.file_hash)
    console.log('删除知识图谱文档响应:', res)
    const msg = (res.data as any)?.message || '删除任务已提交，后台正在处理'
    ElMessage.success(msg)
    selectedDocument.value = null
    graphRawData.value = null
    await handleGetDocuments()
  } catch (error) {
    console.error('删除知识图谱文档失败:', error)
    ElMessage.error('删除知识图谱文档失败')
  } finally {
    deleting.value = false
  }
}

const handleUploadFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_type', 'legal')

  uploading.value = true
  try {
    const res = await uploadGraphDocumentAPI(formData)
    const data: any = res?.data || {}

    if (res.status === 200 && (data.code === 200 || data.success)) {
      const taskId = data.task_id || data.data?.task_id
      if (taskId) {
        lastTaskId.value = taskId
      }

      const baseMsg = data.message || '文档上传成功，后台正在构建知识图谱'
      const successMsg = taskId ? `${baseMsg}（任务ID：${taskId}）` : baseMsg
      ElMessage.success(successMsg)
      uploadResultTitle.value = '上传成功'
      uploadResultMessage.value = successMsg
      uploadResultVisible.value = true
      await handleGetDocuments()
    } else {
      const errMsg = data.message || '上传文档失败'
      ElMessage.error(errMsg)
      uploadResultTitle.value = '上传失败'
      uploadResultMessage.value = errMsg
      uploadResultVisible.value = true
    }
  } catch (error) {
    console.error('上传知识图谱文档失败:', error)
    const errMsg =
      (error as any)?.response?.data?.status_message ||
      (error as any)?.response?.data?.message ||
      (error as any)?.message ||
      '上传文档失败'
    ElMessage.error(errMsg)
    uploadResultTitle.value = '上传失败'
    uploadResultMessage.value = errMsg
    uploadResultVisible.value = true
  } finally {
    uploading.value = false
    input.value = ''
  }
}

// 点击“清空知识图谱”按钮 -> 打开自定义确认弹框
const handleClearGraph = () => {
  clearDialogVisible.value = true
}

// 在清空确认弹框中点击“确定清空”后执行真正清空
const handleConfirmClearGraph = async () => {
  clearDialogVisible.value = false
  clearing.value = true
  graphLoading.value = true

  try {
    const res = await clearGraphAPI()
    const data: any = res.data || {}
    const ok = data.success === true || data.code === 200
    const msg = data.message || (ok ? '知识图谱已清空' : '清空知识图谱失败')

    if (!ok) {
      ElMessage.error(msg)
      return
    }

    ElMessage.success(msg)
    documents.value = []
    selectedDocument.value = null
    graphRawData.value = null
    graphSourceData.value = null
  } catch (error) {
    console.error('清空知识图谱失败:', error)
    ElMessage.error('清空知识图谱失败')
  } finally {
    clearing.value = false
    graphLoading.value = false
  }
}

const filteredDocuments = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return documents.value
  return documents.value.filter((doc) => (doc.file_name || '').toLowerCase().includes(keyword))
})

const buildGraphData = (payload: Record<string, any>, doc: GraphDocumentResponse): { nodes: GraphNode[]; links: GraphLink[] } => {
  // 兼容多种返回结构：
  // 1) { nodes, relationships }
  // 2) { data: { nodes, relationships }}
  // 3) { graph: { nodes, relationships }}
  const graphPayload = getVisualizationPayload(payload)
  const rawNodes = graphPayload?.nodes
  const rawLinks = graphPayload?.links || graphPayload?.edges || graphPayload?.relationships

  // 适配 /graph/visualization 返回格式：
  // nodes: [{ id, labels: [], properties: { name, ... } }]
  // relationships: [{ id, type, startNode, endNode, properties: {} }]
  if (Array.isArray(rawNodes) && rawNodes.length > 0) {
    const nodes: GraphNode[] = rawNodes.map((node: any, index: number) => {
      const labels = Array.isArray(node.labels) ? node.labels : []
      const props = node.properties || {}
      const type = String(props.type || '').toLowerCase()
      let category = 4
      if (type === 'legaldocument') category = 0
      else if (type === 'lawarticle') category = 1
      else if (type === 'legalsubject') category = 2
      else if (type === 'legalconcept') category = 3
      const fallbackName =
        props.name ||
        props.title ||
        props.label ||
        labels[0] ||
        node.name ||
        node.label ||
        node.id ||
        `节点${index + 1}`

      const rawSize = Number(node.symbolSize ?? node.size ?? 40)
      let symbolSize = Math.max(20, Math.min(rawSize, 40))

      const itemStyle = category === 2 ? { color: '#ef4444' } : undefined

      const nodeName = String(fallbackName).trim()
      const isMainLaw = nodeName === '本法'

      if (isMainLaw) {
        symbolSize = 72
      }

      return {
        id: String(node.id ?? node.name ?? `node-${index}`),
        name: nodeName,
        symbolSize,
        category,
        itemStyle,
        ...(isMainLaw
          ? {
              x: 0,
              y: 0,
              fixed: true
            }
          : {})
      }
    })

    const linksSource: any[] = Array.isArray(rawLinks) ? rawLinks : []
    const links: GraphLink[] = linksSource
      .map((link: any) => {
        const parseNodeId = (value: any): string | null => {
          if (value === null || value === undefined) return null
          const str = String(value).trim()
          if (!str || str === '{}' || str === "''") return null
          const match = str.match(/'id':\s*'([^']+)'/)
          if (match) return match[1]
          return str
        }

        const primarySource =
          link.source ??
          link.startNode ??
          link.start_node ??
          link.from ??
          link.start
        const primaryTarget =
          link.target ??
          link.endNode ??
          link.end_node ??
          link.to ??
          link.end

        let source = parseNodeId(primarySource)
        let target = parseNodeId(primaryTarget)

        const startNodeId = parseNodeId(link.startNode)
        const idNodeId = parseNodeId(link.id)

        if (!source && startNodeId) {
          source = startNodeId
        }

        if (!target && startNodeId && idNodeId && idNodeId !== startNodeId) {
          target = idNodeId
        }

        if (!source && idNodeId) {
          source = idNodeId
        }

        if (!source || !target || source === target) return null

        return {
          source,
          target,
          name: link.name || link.label || link.type || link.relation || ''
        } as GraphLink
      })
      .filter(Boolean) as GraphLink[]

    if (nodes.length > 0) {
      if (links.length > 0) {
        const connectedIds = new Set<string>()
        links.forEach((link) => {
          connectedIds.add(String(link.source))
          connectedIds.add(String(link.target))
        })
        const filteredNodes = nodes.filter((node) => connectedIds.has(String(node.id)))
        return { nodes: filteredNodes, links }
      }
      return { nodes, links }
    }
  }

  const triples = payload?.triples || payload?.relations || payload?.relationships || []
  if (Array.isArray(triples) && triples.length > 0) {
    const nodeMap = new Map<string, GraphNode>()
    const links: GraphLink[] = []

    triples.forEach((item: any) => {
      const subject = String(item.subject || item.head || item.source || '')
      const object = String(item.object || item.tail || item.target || '')
      const predicate = String(item.predicate || item.relation || item.label || '')

      if (!subject || !object) return

      if (!nodeMap.has(subject)) {
        nodeMap.set(subject, { id: subject, name: subject, symbolSize: 56, category: 1 })
      }

      if (!nodeMap.has(object)) {
        nodeMap.set(object, { id: object, name: object, symbolSize: 52, category: 2 })
      }

      links.push({
        source: subject,
        target: object,
        name: predicate
      })
    })

    const nodes = Array.from(nodeMap.values())
    if (nodes.length > 0) {
      if (links.length > 0) {
        const connectedIds = new Set<string>()
        links.forEach((link) => {
          connectedIds.add(String(link.source))
          connectedIds.add(String(link.target))
        })
        const filteredNodes = nodes.filter((node) => connectedIds.has(String(node.id)))
        return { nodes: filteredNodes, links }
      }
      return { nodes, links }
    }
  }

  const centerId = doc.file_hash
  const centerName = doc.file_name || '文档'
  const metadataEntries = Object.entries(payload || {})
    .filter(([key, value]) => {
      if (['graph', 'nodes', 'links', 'edges', 'triples', 'relations', 'relationships'].includes(key)) {
        return false
      }
      const valueType = typeof value
      return valueType === 'string' || valueType === 'number' || valueType === 'boolean'
    })
    .slice(0, 8)

  const nodes: GraphNode[] = [
    { id: centerId, name: centerName, symbolSize: 68, category: 0 }
  ]
  const links: GraphLink[] = []

  metadataEntries.forEach(([key, value], index) => {
    const nodeId = `${centerId}-${index}`
    nodes.push({
      id: nodeId,
      name: `${key}: ${String(value)}`,
      symbolSize: 44,
      category: 1
    })
    links.push({ source: centerId, target: nodeId, name: key })
  })

  return { nodes, links }
}

const initChart = () => {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
}

const renderChart = () => {
  if (!chartInstance || !selectedDocument.value || !graphRawData.value) return

  const { nodes, links } = buildGraphData(graphRawData.value, selectedDocument.value)

  const option: echarts.EChartsOption = {
    backgroundColor: '#ffffff',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: 'rgba(148, 163, 184, 0.5)',
      borderWidth: 1,
      textStyle: {
        color: '#e5e7eb',
        fontSize: 12
      },
      formatter: (params: any) => {
        if (params.dataType === 'edge') {
          return ''
        }

        const node = params.data || {}
        const categoryIndex = typeof node.category === 'number' ? node.category : -1
        const category =
          categoryIndex >= 0 && categoryIndex < CATEGORY_DEFINITIONS.length
            ? CATEGORY_DEFINITIONS[categoryIndex].name
            : '其他'
        const title = node.name || params.name

        return `
<div style="min-width: 140px;">
  <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
  <div style="font-size: 12px; color: #cbd5ff;">绫诲埆锛?{category}</div>
</div>`
      }
    },
    legend: {
      top: 10,
      left: 'center',
      itemWidth: 16,
      itemHeight: 10,
      itemGap: 18,
      icon: 'roundRect',
      textStyle: {
        color: '#475569',
        fontSize: 12
      },
      data: CATEGORY_DEFINITIONS.map((item) => item.name)
    },
    color: CATEGORY_DEFINITIONS.map((item) => item.color),
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        scaleLimit: {
          min: 0.3,
          max: 2.5
        },
        animationDurationUpdate: 500,
        force: {
          repulsion: 320,
          edgeLength: [90, 200],
          gravity: 0.04
        },
        draggable: true,
        label: {
          show: true,
          position: 'right',
          fontSize: 12,
          color: '#374151'
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 6,
        lineStyle: {
          color: '#cbd5f5',
          width: 1.4,
          curveness: 0.18,
          opacity: 0.8
        },
        edgeLabel: {
          show: false
        },
        data: nodes,
        links,
        categories: CATEGORY_DEFINITIONS.map((item) => ({
          name: item.name,
          itemStyle: {
            color: item.color
          }
        })),
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 1,
          shadowColor: 'rgba(15, 23, 42, 0.18)',
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowOffsetY: 4
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 2.4
          }
        }
      }
    ]
  }

  chartInstance.setOption(option, true)
  chartInstance.resize()
}

const loadVisualizationByDocument = async (doc: GraphDocumentResponse) => {
  const docInfoResp = await getGraphDocumentInfoAPI(doc.file_hash)
  const docInfoRaw: any = docInfoResp.data || {}
  const docInfoData = docInfoRaw.data ?? docInfoRaw
  const fileHash = docInfoData.file_hash || doc.file_hash

  const params: GraphVisualizationRequest = {
    node_limit: queryNodeLimit.value,
    depth: queryDepth.value || 3,
    file_hash: fileHash
  }

  const nodeTypes = queryNodeTypes.value.join(',')
  if (nodeTypes) {
    params.node_types = nodeTypes
  }

  const relationTypes = queryRelationTypes.value.join(',')
  if (relationTypes) {
    params.relation_types = relationTypes
  }

  const searchTerm = querySearchTerm.value.trim()
  if (searchTerm) {
    params.search_term = searchTerm
  }

  const response = await getGraphVisualizationAPI(params)
  const raw: any = response.data || {}
  const payload = raw.data ?? raw
  graphRawData.value = payload as Record<string, any>
  if (!graphSourceData.value) {
    graphSourceData.value = payload as Record<string, any>
  }

  await nextTick()
  initChart()
  renderChart()
}

const handleSelectDocument = async (doc: GraphDocumentResponse) => {
  selectedDocument.value = doc
  graphLoading.value = true
  graphRawData.value = null
  graphSourceData.value = null

  try {
    await loadVisualizationByDocument(doc)
  } catch (error) {
    console.error('获取知识图谱可视化数据失败:', error)
    ElMessage.error('获取知识图谱可视化数据失败')
  } finally {
    graphLoading.value = false
  }
}

const handleQueryGraph = async () => {
  if (!selectedDocument.value) {
    ElMessage.warning('请先在左侧选择文档')
    return
  }

  if (queryDepth.value <= 0) {
    ElMessage.warning('depth 必须大于 0')
    return
  }

  if (queryNodeLimit.value <= 0) {
    ElMessage.warning('node_limit 必须大于 0')
    return
  }

  querying.value = true
  graphLoading.value = true

  try {
    await loadVisualizationByDocument(selectedDocument.value)
  } catch (error) {
    console.error('查询知识图谱失败:', error)
    ElMessage.error('查询知识图谱失败')
  } finally {
    querying.value = false
    graphLoading.value = false
  }
}

const handleGetDocuments = async () => {
  documentsLoading.value = true
  try {
    console.log('正在获取知识图谱文档列表...')
    const response = await getGraphDocumentsAPI()
    const payload: any = response.data
    console.log('知识图谱文档列表响应:', response)
    console.log('知识图谱文档列表响应原始数据:', payload)

    if (payload && (payload.code === 200 || payload.status === 'success')) {
      const list = payload?.data?.documents || []
      documents.value = Array.isArray(list) ? list : []
    } else {
      const errMsg = payload?.message || '获取知识图谱文档列表失败'
      ElMessage.error(errMsg)
      documents.value = []
    }

    if (selectedDocument.value) {
      const latestSelected = documents.value.find((item) => item.file_hash === selectedDocument.value?.file_hash)
      if (!latestSelected) {
        selectedDocument.value = null
        graphRawData.value = null
        graphSourceData.value = null
      }
    }
  } catch (error) {
    console.error('获取知识图谱文档列表失败:', error)
    ElMessage.error('获取知识图谱文档列表失败')
  } finally {
    documentsLoading.value = false
  }
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(async () => {
  await handleGetDocuments()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<template>
  <div class="knowledge-graph-page">
    <div class="page-header">
      <div class="header-title">
        <img :src="knowledgeIcon" alt="知识图谱" class="title-icon" />
        <h2>知识图谱</h2>
      </div>
      <div class="header-actions">
        <el-button type="primary" plain @click="handleToggleSearch">
          查询文档
        </el-button>
        <template v-if="searchVisible">
          <el-input
            v-model="searchKeyword"
            placeholder="请输入文档名称"
            style="margin-left: 12px; width: 220px;"
            clearable
            size="small"
          />
          <el-button type="primary" size="small" @click="handleSearchConfirm" style="margin-left: 8px;">
            确认
          </el-button>
        </template>
        <el-button type="primary" plain @click="handleOpenTaskStatusDialog" style="margin-left: 12px">
          查询任务状态
        </el-button>
        <el-button type="primary" :loading="uploading" @click="handleClickUpload" style="margin-left: 12px">
          上传文档
        </el-button>
        <el-button type="success" @click="handleGetDocuments" style="margin-left: 12px">
          刷新文档
        </el-button>
        <el-button
          type="danger"
          plain
          :loading="deleting"
          :disabled="!selectedDocument"
          @click="handleDeleteDocument"
          style="margin-left: 12px"
        >
          删除文档
        </el-button>
        <el-button
          type="danger"
          :loading="clearing"
          @click="handleClearGraph"
          style="margin-left: 12px"
        >
          清空知识图谱
        </el-button>
        <input
          ref="uploadInputRef"
          type="file"
          class="hidden-file-input"
          accept=".pdf,.doc,.docx,.txt,.md"
          @change="handleUploadFileChange"
        />
      </div>
    </div>

    <div class="graph-layout">
      <div class="documents-list" v-loading="documentsLoading">
        <div class="list-title">文档列表</div>
        <div v-if="filteredDocuments.length === 0" class="empty-documents">暂无文档</div>
        <ul v-else>
          <li
            v-for="doc in filteredDocuments"
            :key="doc.file_hash"
            :class="['document-item', { active: selectedDocument?.file_hash === doc.file_hash }]"
            @click="handleSelectDocument(doc)"
          >
            <div class="doc-name">{{ getDisplayFileName(doc.file_name) }}</div>
            <div class="doc-meta">
              {{ doc.chunks_count ?? '-' }} 个分片
            </div>
          </li>
        </ul>
      </div>

      <div class="graph-panel" v-loading="graphLoading">
        <div class="query-bar">
          <div class="query-label">图谱查询</div>
          <el-input
            v-model="querySearchTerm"
            size="small"
            placeholder="节点名称"
            class="query-main-input"
            clearable
          />
          <el-select
            v-model="queryNodeTypes"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            clearable
            size="small"
            placeholder="节点类型"
            class="query-extra-input"
          >
            <el-option
              v-for="item in nodeTypeOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
          <el-select
            v-model="queryRelationTypes"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            clearable
            size="small"
            placeholder="关系类型"
            class="query-extra-input"
          >
            <el-option
              v-for="item in relationTypeOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
          <span class="query-limit-label">节点数量限制</span>
          <el-input-number
            v-model="queryNodeLimit"
            :min="1"
            :max="200"
            size="small"
            controls-position="right"
            class="query-limit-input"
          />
          <el-button
            type="primary"
            size="small"
            :loading="querying"
            @click="handleQueryGraph"
          >
            查询知识图谱
          </el-button>
        </div>

        <div class="panel-header" v-if="selectedDocument">
          <div class="panel-title">{{ getDisplayFileName(selectedDocument.file_name) }}</div>
          <!-- <div class="panel-subtitle">鏂囦欢鍝堝笇锛歿{ selectedDocument.file_hash }}</div> -->
        </div>

        <div v-if="selectedDocument" class="graph-body">
          <div ref="chartRef" class="graph-canvas"></div>
        </div>

        <div v-else class="empty-graph">
          请选择左侧文档查看知识图谱
        </div>
      </div>
    </div>

    <!-- 上传结果弹框（单文档上传） -->
    <div v-if="uploadResultVisible" class="dialog-overlay">
      <div class="dialog-container">
        <div class="dialog-header">
          <h3>{{ uploadResultTitle }}</h3>
          <button
            class="close-btn"
            type="button"
            @click="uploadResultVisible = false"
          >
            ×
          </button>
        </div>
        <div class="dialog-body">
          <p>{{ uploadResultMessage }}</p>
        </div>
        <div class="dialog-footer">
          <button
            class="primary-btn"
            type="button"
            @click="uploadResultVisible = false"
          >
            我知道了
          </button>
        </div>
      </div>
    </div>

    <!-- 查询任务状态弹框 -->
    <div v-if="taskStatusDialogVisible" class="dialog-overlay">
      <div class="dialog-container">
        <div class="dialog-header">
          <h3>查询知识图谱构建任务状态</h3>
          <button
            class="close-btn"
            type="button"
            @click="taskStatusDialogVisible = false"
          >
            ×
          </button>
        </div>
        <div class="dialog-body">
          <div class="task-status-form">
            <label class="task-status-label">
              任务 ID（task_id）
              <el-input
                v-model="taskStatusId"
                class="task-status-input"
                placeholder="请输入任务 ID"
                clearable
              />
            </label>
            <el-button
              type="primary"
              :loading="taskStatusLoading"
              @click="handleQueryTaskStatus"
            >
              查询
            </el-button>
          </div>
          <div v-if="taskStatusResult" class="task-status-result">
            <pre>{{ JSON.stringify(taskStatusResult, null, 2) }}</pre>
          </div>
          <div v-else class="task-status-empty">
            请输入任务 ID 并点击查询以查看任务状态。
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="primary-btn"
            type="button"
            @click="taskStatusDialogVisible = false"
          >
            关闭
          </button>
        </div>
      </div>
    </div>

    <!-- 删除知识图谱文档确认弹框 -->
    <div v-if="deleteDialogVisible" class="dialog-overlay">
      <div class="delete-dialog-container">
        <div class="delete-dialog-body">
          <p>
            确定要删除文档
            <strong>{{ selectedDocument?.file_name }}</strong>
            及其对应的知识图谱吗？
          </p>
        </div>
        <div class="delete-dialog-footer">
          <button
            class="delete-dialog-btn cancel-btn"
            type="button"
            @click="deleteDialogVisible = false"
            :disabled="deleting"
          >
            取消
          </button>
          <button
            class="delete-dialog-btn confirm-btn"
            type="button"
            @click="handleConfirmDelete"
            :disabled="deleting"
          >
            {{ deleting ? '正在删除...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 清空知识图谱确认弹框 -->
    <div v-if="clearDialogVisible" class="dialog-overlay">
      <div class="delete-dialog-container">
        <div class="delete-dialog-body">
          <p>
            确定要清空全部知识图谱数据吗？
            <strong>该操作不可恢复</strong>。
          </p>
        </div>
        <div class="delete-dialog-footer">
          <button
            class="delete-dialog-btn cancel-btn"
            type="button"
            @click="clearDialogVisible = false"
            :disabled="clearing || graphLoading"
          >
            取消
          </button>
          <button
            class="delete-dialog-btn confirm-btn"
            type="button"
            @click="handleConfirmClearGraph"
            :disabled="clearing || graphLoading"
          >
            {{ clearing || graphLoading ? '正在清空...' : '确定清空' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.knowledge-graph-page {
  min-height: 100vh;
  padding: 32px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px 24px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 8px 26px rgba(2, 6, 23, 0.05);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;

  .title-icon {
    width: 34px;
    height: 34px;
  }

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
    background: linear-gradient(90deg, #0f766e, #2563eb);
    -webkit-text-fill-color: transparent;
    -webkit-background-clip: text;
    background-clip: text;
  }
}

.header-actions {
  .el-button {
    font-weight: 600;
    letter-spacing: 0.025em;
    border-radius: 12px;
    padding: 12px 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(64, 158, 255, 0.3);
    }
  }
}

.graph-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  height: calc(100vh - 170px);
}

.documents-list {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  background: #ffffff;
  overflow-y: auto;
}

.list-title {
  font-size: 14px;
  font-weight: 700;
  margin: 4px 0 10px;
  color: #1e293b;
}

.documents-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.document-item {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid transparent;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: #f8fafc;
    border-color: #dbeafe;
  }

  &.active {
    background: #ecfeff;
    border-color: #22d3ee;
    box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
  }
}

.doc-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-all;
}

.doc-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.empty-documents,
.empty-graph {
  height: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 14px;
}

.graph-panel {
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
}

.query-bar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(90deg, #f9fafb 0%, #eff6ff 100%);
  gap: 8px;
}

.query-label {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  padding: 4px 10px;
  border-radius: 999px;
  background-color: rgba(37, 99, 235, 0.08);
}

.query-main-input {
  margin-left: 4px;
  max-width: 220px;
}

.query-extra-input {
  margin-left: 4px;
  max-width: 200px;
}

.query-limit-input {
  margin-left: 4px;
  width: 110px;
}

.query-limit-label {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}

.panel-header {
  padding: 14px 18px;
  border-bottom: 1px solid #f1f5f9;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.graph-body {
  flex: 1;
  min-height: 0;
}

.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 460px;
}

.hidden-file-input {
  display: none;
}

/* 通用遮罩弹框样式（上传结果、删除/清空确认共用） */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.dialog-container {
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.3);
  width: 420px;
  max-width: 90vw;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px 10px 20px;
  border-bottom: 1px solid #e4e7ed;

  h3 {
    margin: 0;
    font-size: 16px;
    color: #303133;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 20px;
    color: #909399;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;

    &:hover {
      color: #f56c6c;
    }
  }
}

.dialog-body {
  padding: 14px 20px 6px 20px;

  p {
    margin: 0;
    font-size: 14px;
    color: #303133;
    line-height: 1.7;
  }
}

.dialog-footer {
  padding: 12px 20px 16px 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  justify-content: flex-end;
}

.primary-btn {
  padding: 8px 22px;
  border-radius: 6px;
  border: none;
  background: #409eff;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: #66b1ff;
  }
}

/* 删除 / 清空确认弹框样式 */
.delete-dialog-container {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  width: 420px;
  max-width: 90vw;
  overflow: hidden;
}

.delete-dialog-body {
  padding: 26px 24px 10px 24px;

  p {
    margin: 0;
    font-size: 15px;
    color: #303133;
    line-height: 1.7;

    strong {
      color: #f56c6c;
      font-weight: 600;
    }
  }
}

.delete-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 18px 24px 20px 24px;
  background: #f8fafc;
  border-top: 1px solid #e4e7ed;
}

.delete-dialog-btn {
  padding: 8px 22px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &.cancel-btn {
    background: #f5f7fa;
    color: #606266;

    &:hover:not(:disabled) {
      background: #e4e7ed;
    }
  }

  &.confirm-btn {
    background: #f56c6c;
    color: #ffffff;

    &:hover:not(:disabled) {
      background: #f78989;
    }
  }
}

/* 查询任务状态表单和结果样式 */
.task-status-form {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 12px;
}

.task-status-label {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  color: #606266;
  flex: 1;
}

.task-status-input {
  margin-top: 4px;
}

.task-status-result {
  margin-top: 8px;
  max-height: 260px;
  overflow: auto;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  padding: 8px 10px;

  pre {
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.task-status-empty {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

@media (max-width: 1100px) {
  .knowledge-graph-page {
    padding: 16px;
  }

  .graph-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .documents-list {
    max-height: 280px;
  }

  .graph-canvas {
    min-height: 380px;
  }
}
</style>

