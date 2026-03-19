import type { LegalDocument } from './store-legal-docs';
import { useLegalDocumentsStore } from './store-legal-docs';

export function searchLegalDocuments(query: string, documents?: LegalDocument[]): LegalDocument[] {
  const docs = documents || useLegalDocumentsStore.getState().documents;
  
  if (!query.trim()) {
    return docs;
  }

  const lowerQuery = query.toLowerCase();
  
  return docs.filter((doc) => {
    const nameMatch = doc.name.toLowerCase().includes(lowerQuery);
    const contentMatch = doc.content.toLowerCase().includes(lowerQuery);
    const tagsMatch = doc.tags?.some((tag) => tag.toLowerCase().includes(lowerQuery));
    const categoryMatch = doc.category?.toLowerCase().includes(lowerQuery);
    
    return nameMatch || contentMatch || tagsMatch || categoryMatch;
  });
}

export function extractRelevantContent(documents: LegalDocument[], query: string, maxResults: number = 3): Array<{ document: LegalDocument; relevance: number; snippet: string }> {
  const results: Array<{ document: LegalDocument; relevance: number; snippet: string }> = [];
  
  const lowerQuery = query.toLowerCase();
  const queryTerms = lowerQuery.split(/\s+/).filter((term) => term.length > 1);
  
  for (const doc of documents) {
    let relevance = 0;
    let bestSnippet = '';
    
    const content = doc.content.toLowerCase();
    const name = doc.name.toLowerCase();
    
    if (name.includes(lowerQuery)) {
      relevance += 10;
    }
    
    for (const term of queryTerms) {
      const termCount = (content.match(new RegExp(term, 'g')) || []).length;
      relevance += termCount * 2;
      
      if (doc.tags?.some((tag) => tag.toLowerCase().includes(term))) {
        relevance += 5;
      }
      
      if (doc.category?.toLowerCase().includes(term)) {
        relevance += 3;
      }
    }
    
    if (relevance > 0) {
      const snippet = extractSnippet(doc.content, queryTerms, 200);
      results.push({
        document: doc,
        relevance,
        snippet,
      });
    }
  }
  
  results.sort((a, b) => b.relevance - a.relevance);
  
  return results.slice(0, maxResults);
}

function extractSnippet(content: string, queryTerms: string[], maxLength: number): string {
  const lowerContent = content.toLowerCase();
  
  for (const term of queryTerms) {
    const index = lowerContent.indexOf(term);
    if (index !== -1) {
      const start = Math.max(0, index - 50);
      const end = Math.min(content.length, index + term.length + 50);
      let snippet = content.slice(start, end);
      
      if (start > 0) snippet = '...' + snippet;
      if (end < content.length) snippet = snippet + '...';
      
      if (snippet.length <= maxLength) {
        return snippet;
      }
    }
  }
  
  return content.slice(0, maxLength) + '...';
}

export function formatDocumentForChat(document: LegalDocument): string {
  return `
【法律文档】${document.name}
分类：${document.category || '未分类'}
${document.tags ? `标签：${document.tags.join(', ')}` : ''}
文档内容：
${document.content}
`.trim();
}

export function formatDocumentsForChat(documents: LegalDocument[]): string {
  if (documents.length === 0) {
    return '未找到相关法律文档。';
  }
  
  return documents.map((doc) => formatDocumentForChat(doc)).join('\n\n---\n\n');
}

export function createDocumentContextPrompt(query: string, documents: LegalDocument[]): string {
  const relevantDocs = extractRelevantContent(documents, query, 3);
  
  if (relevantDocs.length === 0) {
    return '';
  }
  
  let context = '【相关法律文档】\n\n';
  
  relevantDocs.forEach((result, index) => {
    context += `${index + 1}. ${result.document.name}\n`;
    context += `   ${result.snippet}\n\n`;
  });
  
  context += '请基于以上法律文档内容回答用户的问题。如果文档中没有相关信息，请明确说明。\n';
  
  return context;
}
