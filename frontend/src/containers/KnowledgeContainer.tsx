/**
 * Knowledge Hub container component
 * Manages document uploads and list
 * Fully responsive for all screen sizes
 */

import { Box, Typography, Alert, Snackbar, useMediaQuery, useTheme, alpha } from '@mui/material';
import { useState } from 'react';
import { DropZone } from '@/components/DropZone';
import { DocumentList } from '@/components/DocumentList';
import { useDocuments } from '@/hooks/useDocuments';
import { colors } from '@/theme';

export function KnowledgeContainer() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

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
        p: { xs: 1.5, sm: 2, md: 3 },
        bgcolor: colors.white,
        // Custom scrollbar
        '&::-webkit-scrollbar': {
          width: 8,
        },
        '&::-webkit-scrollbar-thumb': {
          bgcolor: alpha(colors.textNav, 0.2),
          borderRadius: 4,
        },
        '&::-webkit-scrollbar-track': {
          bgcolor: 'transparent',
        },
      }}
    >
      {/* Header */}
      <Box sx={{ mb: { xs: 2, sm: 3, md: 4 } }}>
        <Typography
          variant="h4"
          sx={{
            fontFamily: '"Asap", sans-serif',
            fontWeight: 700,
            fontStyle: 'italic',
            color: colors.dark,
            mb: { xs: 0.5, sm: 1 },
            fontSize: { xs: '1.25rem', sm: '1.5rem', md: '2rem' },
          }}
        >
          Base de Conocimiento
        </Typography>
        <Typography
          variant="body1"
          sx={{
            color: colors.textParagraph,
            fontSize: { xs: '0.8rem', sm: '0.9rem', md: '1rem' },
            lineHeight: 1.5,
          }}
        >
          Sube documentos para entrenar al agente con informacion de tu empresa.
        </Typography>
      </Box>

      {/* Upload Zone */}
      <Box sx={{ mb: { xs: 2, sm: 3, md: 4 } }}>
        <DropZone onUpload={handleUpload} isUploading={isUploading} />
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert
          severity="error"
          sx={{
            mb: { xs: 2, sm: 3 },
            fontSize: { xs: '0.8rem', sm: '0.875rem' },
          }}
        >
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
            mb: { xs: 1.5, sm: 2 },
            fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' },
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
        anchorOrigin={{
          vertical: isMobile ? 'top' : 'bottom',
          horizontal: isMobile ? 'center' : 'right',
        }}
        sx={{
          // Position above safe area on mobile
          bottom: isMobile ? undefined : 24,
          top: isMobile ? 70 : undefined,
        }}
      >
        <Alert
          severity={notification.severity}
          onClose={() => setNotification({ ...notification, open: false })}
          sx={{
            borderRadius: 2,
            fontSize: { xs: '0.8rem', sm: '0.875rem' },
            maxWidth: { xs: 'calc(100vw - 32px)', sm: 'auto' },
          }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
