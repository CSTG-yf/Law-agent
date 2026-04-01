<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import knowledgeIcon from '../../assets/knowledge.svg'
import { 
  getPromptsAPI,
  getPromptDetailAPI,
  type PromptSummary,
  type PromptDetail
} from '../../apis/prompt'

const prompts = ref<PromptSummary[]>([])
const promptsLoading = ref(false)
const selectedPrompt = ref<PromptDetail | null>(null)
const detailLoading = ref(false)

// 过滤条件
const category = ref('')
const tag = ref('')

const filteredPrompts = computed(() => {
  const c = category.value.trim().toLowerCase()
  const t = tag.value.trim().toLowerCase()
  return prompts.value.filter((p) => {
    const categoryOk = !c || (p.category || '').toLowerCase().includes(c)
    const tagOk = !t || (p.tags || []).some((x) => x.toLowerCase().includes(t))
    return categoryOk && tagOk
  })
})

const promptContent = computed(() => {
  if (!selectedPrompt.value) return ''
  return (
    selectedPrompt.value.content ||
    selectedPrompt.value.template ||
    selectedPrompt.value.text ||
    selectedPrompt.value.prompt ||
    ''
  )
})

// 获取提示词列表
const fetchPrompts = async () => {
  promptsLoading.value = true
  try {
    const res = await getPromptsAPI({
      category: category.value || undefined,
      tag: tag.value || undefined,
    })
    if (res.data.code === 200) {
      prompts.value = res.data.data?.prompts || []
      if (!selectedPrompt.value && prompts.value.length > 0) {
        // 默认选中第一个
        selectPrompt(prompts.value[0])
      }
    } else {
      ElMessage.error(res.data.message || '获取提示词失败')
    }
  } catch (error) {
    console.error('获取提示词失败:', error)
    ElMessage.error('获取提示词失败')
  } finally {
    promptsLoading.value = false
  }
}

// 选择提示词并加载详情
const selectPrompt = async (item: PromptSummary) => {
  selectedPrompt.value = {
    id: item.id,
    label: item.label,
    category: item.category,
    tags: item.tags,
    description: item.description,
    source_file: item.source_file,
  }
  detailLoading.value = true
  try {
    const res = await getPromptDetailAPI(item.id)
    if (res.data.code === 200) {
      selectedPrompt.value = res.data.data || selectedPrompt.value
    } else {
      ElMessage.error(res.data.message || '获取提示词详情失败')
    }
  } catch (error) {
    console.error('获取提示词详情失败:', error)
    ElMessage.error('获取提示词详情失败')
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  fetchPrompts()
})
</script>

<template>
  <div class="prompt-page">
    <div class="page-header">
      <div class="header-title">
        <img :src="knowledgeIcon" alt="提示词" class="title-icon" />
        <h2>提示词管理</h2>
      </div>
      <div class="header-actions">
        <el-input
          v-model="category"
          placeholder="按分类过滤（可选）"
          size="small"
          style="width: 180px; margin-right: 8px;"
          clearable
        />
        <el-input
          v-model="tag"
          placeholder="按标签过滤（可选）"
          size="small"
          style="width: 180px; margin-right: 12px;"
          clearable
        />
        <el-button type="primary" @click="fetchPrompts">
          刷新
        </el-button>
      </div>
    </div>

    <div class="prompts-wrapper">
      <!-- 左侧提示词列表 -->
      <div class="prompts-list" v-loading="promptsLoading">
        <div v-if="filteredPrompts.length === 0" class="empty-prompts">
          暂无提示词
        </div>
        <ul v-else>
          <li
            v-for="p in filteredPrompts"
            :key="p.id"
            :class="['prompt-item', { active: selectedPrompt && selectedPrompt.id === p.id }]"
            @click="selectPrompt(p)"
          >
            <div class="prompt-name">{{ p.label || p.id }}</div>
            <div class="prompt-meta">
              <span v-if="p.category">{{ p.category }}</span>
              <span v-if="p.tags && p.tags.length" class="tags">
                {{ p.tags.join(' / ') }}
              </span>
            </div>
          </li>
        </ul>
      </div>

      <!-- 右侧提示词详情 -->
      <div class="prompt-detail" v-if="selectedPrompt">
        <h3 class="detail-title">{{ selectedPrompt.label || selectedPrompt.id }}</h3>
        <p class="detail-meta">
          <span v-if="selectedPrompt.category" class="meta-label">分类</span>
          <span v-if="selectedPrompt.category" class="meta-badge category-badge">
            {{ selectedPrompt.category }}
          </span>
          <template v-if="selectedPrompt.tags && selectedPrompt.tags.length">
            <span class="meta-label meta-label-tags">标签</span>
            <span
              v-for="tagItem in selectedPrompt.tags"
              :key="tagItem"
              class="meta-badge tag-badge"
            >
              {{ tagItem }}
            </span>
          </template>
        </p>
        <p v-if="selectedPrompt.description" class="detail-desc">
          {{ selectedPrompt.description }}
        </p>
        <div class="detail-content">
          <div v-if="detailLoading" class="detail-loading">正在加载提示词内容...</div>
          <pre v-else>{{ promptContent }}</pre>
        </div>
      </div>
      <div class="prompt-detail empty" v-else>
        请选择左侧的提示词查看详情
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.prompt-page {
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
      display: flex;
      align-items: center;
    }
  }
}

.prompts-wrapper {
  margin-top: 24px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 16px;
  height: calc(100vh - 160px);
}

.prompts-list {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 12px;
  overflow-y: auto;
}

.prompts-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.prompt-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
  margin-bottom: 6px;
}

.prompt-item:hover {
  background: #f3f4f6;
}

.prompt-item.active {
  background: #e0f2fe;
  box-shadow: 0 0 0 1px #38bdf8;
}

.prompt-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.prompt-meta {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
  display: flex;
  justify-content: space-between;
}

.prompt-meta .tags {
  color: #4b5563;
}

.empty-prompts {
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
  padding: 24px 0;
}

.prompt-detail {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  overflow-y: auto;
}

.prompt-detail.empty {
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

.detail-desc {
  margin-top: 8px;
  font-size: 14px;
  color: #4b5563;
}

.detail-content {
  margin-top: 16px;
}

.detail-loading {
  color: #6b7280;
  font-size: 14px;
}

.detail-content pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  line-height: 1.7;
  background: #f9fafb;
  border-radius: 10px;
  padding: 16px 18px;
  border: 1px solid #e5e7eb;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.08);
  color: #111827;
}

.meta-label {
  font-size: 12px;
  font-weight: 600;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 6px;
}

.meta-label-tags {
  margin-left: 16px;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  margin-right: 6px;
}

.category-badge {
  background: rgba(59, 130, 246, 0.08);
  color: #1d4ed8;
  border: 1px solid rgba(59, 130, 246, 0.18);
}

.tag-badge {
  background: rgba(16, 185, 129, 0.06);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.18);
}
</style>
