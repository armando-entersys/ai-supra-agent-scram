/**
 * Drag & Drop file upload component
 * SCRAM styled with dashed border and animations
 */

import { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import {
  Box,
  Typography,
  LinearProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as FileIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { colors } from '@/theme';

interface DropZoneProps {
  onUpload: (file: File) => Promise<void>;
  isUploading?: boolean;
  accept?: Record<string, string[]>;
  maxSize?: number;
}

const DEFAULT_ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
  'text/markdown': ['.md'],
};

const DEFAULT_MAX_SIZE = 25 * 1024 * 1024; // 25MB

export function DropZone({
  onUpload,
  isUploading = false,
  accept = DEFAULT_ACCEPT,
  maxSize = DEFAULT_MAX_SIZE,
}: DropZoneProps) {
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      setError(null);
      setUploadedFile(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection?.errors[0]?.code === 'file-too-large') {
          setError(`Archivo muy grande. Maximo: ${maxSize / (1024 * 1024)}MB`);
        } else if (rejection?.errors[0]?.code === 'file-invalid-type') {
          setError('Tipo de archivo no permitido. Usa PDF, DOCX, TXT o MD.');
        } else {
          setError('Error al procesar el archivo');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        if (file) {
          try {
            await onUpload(file);
            setUploadedFile(file.name);
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al subir archivo');
          }
        }
      }
    },
    [onUpload, maxSize]
  );

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept,
    maxSize,
    multiple: false,
    disabled: isUploading,
  });

  const getBorderColor = () => {
    if (isDragReject) return colors.error;
    if (isDragAccept) return colors.success;
    if (isDragActive) return colors.primary;
    return colors.border;
  };

  const getBackgroundColor = () => {
    if (isDragReject) return `${colors.error}08`;
    if (isDragAccept) return `${colors.success}08`;
    if (isDragActive) return `${colors.primary}08`;
    return colors.bgLight;
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box
        {...getRootProps()}
        sx={{
          border: `2px dashed ${getBorderColor()}`,
          borderRadius: { xs: 2, sm: 3 },
          p: { xs: 2, sm: 4 },
          textAlign: 'center',
          bgcolor: getBackgroundColor(),
          cursor: isUploading ? 'not-allowed' : 'pointer',
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: isUploading ? colors.border : colors.primary,
            bgcolor: isUploading ? colors.bgLight : `${colors.primary}05`,
          },
        }}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <Box>
            <UploadIcon
              sx={{
                fontSize: { xs: 36, sm: 48 },
                color: colors.primary,
                mb: { xs: 1, sm: 2 },
                animation: 'pulse 1.5s infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1 },
                  '50%': { opacity: 0.5 },
                },
              }}
            />
            <Typography variant="body1" sx={{ mb: 2, color: colors.dark, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
              Subiendo documento...
            </Typography>
            <LinearProgress sx={{ maxWidth: 300, mx: 'auto' }} />
          </Box>
        ) : uploadedFile ? (
          <Box>
            <SuccessIcon sx={{ fontSize: { xs: 36, sm: 48 }, color: colors.success, mb: { xs: 1, sm: 2 } }} />
            <Typography variant="body1" sx={{ color: colors.dark, mb: 1, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
              Documento subido exitosamente
            </Typography>
            <Chip
              icon={<FileIcon />}
              label={uploadedFile}
              size="small"
              sx={{
                bgcolor: `${colors.success}15`,
                color: colors.greenDark,
                fontWeight: 500,
                maxWidth: '100%',
                '& .MuiChip-label': {
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                },
              }}
            />
          </Box>
        ) : (
          <Box>
            <UploadIcon
              sx={{
                fontSize: { xs: 36, sm: 48 },
                color: isDragActive ? colors.primary : colors.textNav,
                mb: { xs: 1, sm: 2 },
                transition: 'all 0.3s ease',
              }}
            />
            <Typography
              variant="body1"
              sx={{
                color: isDragActive ? colors.primary : colors.dark,
                fontWeight: 500,
                mb: 1,
                fontSize: { xs: '0.875rem', sm: '1rem' },
              }}
            >
              {isDragActive
                ? 'Suelta el archivo aqui'
                : 'Arrastra un documento o haz clic para seleccionar'}
            </Typography>
            <Typography variant="body2" sx={{ color: colors.textParagraph, fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
              PDF, DOCX, TXT, MD (max. {maxSize / (1024 * 1024)}MB)
            </Typography>
          </Box>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Box>
  );
}
