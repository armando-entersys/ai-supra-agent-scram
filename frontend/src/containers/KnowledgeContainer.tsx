/**
 * Knowledge Hub container component
 * Manages document uploads and list
 */

import { Box, Typography, Alert, Snackbar } from '@mui/material';
import { useState } from 'react';
import { DropZone } from '@/components/DropZone';
import { DocumentList } from '@/components/DocumentList';
import { useDocuments } from '@/hooks/useDocuments';
import { colors } from '@/theme';

export function KnowledgeContainer() {
  const {
    documents,
    isLoading,
    error,
    uploadDocument,
    deleteDocument,
    reindexDocument,
    isUploading,
    refetch,
  } = useDocuments();

  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const handleUpload = async (file: File) => {
    try {
      await uploadDocument(file);
      setNotification({
        open: true,
        message: `"${file.name}" subido exitosamente`,
        severity: 'success',
      });
    } catch (err) {
      setNotification({
        open: true,
        message: err instanceof Error ? err.message : 'Error al subir archivo',
        severity: 'error',
      });
    }
  };

  const handleDelete = async (documentId: string) => {
    try {
      await deleteDocument(documentId);
      setNotification({
        open: true,
        message: 'Documento eliminado',
        severity: 'success',
      });
    } catch (err) {
      setNotification({
        open: true,
        message: err instanceof Error ? err.message : 'Error al eliminar',
        severity: 'error',
      });
    }
  };

  const handleReindex = async (documentId: string) => {
    try {
      await reindexDocument(documentId);
      setNotification({
        open: true,
        message: 'Re-indexacion iniciada',
        severity: 'success',
      });
    } catch (err) {
      setNotification({
        open: true,
        message: err instanceof Error ? err.message : 'Error al re-indexar',
        severity: 'error',
      });
    }
  };

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        p: 3,
        bgcolor: colors.white,
      }}
    >
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          sx={{
            fontFamily: '"Asap", sans-serif',
            fontWeight: 700,
            fontStyle: 'italic',
            color: colors.dark,
            mb: 1,
          }}
        >
          Base de Conocimiento
        </Typography>
        <Typography variant="body1" sx={{ color: colors.textParagraph }}>
          Sube documentos para entrenar al agente con informacion especifica de tu empresa.
        </Typography>
      </Box>

      {/* Upload Zone */}
      <Box sx={{ mb: 4 }}>
        <DropZone onUpload={handleUpload} isUploading={isUploading} />
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error.message}
        </Alert>
      )}

      {/* Documents Section */}
      <Box>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Asap", sans-serif',
            fontWeight: 600,
            color: colors.dark,
            mb: 2,
          }}
        >
          Documentos Indexados
        </Typography>
        <DocumentList
          documents={documents}
          isLoading={isLoading}
          onDelete={handleDelete}
          onReindex={handleReindex}
        />
      </Box>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={4000}
        onClose={() => setNotification({ ...notification, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          severity={notification.severity}
          onClose={() => setNotification({ ...notification, open: false })}
          sx={{ borderRadius: 2 }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
