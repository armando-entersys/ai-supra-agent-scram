/**
 * Document list component for Knowledge Hub
 * Displays uploaded documents with status and actions
 */

import { memo } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Typography,
  Tooltip,
  Skeleton,
  Card,
  CardContent,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Description as FileIcon,
  PictureAsPdf as PdfIcon,
  Article as DocIcon,
} from '@mui/icons-material';
import { colors } from '@/theme';
import type { Document, DocumentStatus } from '@/types';

interface DocumentListProps {
  documents: Document[];
  isLoading?: boolean;
  onDelete: (documentId: string) => void;
  onReindex: (documentId: string) => void;
}

const getStatusColor = (status: DocumentStatus) => {
  switch (status) {
    case 'indexed':
      return { bg: `${colors.success}15`, color: colors.greenDark, label: 'Indexado' };
    case 'processing':
      return { bg: `${colors.primary}15`, color: colors.primaryDark, label: 'Procesando' };
    case 'pending':
      return { bg: `${colors.info}15`, color: colors.info, label: 'Pendiente' };
    case 'error':
      return { bg: `${colors.error}15`, color: colors.error, label: 'Error' };
    default:
      return { bg: colors.bgLight, color: colors.textNav, label: status };
  }
};

const getFileIcon = (mimeType: string) => {
  if (mimeType === 'application/pdf') {
    return <PdfIcon sx={{ color: colors.error }} />;
  }
  if (mimeType.includes('word') || mimeType.includes('document')) {
    return <DocIcon sx={{ color: colors.info }} />;
  }
  return <FileIcon sx={{ color: colors.textNav }} />;
};

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const DocumentList = memo(function DocumentList({
  documents,
  isLoading = false,
  onDelete,
  onReindex,
}: DocumentListProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  if (isLoading) {
    if (isMobile) {
      return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {[1, 2, 3].map((i) => (
            <Card key={i} sx={{ borderRadius: 2 }}>
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Skeleton variant="text" width="70%" />
                <Skeleton variant="text" width="40%" />
              </CardContent>
            </Card>
          ))}
        </Box>
      );
    }
    return (
      <TableContainer component={Paper} sx={{ borderRadius: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Documento</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Chunks</TableCell>
              <TableCell>Tamano</TableCell>
              <TableCell>Fecha</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {[1, 2, 3].map((i) => (
              <TableRow key={i}>
                <TableCell>
                  <Skeleton variant="text" width={200} />
                </TableCell>
                <TableCell>
                  <Skeleton variant="rounded" width={80} height={24} />
                </TableCell>
                <TableCell>
                  <Skeleton variant="text" width={40} />
                </TableCell>
                <TableCell>
                  <Skeleton variant="text" width={60} />
                </TableCell>
                <TableCell>
                  <Skeleton variant="text" width={120} />
                </TableCell>
                <TableCell>
                  <Skeleton variant="circular" width={32} height={32} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }

  if (documents.length === 0) {
    return (
      <Paper
        sx={{
          p: { xs: 4, sm: 6 },
          textAlign: 'center',
          borderRadius: { xs: 2, sm: 3 },
          bgcolor: colors.bgLight,
        }}
      >
        <FileIcon sx={{ fontSize: { xs: 48, sm: 64 }, color: colors.border, mb: 2 }} />
        <Typography variant="h6" sx={{ color: colors.dark, mb: 1, fontSize: { xs: '1rem', sm: '1.25rem' } }}>
          No hay documentos
        </Typography>
        <Typography variant="body2" sx={{ color: colors.textParagraph, fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
          Sube documentos para entrenar la base de conocimiento
        </Typography>
      </Paper>
    );
  }

  // Mobile card view
  if (isMobile) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {documents.map((doc) => {
          const statusInfo = getStatusColor(doc.status);
          return (
            <Card
              key={doc.id}
              sx={{
                borderRadius: 2,
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
              }}
            >
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                  {getFileIcon(doc.mime_type)}
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 500,
                        color: colors.dark,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {doc.original_name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
                      <Chip
                        label={statusInfo.label}
                        size="small"
                        sx={{
                          bgcolor: statusInfo.bg,
                          color: statusInfo.color,
                          fontWeight: 500,
                          fontSize: '0.7rem',
                          height: 22,
                        }}
                      />
                      <Typography variant="caption" sx={{ color: colors.textNav }}>
                        {formatFileSize(doc.file_size)} • {doc.chunk_count} chunks
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <IconButton
                      size="small"
                      onClick={() => onReindex(doc.id)}
                      disabled={doc.status === 'processing'}
                      sx={{ color: colors.primary }}
                    >
                      <RefreshIcon sx={{ fontSize: 18 }} />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => onDelete(doc.id)}
                      sx={{ color: colors.error }}
                    >
                      <DeleteIcon sx={{ fontSize: 18 }} />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>
    );
  }

  // Desktop table view
  return (
    <TableContainer component={Paper} sx={{ borderRadius: 3 }}>
      <Table>
        <TableHead>
          <TableRow sx={{ bgcolor: colors.bgLightAlt }}>
            <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Documento</TableCell>
            <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Estado</TableCell>
            <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Chunks</TableCell>
            <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Tamano</TableCell>
            <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Fecha</TableCell>
            <TableCell align="right" sx={{ fontWeight: 600, color: colors.dark }}>
              Acciones
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {documents.map((doc) => {
            const statusInfo = getStatusColor(doc.status);

            return (
              <TableRow
                key={doc.id}
                sx={{
                  '&:hover': {
                    bgcolor: colors.bgLight,
                  },
                  transition: 'background-color 0.2s',
                }}
              >
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    {getFileIcon(doc.mime_type)}
                    <Box>
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 500, color: colors.dark }}
                      >
                        {doc.original_name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: colors.textNav }}>
                        {doc.mime_type.split('/')[1]?.toUpperCase()}
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={statusInfo.label}
                    size="small"
                    sx={{
                      bgcolor: statusInfo.bg,
                      color: statusInfo.color,
                      fontWeight: 500,
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ color: colors.textParagraph }}>
                    {doc.chunk_count}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ color: colors.textParagraph }}>
                    {formatFileSize(doc.file_size)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ color: colors.textParagraph }}>
                    {formatDate(doc.created_at)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
                    <Tooltip title="Re-indexar">
                      <IconButton
                        size="small"
                        onClick={() => onReindex(doc.id)}
                        disabled={doc.status === 'processing'}
                        sx={{
                          color: colors.primary,
                          '&:hover': {
                            bgcolor: `${colors.primary}15`,
                          },
                        }}
                      >
                        <RefreshIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Eliminar">
                      <IconButton
                        size="small"
                        onClick={() => onDelete(doc.id)}
                        sx={{
                          color: colors.error,
                          '&:hover': {
                            bgcolor: `${colors.error}15`,
                          },
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
});
