<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElDialog, ElForm, ElFormItem, ElInput, ElButton } from 'element-plus'
import 'element-plus/es/components/dialog/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/form-item/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/button/style/css'
import { Plus, Document, Folder, Edit, Delete } from '@element-plus/icons-vue'
import knowledgeIcon from '../../assets/knowledge.svg'
import { 
  getRagDocumentsAPI,
  getRagDocumentContentAPI,
  deleteRagDocumentAPI,
  uploadRagDocumentAPI,
  uploadRagDocumentsBatchAPI,
  type RagDocumentResponse
} from '../../apis/knowledge'

const documents = ref<RagDocumentResponse[]>([])
const documentsLoading = ref(false)
const selectedDocument = ref<RagDocumentResponse | null>(null)
const documentContent = ref('')
const documentContentLoading = ref(false)
const uploading = ref(false)
const batchUploading = ref(false)
const deleting = ref(false)
const deleteDialogVisible = ref(false)
const uploadResultVisible = ref(false)
const uploadResultTitle = ref('')
const uploadResultMessage = ref('')

// 查询相关状态
const searchVisible = ref(false)
const searchKeyword = ref('')

// 基于关键字过滤后的文档列表
const filteredDocuments = computed(() => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) return documents.value
  return documents.value.filter((doc) => doc.file_name.toLowerCase().includes(keyword.toLowerCase()))
})

// 当前文档是否为 PDF
const isPdfDocument = computed(() => {
  const name = selectedDocument.value?.file_name || ''
  return name.toLowerCase().endsWith('.pdf')
})

// 规范化 PDF 页面文本：去掉页码行、压缩空行，并按段落合并行，提高可读性
const normalizePdfPageText = (text: string) => {
  const rawLines = text.split(/\r?\n/)

  // 先清理掉页码行和空白行，保留需要的文本
  const cleanedLines: string[] = []
  for (const line of rawLines) {
    const trimmed = line.trim()

    // 跳过形如 "[页面2]" 的标记
    if (/^\[页面\d+\]$/.test(trimmed)) continue
    // 跳过形如 "- 2 -" 这类页码行
    if (/^-+\s*\d+\s*-+$/.test(trimmed)) continue

    cleanedLines.push(trimmed)
  }

  // 再按段落合并：连续非空行合并成一个段落，段落之间用一个空行分隔
  const paragraphs: string[] = []
  let currentParagraph = ''

  for (const line of cleanedLines) {
    if (!line) {
      if (currentParagraph) {
        paragraphs.push(currentParagraph)
        currentParagraph = ''
      }
      continue
    }

    currentParagraph += (currentParagraph ? ' ' : '') + line
  }

  if (currentParagraph) {
    paragraphs.push(currentParagraph)
  }

  return paragraphs.join('\n\n').trim()
}

// 针对 PDF 的分页内容（根据 [页面1]、[页面2] 等标记拆分，同一页码会自动合并并做文本规范化）
const pdfPages = computed(() => {
  if (!isPdfDocument.value) return [] as { title: string; content: string }[]

  const raw = documentContent.value || ''
  if (!raw) return [] as { title: string; content: string }[]

  const pagesMap = new Map<string, string>()
  const regex = /\[页面(\d+)\]/g

  let lastIndex = 0
  let currentPageNo: string | null = null
  let match: RegExpExecArray | null

  // 遍历所有页码标记，把中间的文本归属到对应的页面里
  while ((match = regex.exec(raw)) !== null) {
    const pageNo = match[1]

    if (currentPageNo) {
      const segment = raw.slice(lastIndex, match.index).trim()
      if (segment) {
        const existing = pagesMap.get(currentPageNo) || ''
        pagesMap.set(currentPageNo, existing ? `${existing}\n${segment}` : segment)
      }
    }

    currentPageNo = pageNo
    lastIndex = regex.lastIndex
  }

  // 处理最后一段文本
  if (currentPageNo) {
    const tail = raw.slice(lastIndex).trim()
    if (tail) {
      const existing = pagesMap.get(currentPageNo) || ''
      pagesMap.set(currentPageNo, existing ? `${existing}\n${tail}` : tail)
    }
  }

  // 如果没有识别到任何 [页面X] 标记，则整体作为一页
  if (pagesMap.size === 0) {
    return [
      {
        title: '全文',
        content: normalizePdfPageText(raw)
      }
    ]
  }

  // 根据页码排序并转换成数组
  return Array.from(pagesMap.entries())
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([pageNo, content]) => ({
      title: `第 ${pageNo} 页`,
      content: normalizePdfPageText(content)
    }))
})

