import * as React from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface LegalDocument {
  id: string;
  name: string;
  type: string;
  size: number;
  content: string;
  uploadedAt: number;
  category?: string;
  tags?: string[];
  summary?: string;
}

interface LegalDocumentsState {
  documents: LegalDocument[];
  selectedDocumentId: string | null;
  isPanelOpen: boolean;
  searchQuery: string;
  selectedCategory: string | null;

  addDocument: (document: LegalDocument) => void;
  removeDocument: (id: string) => void;
  updateDocument: (id: string, updates: Partial<LegalDocument>) => void;
  selectDocument: (id: string | null) => void;
  togglePanel: () => void;
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: string | null) => void;
  clearAllDocuments: () => void;
}

const initialState = {
  documents: [],
  selectedDocumentId: null,
  isPanelOpen: false,
  searchQuery: '',
  selectedCategory: null,
};

export const useLegalDocumentsStore = create<LegalDocumentsState>()(
  persist(
    (set, get) => ({
      ...initialState,

      addDocument: (document) => {
        set((state) => ({
          documents: [...state.documents, document],
        }));
      },

      removeDocument: (id) => {
        set((state) => ({
          documents: state.documents.filter((doc) => doc.id !== id),
          selectedDocumentId: state.selectedDocumentId === id ? null : state.selectedDocumentId,
        }));
      },

      updateDocument: (id, updates) => {
        set((state) => ({
          documents: state.documents.map((doc) =>
            doc.id === id ? { ...doc, ...updates } : doc
          ),
        }));
      },

      selectDocument: (id) => {
        set({ selectedDocumentId: id });
      },

      togglePanel: () => {
        set((state) => ({ isPanelOpen: !state.isPanelOpen }));
      },

      setSearchQuery: (query) => {
        set({ searchQuery: query });
      },

      setSelectedCategory: (category) => {
        set({ selectedCategory: category });
      },

      clearAllDocuments: () => {
        set({
          documents: [],
          selectedDocumentId: null,
          searchQuery: '',
          selectedCategory: null,
        });
      },
    }),
    {
      name: 'legal-documents-storage',
      partialize: (state) => ({
        documents: state.documents,
        selectedDocumentId: state.selectedDocumentId,
        isPanelOpen: state.isPanelOpen,
      }),
    }
  )
);

export const getFilteredDocuments = (state: LegalDocumentsState): LegalDocument[] => {
  let filtered = state.documents;

  if (state.searchQuery) {
    const query = state.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (doc) =>
        doc.name.toLowerCase().includes(query) ||
        doc.content.toLowerCase().includes(query) ||
        doc.tags?.some((tag) => tag.toLowerCase().includes(query))
    );
  }

  if (state.selectedCategory) {
    filtered = filtered.filter((doc) => doc.category === state.selectedCategory);
  }

  return filtered;
};

export const getDocumentCategories = (documents: LegalDocument[]): string[] => {
  const categories = new Set(documents.map((doc) => doc.category).filter(Boolean) as string[]);
  return Array.from(categories);
};
