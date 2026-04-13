<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import knowledgeIcon from '../../assets/exported_image.svg'
import {
  getGraphDocumentInfoAPI,
  getGraphDocumentsAPI,
  uploadGraphDocumentAPI,
  deleteGraphDocumentAPI,
  queryGraphAPI,
  clearGraphAPI,
  type GraphDocumentResponse,
  type GraphQueryRequest,
  postGraphVisualizationAPI,
  type GraphVisualizationRequest
} from '../../apis/knowledge-graph'

type GraphNode = {
  id: string
  name: string
  category?: number
  value?: number
  symbolSize?: number
}

type GraphLink = {
  source: string
  target: string
  name?: string
}

const documents = ref<GraphDocumentResponse[]>([])
const documentsLoading = ref(false)
const selectedDocument = ref<GraphDocumentResponse | null>(null)
const graphLoading = ref(false)
const graphRawData = ref<Record<string, any> | null>(null)
const searchVisible = ref(false)
const searchKeyword = ref('')
const uploading = ref(false)
const deleting = ref(false)
const clearing = ref(false)
const uploadInputRef = ref<HTMLInputElement | null>(null)

const queryType = ref<'entity' | 'relation' | 'cypher'>('relation')
const queryText = ref('')
const queryEntityType = ref('')
const queryRelationType = ref('')
const queryLimit = ref<number | null>(10)
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

