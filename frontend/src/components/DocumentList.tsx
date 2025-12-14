/**
 * Document list component for Knowledge Hub
 * Displays uploaded documents with status and actions
 * Responsive: Cards on mobile, Table on desktop
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

const getFileIcon = (mimeType: string, isMobile: boolean) => {
  const fontSize = isMobile ? 20 : 24;
  if (mimeType === 'application/pdf') {
    return <PdfIcon sx={{ color: colors.error, fontSize }} />;
  }
  if (mimeType.includes('word') || mimeType.includes('document')) {
    return <DocIcon sx={{ color: colors.info, fontSize }} />;
  }
  return <FileIcon sx={{ color: colors.textNav, fontSize }} />;
};

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (dateStr: string, short = false) => {
  const date = new Date(dateStr);
  if (short) {
    return date.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
    });
  }
  return date.toLocaleDateString('es-ES', {
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
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));

  // Loading skeleton
  if (isLoading) {
    if (isMobile) {
      return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {[1, 2, 3].map((i) => (
            <Card key={i} sx={{ borderRadius: 2 }}>
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Box sx={{ display: 'flex', gap: 1.5 }}>
                  <Skeleton variant="circular" width={36} height={36} />
                  <Box sx={{ flex: 1 }}>
                    <Skeleton variant="text" width="70%" height={20} />
                    <Skeleton variant="text" width="50%" height={16} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      );
    }
    return (
      <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
        <Table size={isTablet ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              <TableCell>Documento</TableCell>
              <TableCell>Estado</TableCell>
              {!isTablet && <TableCell>Chunks</TableCell>}
              <TableCell>Tamano</TableCell>
              {!isTablet && <TableCell>Fecha</TableCell>}
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {[1, 2, 3].map((i) => (
              <TableRow key={i}>
                <TableCell><Skeleton variant="text" width={150} /></TableCell>
                <TableCell><Skeleton variant="rounded" width={70} height={24} /></TableCell>
                {!isTablet && <TableCell><Skeleton variant="text" width={40} /></TableCell>}
                <TableCell><Skeleton variant="text" width={50} /></TableCell>
                {!isTablet && <TableCell><Skeleton variant="text" width={100} /></TableCell>}
                <TableCell><Skeleton variant="circular" width={28} height={28} /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }

  // Empty state
  if (documents.length === 0) {
    return (
      <Paper
        sx={{
          p: { xs: 3, sm: 4, md: 6 },
          textAlign: 'center',
          borderRadius: { xs: 2, sm: 2.5, md: 3 },
          bgcolor: colors.bgLight,
        }}
      >
        <FileIcon
          sx={{
            fontSize: { xs: 40, sm: 52, md: 64 },
            color: colors.border,
            mb: { xs: 1.5, sm: 2 },
          }}
        />
        <Typography
          variant="h6"
          sx={{
            color: colors.dark,
            mb: 0.5,
            fontSize: { xs: '0.95rem', sm: '1.1rem', md: '1.25rem' },
          }}
        >
          No hay documentos
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: colors.textParagraph,
            fontSize: { xs: '0.75rem', sm: '0.8rem', md: '0.875rem' },
          }}
        >
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
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
                transition: 'box-shadow 0.2s',
                '&:active': {
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                },
              }}
            >
              <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: 1.5,
                      bgcolor: colors.bgLight,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {getFileIcon(doc.mime_type, true)}
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      sx={{
                        fontWeight: 500,
                        color: colors.dark,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontSize: '0.875rem',
                        mb: 0.5,
                      }}
                    >
                      {doc.original_name}
                    </Typography>
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        flexWrap: 'wrap',
                      }}
                    >
                      <Chip
                        label={statusInfo.label}
                        size="small"
                        sx={{
                          bgcolor: statusInfo.bg,
                          color: statusInfo.color,
                          fontWeight: 500,
                          fontSize: '0.65rem',
                          height: 20,
                          '& .MuiChip-label': { px: 1 },
                        }}
                      />
                      <Typography
                        variant="caption"
                        sx={{ color: colors.textNav, fontSize: '0.7rem' }}
                      >
                        {formatFileSize(doc.file_size)} · {doc.chunk_count} chunks
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }}>
                    <IconButton
                      size="small"
                      onClick={() => onReindex(doc.id)}
                      disabled={doc.status === 'processing'}
                      sx={{
                        color: colors.primary,
                        p: 0.75,
                        '&:disabled': { color: colors.border },
                      }}
                    >
                      <RefreshIcon sx={{ fontSize: 18 }} />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => onDelete(doc.id)}
                      sx={{ color: colors.error, p: 0.75 }}
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

  // Desktop/Tablet table view
  return (
    <TableContainer
      component={Paper}
      sx={{
        borderRadius: { sm: 2, md: 3 },
        overflow: 'hidden',
      }}
    >
      <Table size={isTablet ? 'small' : 'medium'}>
        <TableHead>
          <TableRow sx={{ bgcolor: colors.bgLightAlt }}>
            <TableCell
              sx={{
                fontWeight: 600,
                color: colors.dark,
                fontSize: isTablet ? '0.8rem' : '0.875rem',
              }}
            >
              Documento
            </TableCell>
            <TableCell
              sx={{
                fontWeight: 600,
                color: colors.dark,
                fontSize: isTablet ? '0.8rem' : '0.875rem',
              }}
            >
              Estado
            </TableCell>
            {!isTablet && (
              <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Chunks</TableCell>
            )}
            <TableCell
              sx={{
                fontWeight: 600,
                color: colors.dark,
                fontSize: isTablet ? '0.8rem' : '0.875rem',
              }}
            >
              Tamano
            </TableCell>
            {!isTablet && (
              <TableCell sx={{ fontWeight: 600, color: colors.dark }}>Fecha</TableCell>
            )}
            <TableCell
              align="right"
              sx={{
                fontWeight: 600,
                color: colors.dark,
                fontSize: isTablet ? '0.8rem' : '0.875rem',
              }}
            >
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
                  transition: 'background-color 0.15s',
                }}
              >
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    {getFileIcon(doc.mime_type, isTablet)}
                    <Box sx={{ minWidth: 0 }}>
                      <Typography
                        sx={{
                          fontWeight: 500,
                          color: colors.dark,
                          fontSize: isTablet ? '0.8rem' : '0.875rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: isTablet ? 150 : 250,
                        }}
                      >
                        {doc.original_name}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: colors.textNav,
                          fontSize: isTablet ? '0.65rem' : '0.7rem',
                        }}
                      >
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
                      fontSize: isTablet ? '0.65rem' : '0.7rem',
                      height: isTablet ? 22 : 24,
                    }}
                  />
                </TableCell>
                {!isTablet && (
                  <TableCell>
                    <Typography variant="body2" sx={{ color: colors.textParagraph }}>
                      {doc.chunk_count}
                    </Typography>
                  </TableCell>
                )}
                <TableCell>
                  <Typography
                    variant="body2"
                    sx={{
                      color: colors.textParagraph,
                      fontSize: isTablet ? '0.75rem' : '0.875rem',
                    }}
                  >
                    {formatFileSize(doc.file_size)}
                  </Typography>
                </TableCell>
                {!isTablet && (
                  <TableCell>
                    <Typography variant="body2" sx={{ color: colors.textParagraph }}>
                      {formatDate(doc.created_at)}
                    </Typography>
                  </TableCell>
                )}
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
                          '&:disabled': {
                            color: colors.border,
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
