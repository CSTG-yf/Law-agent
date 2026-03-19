export type { LegalDocument } from './store-legal-docs';
export {
  useLegalDocumentsStore,
  getFilteredDocuments,
  getDocumentCategories,
} from './store-legal-docs';

export { LegalDocumentUpload } from './LegalDocumentUpload';
export { LegalDocumentSearch } from './LegalDocumentSearch';
export { LegalDocumentsPanel } from './LegalDocumentsPanel';
export { LegalDocumentsDrawer } from './LegalDocumentsDrawer';
export { LegalDocumentsMobileDrawer } from './LegalDocumentsMobileDrawer';

export {
  searchLegalDocuments,
  extractRelevantContent,
  formatDocumentForChat,
  formatDocumentsForChat,
  createDocumentContextPrompt,
} from './legal-docs.utils';