const handleDeleteDocument = async () => {
  if (!selectedDocument.value) {
    ElMessage.warning('请先在左侧选择要删除的文档')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除文档 "${selectedDocument.value.file_name}" 及其对应的知识图谱吗？`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

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
      const successMsg = data.message || '文档上传成功，后台正在构建知识图谱'
      ElMessage.success(successMsg)
      await ElMessageBox.alert(successMsg, '上传结果', {
        type: 'success'
      })
      await handleGetDocuments()
    } else {
      const errMsg = data.message || '上传文档失败'
      ElMessage.error(errMsg)
      await ElMessageBox.alert(errMsg, '上传结果', {
        type: 'error'
      })
    }
  } catch (error) {
    console.error('上传知识图谱文档失败:', error)
    const errMsg =
      (error as any)?.response?.data?.status_message ||
      (error as any)?.response?.data?.message ||
      (error as any)?.message ||
      '上传文档失败'
    ElMessage.error(errMsg)
    await ElMessageBox.alert(errMsg, '上传结果', {
      type: 'error'
    })
  } finally {
    uploading.value = false
    input.value = ''
  }
}

const handleClearGraph = async () => {
  try {
    await ElMessageBox.confirm('确定要清空全部知识图谱数据吗？该操作不可恢复。', '清空确认', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

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
  const graphPayload = payload?.graph || payload
  const rawNodes = graphPayload?.nodes
  const rawLinks = graphPayload?.links || graphPayload?.edges || graphPayload?.relationships

  // 适配 /graph/visualization 返回格式：
  // nodes: [{ id, labels: [], properties: { name, ... } }]
  // relationships: [{ id, type, startNode, endNode, properties: {} }]
  if (Array.isArray(rawNodes) && Array.isArray(rawLinks) && rawNodes.length > 0) {
    const nodes: GraphNode[] = rawNodes.map((node: any, index: number) => {
      const labels = Array.isArray(node.labels) ? node.labels : []
      const props = node.properties || {}
      const fallbackName =
        props.name ||
        props.title ||
        props.label ||
        labels[0] ||
        node.name ||
        node.label ||
        node.id ||
        `节点${index + 1}`

      return {
        id: String(node.id ?? node.name ?? `node-${index}`),
        name: String(fallbackName),
        symbolSize: Number(node.symbolSize ?? node.size ?? 46),
        category: Number(node.category ?? (labels.length > 0 ? 1 : 0))
      }
    })

    const links: GraphLink[] = rawLinks
      .map((link: any) => {
        const source =
          link.source ??
          link.startNode ??
          link.start_node ??
          link.from ??
          link.start
        const target =
          link.target ??
          link.endNode ??
          link.end_node ??
          link.to ??
          link.end

        if (!source || !target) return null

        return {
          source: String(source),
          target: String(target),
          name: link.name || link.label || link.type || link.relation || ''
        } as GraphLink
      })
      .filter(Boolean) as GraphLink[]

    if (nodes.length > 0 && links.length > 0) {
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
      trigger: 'item'
    },
    legend: {
      top: 10,
      data: ['文档', '实体', '关联实体']
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        animationDurationUpdate: 500,
        force: {
          repulsion: 220,
          edgeLength: [80, 180],
          gravity: 0.06
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
          color: '#94a3b8',
          width: 1.6,
          curveness: 0.14
        },
        edgeLabel: {
          show: true,
          formatter: (params: any) => params.data?.name || '',
          fontSize: 10,
          color: '#64748b'
        },
        data: nodes,
        links,
        categories: [
          { name: '文档' },
          { name: '实体' },
          { name: '关联实体' }
        ],
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 1
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

  chartInstance.setOption(option)
  chartInstance.resize()
}

const handleSelectDocument = async (doc: GraphDocumentResponse) => {
  selectedDocument.value = doc
  graphLoading.value = true
  graphRawData.value = null

  try {
    const body: GraphVisualizationRequest = {
      node_limit: 100,
      depth: 2,
      search_term: getDisplayFileName(doc.file_name) || doc.file_name
    }

    const response = await postGraphVisualizationAPI(body)
    const raw: any = response.data || {}
    const payload = raw.data ?? raw
    graphRawData.value = payload as Record<string, any>

    await nextTick()
    initChart()
    renderChart()
  } catch (error) {
    console.error('获取知识图谱可视化数据失败:', error)
    ElMessage.error('获取知识图谱可视化数据失败')
  } finally {
    graphLoading.value = false
  }
}

const handleQueryGraph = async () => {
  const query = queryText.value.trim()
  if (!query) {
    ElMessage.warning('请输入查询内容')
    return
  }

  const payload: GraphQueryRequest = {
    query_type: queryType.value,
    query
  }

  if (queryLimit.value && queryLimit.value > 0) {
    payload.limit = queryLimit.value
  }

  if (queryType.value === 'entity') {
    const entity = queryEntityType.value.trim()
    if (entity) payload.entity_type = entity
  }

  if (queryType.value === 'relation') {
    const relation = queryRelationType.value.trim()
    if (relation) payload.relation_type = relation
  }

  querying.value = true
  graphLoading.value = true

  try {
    const response = await queryGraphAPI(payload)
    const data: any = response.data || {}

    const ok = data.success === true || data.code === 200
    if (!ok) {
      const msg = data.message || '查询知识图谱失败'
      ElMessage.error(msg)
      return
    }

    const results = data.results ?? data.data?.results ?? []
    const graphPayload = Array.isArray(results) && results.length > 0 ? results[0] : data.data || data

    graphRawData.value = graphPayload as Record<string, any>
    selectedDocument.value = {
      file_hash: 'graph-query',
      file_name: `查询：${query}`
    } as GraphDocumentResponse

    await nextTick()
    initChart()
    renderChart()
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
          <el-select v-model="queryType" size="small" class="query-type-select">
            <el-option label="实体查询" value="entity" />
            <el-option label="关系查询" value="relation" />
            <el-option label="Cypher 查询" value="cypher" />
          </el-select>
          <el-input
            v-model="queryText"
            size="small"
            placeholder="请输入查询内容"
            class="query-main-input"
            clearable
          />
          <el-input
            v-if="queryType === 'entity'"
            v-model="queryEntityType"
            size="small"
            placeholder="实体类型（可选）"
            class="query-extra-input"
            clearable
          />
          <el-input
            v-if="queryType === 'relation'"
            v-model="queryRelationType"
            size="small"
            placeholder="关系类型（可选）"
            class="query-extra-input"
            clearable
          />
          <el-input-number
            v-model="queryLimit"
            :min="1"
            :max="100"
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
          <!-- <div class="panel-subtitle">文件哈希：{{ selectedDocument.file_hash }}</div> -->
        </div>

        <div v-if="selectedDocument" class="graph-body">
          <div ref="chartRef" class="graph-canvas"></div>
        </div>

        <div v-else class="empty-graph">
          请选择左侧文档查看知识图谱
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

.query-type-select {
  width: 120px;
}

.query-main-input {
  margin-left: 4px;
  max-width: 280px;
}

.query-extra-input {
  margin-left: 4px;
  max-width: 200px;
}

.query-limit-input {
  margin-left: 4px;
  width: 110px;
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