// 触发文件选择
const fileInputRef = ref<HTMLInputElement | null>(null)
const handleClickUpload = () => {
  fileInputRef.value?.click()
}

// 查询按钮点击，切换输入框显示
const handleToggleSearch = () => {
  searchVisible.value = !searchVisible.value
}

// 确认查询
const handleSearchConfirm = () => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入要查询的文档名称')
    return
  }
  const matchCount = documents.value.filter((doc) =>
    doc.file_name.toLowerCase().includes(keyword.toLowerCase())
  ).length
  if (matchCount === 0) {
    ElMessage.info('未找到匹配的文档')
  } else {
    ElMessage.success(`共找到 ${matchCount} 个匹配文档`)
  }
}

// 触发批量 ZIP 上传
const batchFileInputRef = ref<HTMLInputElement | null>(null)
const handleClickBatchUpload = () => {
  batchFileInputRef.value?.click()
}

// 处理文件选择并上传
const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  // 这里先传一个简单的 metadata 示例，你可以根据需要改成真正的分类/作者等
  formData.append('metadata', JSON.stringify({ category: '默认分类', author: '未知' }))

  uploading.value = true
  try {
    console.log('正在上传文件:', file.name, '参数', formData)
    const res = await uploadRagDocumentAPI(formData)
    // 在控制台查看后端完整响应
    console.log('文件上传响应:', res)
    // 一般我们更关心 res.data 的内容
    console.log('上传返回的数据:', res.data)
    const successMsg = (res.data as any)?.message || '文档上传成功，正在后台处理'
    ElMessage.success(successMsg)
    uploadResultTitle.value = '上传成功'
    uploadResultMessage.value = successMsg
    uploadResultVisible.value = true
    // 上传完成后，重新拉取一次文档列表
    await handleGetDocuments()
  } catch (error) {
    console.error('上传文档失败:', error)
    const errMessage =
      (error as any)?.response?.data?.status_message ||
      (error as any)?.response?.data?.message ||
      (error as any)?.message ||
      '上传文档失败'
    ElMessage.error(errMessage)
    uploadResultTitle.value = '上传失败'
    uploadResultMessage.value = errMessage
    uploadResultVisible.value = true
  } finally {
    uploading.value = false
    // 清空 input，避免同一个文件无法再次选择
    if (input) input.value = ''
  }
}

// 处理 ZIP 批量上传
const handleBatchFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('metadata', JSON.stringify({ category: '默认分类', tags: ['批量上传'] }))

  batchUploading.value = true
  try {
    console.log('正在批量上传 ZIP 文件:', file.name, '参数', formData)
    const res = await uploadRagDocumentsBatchAPI(formData)
    console.log('批量上传响应:', res)
    console.log('批量上传返回的数据:', res.data)
    const successMsg = (res.data as any)?.message || 'ZIP 批量上传成功，正在后台处理'
    ElMessage.success(successMsg)
    uploadResultTitle.value = '批量上传成功'
    uploadResultMessage.value = successMsg
    uploadResultVisible.value = true
    await handleGetDocuments()
  } catch (error) {
    console.error('批量上传文档失败:', error)
    const errMessage =
      (error as any)?.response?.data?.status_message ||
      (error as any)?.response?.data?.message ||
      (error as any)?.message ||
      '批量上传文档失败'
    ElMessage.error(errMessage)
    uploadResultTitle.value = '批量上传失败'
    uploadResultMessage.value = errMessage
    uploadResultVisible.value = true
  } finally {
    batchUploading.value = false
    if (input) input.value = ''
  }
}

// 点击删除按钮：只负责打开本页内的确认弹框
const handleDeleteDocument = () => {
  console.log('点击删除文档按钮，当前选中文档：', selectedDocument.value)
  if (!selectedDocument.value) {
    ElMessage.warning('请先在左侧选择要删除的文档')
    return
  }
  deleteDialogVisible.value = true
}

