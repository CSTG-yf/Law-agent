# 法律文档管理模块使用指南

## 概述

法律文档管理模块是一个功能完整的文档管理系统，专门用于上传、存储、搜索和检索法律文档。该模块已集成到应用的布局系统中，可以在任何页面中使用。

## 功能特性

### 1. 文档上传
- 支持多种法律文档格式：PDF、DOC、DOCX、TXT、RTF、ODT、HTML
- 拖拽上传支持
- 文档分类管理（合同法、刑法、民法等）
- 标签系统，便于文档组织
- 文件大小显示和格式化

### 2. 文档搜索
- 全文搜索功能
- 按分类筛选
- 按标签搜索
- 实时搜索结果更新

### 3. 文档管理
- 查看文档内容
- 删除文档
- 选择文档用于对话
- 文档列表展示（名称、大小、上传日期、分类、标签）

### 4. 智能集成
- 自动提取相关文档内容
- 生成文档上下文提示
- 支持在 AI 对话中引用文档

## 安装和配置

模块已自动集成到布局系统中，无需额外配置。

## 使用方法

### 1. 打开法律文档面板

通过页面菜单（右上角三点菜单）中的 "Legal Documents" 选项打开/关闭法律文档面板。

### 2. 上传文档

1. 点击 "上传文档" 按钮
2. 选择或拖拽文件到上传区域
3. 选择文档分类
4. 添加标签（可选）
5. 点击 "上传文档"

### 3. 搜索文档

在搜索框中输入关键词，系统会实时过滤文档列表。支持：
- 文档名称搜索
- 文档内容搜索
- 标签搜索
- 分类筛选

### 4. 查看文档

点击文档列表中的 "眼睛" 图标查看完整文档内容。

### 5. 选择文档用于对话

点击文档列表项，该文档将被标记为选中状态，可用于后续的 AI 对话。

## API 参考

### 状态管理 Hook

```typescript
import { useLegalDocumentsStore } from '~/modules/legal-docs';

const {
  documents,           // 所有文档
  selectedDocumentId,  // 当前选中的文档 ID
  isPanelOpen,        // 面板是否打开
  searchQuery,        // 搜索查询
  selectedCategory,   // 选中的分类
  addDocument,        // 添加文档
  removeDocument,     // 删除文档
  updateDocument,     // 更新文档
  selectDocument,     // 选择文档
  togglePanel,       // 切换面板
  setSearchQuery,    // 设置搜索查询
  setSelectedCategory, // 设置分类
  clearAllDocuments, // 清除所有文档
} = useLegalDocumentsStore();
```

### 工具函数

```typescript
import {
  searchLegalDocuments,        // 搜索文档
  extractRelevantContent,     // 提取相关内容
  formatDocumentForChat,      // 格式化文档用于对话
  formatDocumentsForChat,     // 格式化多个文档
  createDocumentContextPrompt, // 创建文档上下文提示
} from '~/modules/legal-docs';
```

### 组件

```typescript
import {
  LegalDocumentUpload,        // 上传模态框
  LegalDocumentSearch,        // 搜索组件
  LegalDocumentsPanel,        // 面板组件
  LegalDocumentsDrawer,      // 桌面端抽屉
  LegalDocumentsMobileDrawer, // 移动端抽屉
} from '~/modules/legal-docs';
```

## 在 AI 对话中使用文档

### 示例 1：获取文档上下文

```typescript
import { useLegalDocumentsStore, createDocumentContextPrompt } from '~/modules/legal-docs';

function ChatComponent() {
  const { documents, selectedDocumentId } = useLegalDocumentsStore();
  
  const sendMessage = (userMessage: string) => {
    const selectedDoc = documents.find(doc => doc.id === selectedDocumentId);
    
    if (selectedDoc) {
      const context = createDocumentContextPrompt(userMessage, [selectedDoc]);
      const fullMessage = context + '\n\n' + userMessage;
      
      // 发送带有文档上下文的消息给 AI
      sendToAI(fullMessage);
    } else {
      sendToAI(userMessage);
    }
  };
  
  return <ChatUI onSend={sendMessage} />;
}
```

### 示例 2：搜索相关文档

```typescript
import { extractRelevantContent } from '~/modules/legal-docs';

function findRelevantDocuments(query: string) {
  const relevantDocs = extractRelevantContent(documents, query, 3);
  
  relevantDocs.forEach((result, index) => {
    console.log(`文档 ${index + 1}: ${result.document.name}`);
    console.log(`相关性: ${result.relevance}`);
    console.log(`片段: ${result.snippet}`);
  });
  
  return relevantDocs;
}
```

### 示例 3：格式化文档用于显示

```typescript
import { formatDocumentForChat } from '~/modules/legal-docs';

function displayDocument(document: LegalDocument) {
  const formatted = formatDocumentForChat(document);
  console.log(formatted);
  
  // 输出示例：
  // 【法律文档】合同样本.docx
  // 分类：合同法
  // 标签：合同, 民法, 2024
  // 文档内容：
  // 本合同由以下双方签订...
}
```

## 数据结构

### LegalDocument

```typescript
interface LegalDocument {
  id: string;           // 文档唯一 ID
  name: string;         // 文档名称
  type: string;         // 文件类型
  size: number;         // 文件大小（字节）
  content: string;      // 文档内容
  uploadedAt: number;    // 上传时间戳
  category?: string;     // 文档分类
  tags?: string[];      // 文档标签
  summary?: string;     // 文档摘要
}
```

## 预定义分类

- 合同法
- 刑法
- 民法
- 行政法
- 经济法
- 劳动法
- 知识产权法
- 国际法
- 其他

## 注意事项

1. **文件大小限制**：建议单个文件不超过 10MB
2. **内容存储**：文档内容以纯文本形式存储，格式化信息可能丢失
3. **搜索性能**：大量文档时，搜索可能会有延迟
4. **持久化**：文档数据存储在浏览器的 localStorage 中
5. **安全性**：敏感文档请勿上传到公共环境

## 扩展功能

### 添加自定义分类

修改 `LegalDocumentUpload.tsx` 中的 `LEGAL_CATEGORIES` 数组：

```typescript
const LEGAL_CATEGORIES = [
  '合同法',
  '刑法',
  '民法',
  // 添加你的自定义分类
  '自定义分类',
];
```

### 支持更多文件格式

修改 `LegalDocumentUpload.tsx` 中的 `LEGAL_FILE_TYPES` 数组：

```typescript
const LEGAL_FILE_TYPES = [
  '.pdf',
  '.doc',
  '.docx',
  // 添加更多格式
  '.xls',
  '.xlsx',
];
```

### 自定义搜索算法

修改 `legal-docs.utils.ts` 中的搜索函数以实现更复杂的搜索逻辑。

## 故障排除

### 问题：文档上传失败

**解决方案**：
- 检查文件格式是否在支持的列表中
- 确认文件大小是否过大
- 检查浏览器控制台是否有错误信息

### 问题：搜索结果不准确

**解决方案**：
- 尝试使用不同的关键词
- 检查文档内容是否正确提取
- 考虑添加更多标签以提高搜索准确性

### 问题：面板无法打开

**解决方案**：
- 检查是否有其他模态框打开
- 尝试刷新页面
- 检查浏览器控制台是否有错误

## 技术支持

如有问题，请查看项目文档或联系开发团队。
