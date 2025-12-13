/**
 * Custom hook for document management
 */

import { useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { documentsService } from '@/services/documents';
import type { Document, DocumentStatus, SearchResponse } from '@/types';

interface UseDocumentsOptions {
  page?: number;
  pageSize?: number;
  status?: DocumentStatus;
}

interface UseDocumentsReturn {
  documents: Document[];
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: Error | null;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (documentId: string) => Promise<void>;
  reindexDocument: (documentId: string) => Promise<void>;
  searchDocuments: (query: string) => Promise<SearchResponse>;
  refetch: () => void;
  isUploading: boolean;
}

export function useDocuments(options: UseDocumentsOptions = {}): UseDocumentsReturn {
  const { page = 1, pageSize = 20, status } = options;
  const queryClient = useQueryClient();

  // Fetch documents
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['documents', page, pageSize, status],
    queryFn: () => documentsService.list(page, pageSize, status),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsService.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => documentsService.delete(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  // Reindex mutation
  const reindexMutation = useMutation({
    mutationFn: (documentId: string) => documentsService.reindex(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const uploadDocument = useCallback(
    async (file: File) => {
      await uploadMutation.mutateAsync(file);
    },
    [uploadMutation]
  );

  const deleteDocument = useCallback(
    async (documentId: string) => {
      await deleteMutation.mutateAsync(documentId);
    },
    [deleteMutation]
  );

  const reindexDocument = useCallback(
    async (documentId: string) => {
      await reindexMutation.mutateAsync(documentId);
    },
    [reindexMutation]
  );

  const searchDocuments = useCallback(
    async (query: string) => {
      return documentsService.search(query);
    },
    []
  );

  return {
    documents: data?.documents ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? page,
    pageSize: data?.page_size ?? pageSize,
    isLoading,
    error: error as Error | null,
    uploadDocument,
    deleteDocument,
    reindexDocument,
    searchDocuments,
    refetch,
    isUploading: uploadMutation.isPending,
  };
}