// 在确认弹框中点击“确认删除”后，执行真正的删除请求
const handleConfirmDelete = async () => {
  if (!selectedDocument.value) {
    deleteDialogVisible.value = false
    return
  }

  deleteDialogVisible.value = false
  deleting.value = true
  try {
    const res = await deleteRagDocumentAPI(selectedDocument.value.file_hash)
    console.log('删除文档响应:', res)
    const successMsg = res.data?.message || '删除任务已提交，后台正在处理'
    ElMessage.success(successMsg)
    await ElMessageBox.alert(successMsg, '删除成功', {
      type: 'success'
    })
    // 删除后刷新列表并清空选中
    selectedDocument.value = null
    documentContent.value = ''
    await handleGetDocuments()
  } catch (error) {
    console.error('删除文档失败:', error)
    const errMessage =
      (error as any)?.response?.data?.status_message ||
      (error as any)?.response?.data?.message ||
      (error as any)?.message ||
      '删除文档失败'
    ElMessage.error(errMessage)
    await ElMessageBox.alert(errMessage, '删除失败', {
      type: 'error'
    })
  } finally {
    deleting.value = false
  }
}

// 获取文档列表
const handleGetDocuments = async () => {
  documentsLoading.value = true
  try {
    const response = await getRagDocumentsAPI()
    console.log('后端返回数据:', response.data)
    if (response.status === 200 && response.data) {
      // 后端返回结构: { documents: RagDocumentResponse[], total: number }
      documents.value = response.data.documents || []
      ElMessage.success('获取文档成功')
    } else {
      ElMessage.error('获取文档失败')
    }
  } catch (error) {
    console.error('获取文档失败:', error)
    ElMessage.error('获取文档失败')
  } finally {
    documentsLoading.value = false
  }
}

// 选中文档并加载内容
const handleSelectDocument = async (doc: RagDocumentResponse) => {
  selectedDocument.value = doc
  documentContent.value = ''
  documentContentLoading.value = true
  try {
    const res = await getRagDocumentContentAPI(doc.file_hash)
    console.log('获取文档内容响应:', res)
    // 后端返回结构：{ code, message, data: { full_content: string, ... } }
    const payload: any = res.data
    const fullContent = payload?.data?.full_content
    documentContent.value = typeof fullContent === 'string' ? fullContent : ''
  } catch (error) {
    console.error('获取文档内容失败:', error)
    ElMessage.error('获取文档内容失败')
  } finally {
    documentContentLoading.value = false
  }
}

onMounted(() => {
  handleGetDocuments()
})
</script>

<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div class="header-title">
        <img :src="knowledgeIcon" alt="知识库" class="title-icon" />
        <h2>知识库管理</h2>
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
        <el-button type="success" @click="handleGetDocuments" style="margin-left: 12px;">
          获取文档
        </el-button>
        <el-button type="primary" :loading="uploading" @click="handleClickUpload" style="margin-left: 12px;">
          上传文档
        </el-button>
        
        <el-button type="primary" plain :loading="batchUploading" @click="handleClickBatchUpload" style="margin-left: 12px;">
          批量上传（ZIP）
        </el-button>

        <el-button
          type="danger"
          plain
          :loading="deleting"
          :disabled="!selectedDocument"
          @click="handleDeleteDocument"
          style="margin-left: 12px;"
        >
          删除文档
        </el-button>
        <!-- 隐藏的原生文件选择框 -->
        <input
          ref="fileInputRef"
          type="file"
          style="display: none;"
          @change="handleFileChange"
        />
        <input
          ref="batchFileInputRef"
          type="file"
          accept=".zip"
          style="display: none;"
          @change="handleBatchFileChange"
        />
      </div>
    </div>
    <div class="documents-wrapper">
      <!-- 左侧文档列表 -->
      <div class="documents-list" v-loading="documentsLoading">
        <div v-if="documents.length === 0" class="empty-documents">
          暂无文档
        </div>
        <ul v-else>
          <li
            v-for="doc in filteredDocuments"
            :key="doc.file_hash"
            :class="['document-item', { active: selectedDocument && selectedDocument.file_hash === doc.file_hash }]"
            @click="handleSelectDocument(doc)"
          >
            <div class="doc-name">{{ doc.file_name }}</div>
            <div class="doc-meta">{{ doc.chunks_count }} 个分片</div>
          </li>
        </ul>
      </div>

      <!-- 右侧文档内容/详情 -->
      <div class="document-detail" v-if="selectedDocument">
        <!-- <h3 class="detail-title">{{ selectedDocument.file_name }}</h3> -->
        <!-- <p class="detail-meta">
          文件哈希：{{ selectedDocument.file_hash }}<br />
          分片数：{{ selectedDocument.chunks_count }}<br />
          上传时间：{{ selectedDocument.uploaded_at || '未知' }}
        </p> -->
        <div class="detail-content">
          <div v-if="documentContentLoading" class="detail-loading">正在加载文档内容...</div>
          <template v-else>
            <!-- PDF 文档分页排版展示 -->
            <div v-if="isPdfDocument && pdfPages.length" class="pdf-pages-wrapper">
              <div
                v-for="(page, index) in pdfPages"
                :key="index"
                class="pdf-page"
              >
                <div class="pdf-page-header">{{ page.title }}</div>
                <div class="pdf-page-content">{{ page.content }}</div>
              </div>
            </div>
            <!-- 其他文档类型保持原来的预格式文本展示 -->
            <pre v-else>{{ documentContent }}</pre>
          </template>
        </div>
        <!-- <p class="detail-placeholder">
          这里暂时显示文档的基本信息。如果后端提供文档内容接口，可以在这里加载并展示具体内容。
        </p> -->
      </div>
      <div class="document-detail empty" v-else>
        请选择左侧的文档查看详情
      </div>
    </div>
    <!-- 上传结果弹框（单个/批量共用） -->
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
    <!-- 删除确认原生弹框 -->
    <div v-if="deleteDialogVisible" class="dialog-overlay">
      <div class="delete-dialog-container">
        <div class="delete-dialog-body">
          <p>
            确定要删除文档
            <strong>{{ selectedDocument?.file_name }}</strong>
            及其所有分片吗？
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
  </div>
