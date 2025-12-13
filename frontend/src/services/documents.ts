/**
 * Documents API service
 */

import { apiClient } from './api';
import type {
  Document,
  DocumentListResponse,
  DocumentUploadResponse,
  DocumentStatus,
  SearchResponse,
} from '@/types';

export const documentsService = {
  /**
   * Upload a document
   */
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    return apiClient.upload<DocumentUploadResponse>('/api/v1/documents/upload', file);
  },

  /**
   * List documents with pagination
   */
  list: async (
    page = 1,
    pageSize = 20,
    status?: DocumentStatus
  ): Promise<DocumentListResponse> => {
    return apiClient.get<DocumentListResponse>('/api/v1/documents', {
      page,
      page_size: pageSize,
      status,
    });
  },

  /**
   * Get a specific document
   */
  get: async (documentId: string): Promise<Document> => {
    return apiClient.get<Document>(`/api/v1/documents/${documentId}`);
  },

  /**
   * Delete a document
   */
  delete: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/documents/${documentId}`);
  },

  /**
   * Reindex a document
   */
  reindex: async (documentId: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>(
      `/api/v1/documents/${documentId}/reindex`
    );
  },

  /**
   * Search documents
   */
  search: async (
    query: string,
    topK = 5,
    threshold = 0.7
  ): Promise<SearchResponse> => {
    return apiClient.post<SearchResponse>('/api/v1/documents/search', {
      query,
      top_k: topK,
      threshold,
    });
  },
};
