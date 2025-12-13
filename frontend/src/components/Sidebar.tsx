/**
 * Navigation sidebar component
 * SCRAM styled with session list and navigation
 */

import { memo } from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Typography,
  Divider,
  Tooltip,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Chat as ChatIcon,
  Folder as FolderIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Menu as MenuIcon,
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
}

const DRAWER_WIDTH = 280;

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
}: SidebarProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Hoy';
    if (diffDays === 1) return 'Ayer';
    if (diffDays < 7) return `Hace ${diffDays} dias`;
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  };

  const drawerContent = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: colors.white,
      }}
    >
      {/* Logo / Brand */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
        }}
      >
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryHover} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 4px 12px ${colors.primary}40`,
          }}
        >
          <Typography
            sx={{
              color: colors.white,
              fontWeight: 700,
              fontFamily: '"Asap", sans-serif',
              fontStyle: 'italic',
              fontSize: '1.2rem',
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
          }}
        >
          AI-SupraAgent
        </Typography>
      </Box>

      <Divider />

      {/* Navigation */}
      <List sx={{ px: 1, py: 1 }}>
        <ListItem disablePadding>
          <ListItemButton
            selected={currentView === 'chat'}
            onClick={() => onViewChange('chat')}
            sx={{
              borderRadius: 2,
              mb: 0.5,
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
              primary="Base de Conocimiento"
              primaryTypographyProps={{
                fontWeight: currentView === 'knowledge' ? 600 : 400,
                color: currentView === 'knowledge' ? colors.dark : colors.textParagraph,
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
            }}
          >
            <Typography variant="caption" sx={{ fontWeight: 600, color: colors.textNav }}>
              CONVERSACIONES
            </Typography>
            <Tooltip title="Nueva conversacion">
              <IconButton
                size="small"
                onClick={onNewChat}
                sx={{
                  bgcolor: `${colors.primary}15`,
                  '&:hover': {
                    bgcolor: `${colors.primary}25`,
                  },
                }}
              >
                <AddIcon sx={{ fontSize: 18, color: colors.primary }} />
              </IconButton>
            </Tooltip>
          </Box>

          <List sx={{ flex: 1, overflow: 'auto', px: 1 }}>
            {sessions.length === 0 ? (
              <Typography
                variant="body2"
                sx={{ px: 2, py: 4, textAlign: 'center', color: colors.textNav }}
              >
                No hay conversaciones
              </Typography>
            ) : (
              sessions.map((session) => (
                <ListItem
                  key={session.id}
                  disablePadding
                  secondaryAction={
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSessionDelete(session.id);
                      }}
                      sx={{
                        opacity: 0,
                        transition: 'opacity 0.2s',
                        '.MuiListItem-root:hover &': {
                          opacity: 1,
                        },
                      }}
                    >
                      <DeleteIcon sx={{ fontSize: 16, color: colors.error }} />
                    </IconButton>
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
                      '&.Mui-selected': {
                        bgcolor: `${colors.primary}10`,
                      },
                    }}
                  >
                    <ListItemText
                      primary={session.title || 'Nueva conversacion'}
                      secondary={formatDate(session.updated_at)}
                      primaryTypographyProps={{
                        noWrap: true,
                        fontSize: '0.875rem',
                        fontWeight: session.id === currentSessionId ? 600 : 400,
                      }}
                      secondaryTypographyProps={{
                        fontSize: '0.75rem',
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

  return (
    <Drawer
      variant={isMobile ? 'temporary' : 'persistent'}
      open={open}
      onClose={onClose}
      sx={{
        width: open ? DRAWER_WIDTH : 0,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          borderRight: 'none',
          boxShadow: '4px 0 20px rgba(0, 0, 0, 0.05)',
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
});