</template>

<style lang="scss" scoped>
.knowledge-page {
  padding: 32px;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    padding: 20px 28px;
    border-radius: 16px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
    border: 1px solid rgba(226, 232, 240, 0.6);

    .header-title {
      display: flex;
      align-items: center;
      gap: 14px;
      
      .title-icon {
        width: 36px;
        height: 36px;
      }
      
      h2 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
        background: linear-gradient(90deg, #1B7CE4, #409eff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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
  }
  
  .knowledge-container {
    background: white;
    border-radius: 16px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
    border: 1px solid rgba(226, 232, 240, 0.6);
    overflow: hidden;
    
    .list-header {
      display: grid;
      grid-template-columns: 2fr 3fr 1fr 1fr 1.2fr 1.5fr;
      gap: 16px;
      padding: 16px 24px;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      border-bottom: 2px solid #e1e5e9;
      font-weight: 600;
      font-size: 13px;
      color: #606266;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      
      > div {
        display: flex;
        align-items: center;
        gap: 6px;
        
        .el-icon, svg {
          font-size: 14px;
          color: #909399;
        }
      }
    }
    
    .knowledge-list {
      .knowledge-row {
        display: grid;
        grid-template-columns: 2fr 3fr 1fr 1fr 1.2fr 1.5fr;
        gap: 16px;
        padding: 20px 24px;
        border-bottom: 1px solid #f0f2f5;
        transition: all 0.2s ease;
        cursor: pointer;
        align-items: center;
        
        &:hover {
          background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f5 100%);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        
        &:last-child {
          border-bottom: none;
        }
        
        .col-name {
          .knowledge-info {
            display: flex;
            align-items: center;
            gap: 12px;
            
            .knowledge-avatar {
              width: 40px;
              height: 40px;
              border-radius: 10px;
              background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
              display: flex;
              align-items: center;
              justify-content: center;
              flex-shrink: 0;
              
              img {
                width: 24px;
                height: 24px;
              }
            }
            
            .knowledge-name {
              font-size: 15px;
              font-weight: 600;
              color: #303133;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
          }
        }
        
        .col-desc {
          .knowledge-desc {
            font-size: 14px;
            color: #606266;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: block;
          }
        }
        
        .col-files {
          .file-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            color: #1976d2;
            
            .el-icon {
              font-size: 14px;
            }
          }
        }
        
        .col-size {
          .size-text {
            font-size: 14px;
            font-weight: 500;
            color: #606266;
          }
        }
        
        .col-time {
          .time-text {
            font-size: 13px;
            color: #909399;
          }
        }
        
        .col-actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
          
          .action-btn {
            width: 36px;
            height: 36px;
            border: 1px solid #e1e5e9;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #606266;
            
            .el-icon {
              font-size: 18px;
            }
            
            &:hover {
              transform: translateY(-2px);
              box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
            
            &.view-btn:hover {
              background: #409eff;
              border-color: #409eff;
              color: white;
            }
            
            &.edit-btn:hover {
              background: #67c23a;
              border-color: #67c23a;
              color: white;
            }
            
            &.delete-btn:hover {
              background: #f56c6c;
              border-color: #f56c6c;
              color: white;
            }
          }
        }
      }
    }
  }
}

.documents-wrapper {
  margin-top: 24px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 16px;
  height: calc(100vh - 160px);
}

.documents-list {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 12px;
  overflow-y: auto;
}

.documents-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.document-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
  margin-bottom: 6px;
}

