/**
 * Navigation sidebar component
 * SCRAM styled with session list and navigation
 * Fully responsive for mobile, tablet, and desktop
 */

import { memo } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Typography,
  Divider,
  Tooltip,
  alpha,
} from '@mui/material';
import {
  Chat as ChatIcon,
  Folder as FolderIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { colors } from '@/theme';
import type { ChatSession, ViewType } from '@/types';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionDelete: (sessionId: string) => void;
  onNewChat: () => void;
  isMobile?: boolean;
}

export const Sidebar = memo(function Sidebar({
  open,
  onClose,
  currentView,
  onViewChange,
  sessions,
  currentSessionId,
  onSessionSelect,
  onSessionDelete,
  onNewChat,
  isMobile = false,
}: SidebarProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Hoy';
    if (diffDays === 1) return 'Ayer';
    if (diffDays < 7) return `Hace ${diffDays} dias`;
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: colors.white,
        overflow: 'hidden',
      }}
    >
      {/* Logo / Brand */}
      <Box
        sx={{
          p: isMobile ? 2 : 2.5,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          flexShrink: 0,
        }}
      >
        <Box
          sx={{
            width: isMobile ? 36 : 40,
            height: isMobile ? 36 : 40,
            borderRadius: 2,
            background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryHover} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 4px 12px ${colors.primary}40`,
            flexShrink: 0,
          }}
        >
          <Typography
            sx={{
              color: colors.white,
              fontWeight: 700,
              fontFamily: '"Asap", sans-serif',
              fontStyle: 'italic',
              fontSize: isMobile ? '1rem' : '1.2rem',
            }}
          >
            S
          </Typography>
        </Box>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Asap", sans-serif',
            fontWeight: 700,
            fontStyle: 'italic',
            color: colors.dark,
            fontSize: isMobile ? '1rem' : '1.125rem',
            whiteSpace: 'nowrap',
          }}
        >
          AI-SupraAgent
        </Typography>
      </Box>

      <Divider />

      {/* Navigation */}
      <List sx={{ px: 1, py: 1, flexShrink: 0 }}>
        <ListItem disablePadding>
          <ListItemButton
            selected={currentView === 'chat'}
            onClick={() => onViewChange('chat')}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              py: isMobile ? 1.25 : 1,
              '&.Mui-selected': {
                bgcolor: `${colors.primary}15`,
                '&:hover': {
                  bgcolor: `${colors.primary}20`,
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              <ChatIcon sx={{ color: currentView === 'chat' ? colors.primary : colors.textNav }} />
            </ListItemIcon>
            <ListItemText
              primary="Chat"
              primaryTypographyProps={{
                fontWeight: currentView === 'chat' ? 600 : 400,
                color: currentView === 'chat' ? colors.dark : colors.textParagraph,
                fontSize: isMobile ? '0.95rem' : '1rem',
              }}
            />
          </ListItemButton>
        </ListItem>

        <ListItem disablePadding>
          <ListItemButton
            selected={currentView === 'knowledge'}
            onClick={() => onViewChange('knowledge')}
            sx={{
              borderRadius: 2,
              py: isMobile ? 1.25 : 1,
              '&.Mui-selected': {
                bgcolor: `${colors.primary}15`,
                '&:hover': {
                  bgcolor: `${colors.primary}20`,
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              <FolderIcon
                sx={{ color: currentView === 'knowledge' ? colors.primary : colors.textNav }}
              />
            </ListItemIcon>
            <ListItemText
              primary="Conocimiento"
              primaryTypographyProps={{
                fontWeight: currentView === 'knowledge' ? 600 : 400,
                color: currentView === 'knowledge' ? colors.dark : colors.textParagraph,
                fontSize: isMobile ? '0.95rem' : '1rem',
              }}
            />
          </ListItemButton>
        </ListItem>
      </List>

      <Divider />

      {/* Chat Sessions */}
      {currentView === 'chat' && (
        <>
          <Box
            sx={{
              px: 2,
              py: 1.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontWeight: 600,
                color: colors.textNav,
                fontSize: isMobile ? '0.7rem' : '0.75rem',
                letterSpacing: '0.5px',
              }}
            >
              CONVERSACIONES
            </Typography>
            <Tooltip title="Nueva conversacion">
              <IconButton
                size="small"
                onClick={onNewChat}
                sx={{
                  bgcolor: `${colors.primary}15`,
                  width: isMobile ? 32 : 28,
                  height: isMobile ? 32 : 28,
                  '&:hover': {
                    bgcolor: `${colors.primary}25`,
                  },
                }}
              >
                <AddIcon sx={{ fontSize: isMobile ? 20 : 18, color: colors.primary }} />
              </IconButton>
            </Tooltip>
          </Box>

          <List
            sx={{
              flex: 1,
              overflow: 'auto',
              px: 1,
              // Custom scrollbar
              '&::-webkit-scrollbar': {
                width: 6,
              },
              '&::-webkit-scrollbar-thumb': {
                bgcolor: alpha(colors.textNav, 0.3),
                borderRadius: 3,
              },
              '&::-webkit-scrollbar-track': {
                bgcolor: 'transparent',
              },
            }}
          >
            {sessions.length === 0 ? (
              <Box sx={{ py: 4, textAlign: 'center' }}>
                <Typography
                  variant="body2"
                  sx={{ color: colors.textNav, fontSize: isMobile ? '0.85rem' : '0.875rem' }}
                >
                  No hay conversaciones
                </Typography>
              </Box>
            ) : (
              sessions.map((session) => (
                <ListItem
                  key={session.id}
                  disablePadding
                  secondaryAction={
                    <Tooltip title="Eliminar conversación">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm('¿Eliminar esta conversación?')) {
                            onSessionDelete(session.id);
                          }
                        }}
                        sx={{
                          opacity: isMobile ? 0.8 : 0,
                          transition: 'all 0.2s',
                          p: isMobile ? 1 : 0.5,
                          '.MuiListItem-root:hover &': {
                            opacity: 1,
                          },
                          '&:hover': {
                            bgcolor: `${colors.error}15`,
                          },
                        }}
                      >
                        <DeleteIcon sx={{ fontSize: isMobile ? 18 : 16, color: colors.error }} />
                      </IconButton>
                    </Tooltip>
                  }
                  sx={{
                    mb: 0.5,
                    '& .MuiListItemSecondaryAction-root': {
                      right: 8,
                    },
                  }}
                >
                  <ListItemButton
                    selected={session.id === currentSessionId}
                    onClick={() => onSessionSelect(session.id)}
                    sx={{
                      borderRadius: 2,
                      pr: 5,
                      py: isMobile ? 1.25 : 1,
                      '&.Mui-selected': {
                        bgcolor: `${colors.primary}10`,
                        '&:hover': {
                          bgcolor: `${colors.primary}15`,
                        },
                      },
                    }}
                  >
                    <ListItemText
                      primary={session.title || 'Nueva conversacion'}
                      secondary={formatDate(session.updated_at)}
                      primaryTypographyProps={{
                        noWrap: true,
                        fontSize: isMobile ? '0.9rem' : '0.875rem',
                        fontWeight: session.id === currentSessionId ? 600 : 400,
                      }}
                      secondaryTypographyProps={{
                        fontSize: isMobile ? '0.75rem' : '0.7rem',
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              ))
            )}
          </List>
        </>
      )}
    </Box>
  );
});