.document-item:hover {
  background: #f3f4f6;
}

.document-item.active {
  background: #e0f2fe;
  box-shadow: 0 0 0 1px #38bdf8;
}

.doc-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.doc-meta {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.empty-documents {
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
  padding: 24px 0;
}

.document-detail {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  overflow-y: auto;
}

.document-detail.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 14px;
}

.detail-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.detail-meta {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
}

.detail-placeholder {
  margin-top: 16px;
  font-size: 14px;
  color: #4b5563;
}

/* PDF 文档分页阅读样式 */
.detail-content {
  height: 100%;
}

.pdf-pages-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pdf-page {
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  width: 100%;
  box-sizing: border-box;
}

.pdf-page-header {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 8px;
}

.pdf-page-content {
  font-size: 14px;
  line-height: 1.8;
  color: #111827;
  white-space: pre-wrap;
}

/* 原生对话框样式 */
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
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  width: 500px;
  max-width: 90vw;
  max-height: 80vh;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 20px 0 20px;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 20px;
  
  h3 {
    margin: 0;
    font-size: 18px;
    color: #303133;
  }
  
  .close-btn {
    background: none;
    border: none;
    font-size: 24px;
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
  padding: 0 20px 20px 20px;
  
  .form-item {
    margin-bottom: 20px;
    
    label {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      color: #606266;
      font-weight: 500;
    }
    
    input, textarea {
      width: 100%;
      padding: 12px;
      border: 1px solid #dcdfe6;
      border-radius: 4px;
      font-size: 14px;
      box-sizing: border-box;
      transition: border-color 0.2s;
      
      &:focus {
        outline: none;
        border-color: #409eff;
      }
      
      &::placeholder {
        color: #c0c4cc;
      }
    }
    
    textarea {
      resize: vertical;
      font-family: inherit;
    }
  }
}

.dialog-footer {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  
  button {
    padding: 8px 20px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      opacity: 0.8;
    }
    
    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
  
  .primary-btn {
    background: #409eff;
    color: white;
    border-color: #409eff;
    
    &:hover:not(:disabled) {
      background: #66b1ff;
      border-color: #66b1ff;
    }
  }
}

/* 输入框字符计数器样式 */
.input-with-count, .textarea-with-count {
  position: relative;
  
  input.error, textarea.error {
    border-color: #f56c6c !important;
    box-shadow: 0 0 0 2px rgba(245, 108, 108, 0.2);
  }
  
  .char-count {
    position: absolute;
    font-size: 11px;
    color: #909399;
    background: rgba(255, 255, 255, 0.9);
    padding: 2px 4px;
    border-radius: 4px;
    font-weight: 500;
    
    &.error {
      color: #f56c6c;
      background: rgba(245, 108, 108, 0.1);
    }
  }
}

.input-with-count .char-count {
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
}

.textarea-with-count .char-count {
  right: 8px;
  bottom: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  margin: 20px auto;
  max-width: 600px;
  
  .empty-icon {
    width: 120px;
    height: 120px;
    display: flex;
    justify-content: center;
    align-items: center;
    background: rgba(64, 158, 255, 0.1);
    border-radius: 50%;
    margin-bottom: 20px;
    
    .empty-icon-symbol {
      font-size: 60px;
    }
    
    .empty-icon-img {
      width: 60px;
      height: 60px;
      object-fit: contain;
    }
  }
  
  h3 {
    font-size: 20px;
    color: #303133;
    margin: 0 0 16px;
  }
  
  p {
    margin: 0 0 20px;
    font-size: 16px;
    color: #909399;
    max-width: 300px;
  }
  
  .create-btn {
    padding: 12px 24px;
    font-size: 16px;
  }
}

/* 删除确认对话框样式 */
.delete-dialog-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  width: 400px;
  max-width: 90vw;
  overflow: hidden;
}

.delete-dialog-body {
  padding: 30px;
  
  p {
    margin: 0;
    font-size: 16px;
    color: #303133;
    line-height: 1.6;
    
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
  padding: 20px 30px;
  background: #f8fafc;
  border-top: 1px solid #e4e7ed;
}

.delete-dialog-btn {
  padding: 10px 24px;
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
    color: white;
    
    &:hover:not(:disabled) {
      background: #f78989;
    }
  }
}
</style> 