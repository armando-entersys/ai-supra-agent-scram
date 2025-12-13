/**
 * Main App component
 * Integrates sidebar navigation with chat and knowledge views
 */

import { useState, useCallback } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Menu as MenuIcon } from '@mui/icons-material';
import { Sidebar } from '@/components/Sidebar';
import { ChatContainer } from '@/containers/ChatContainer';
import { KnowledgeContainer } from '@/containers/KnowledgeContainer';
import { useChat } from '@/hooks/useChat';
import { colors } from '@/theme';
import type { ViewType } from '@/types';

const DRAWER_WIDTH = 280;

function App() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [currentView, setCurrentView] = useState<ViewType>('chat');

  const {
    sessions,
    currentSession,
    selectSession,
    deleteSession,
    createSession,
    clearMessages,
  } = useChat();

  const handleSidebarToggle = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const handleViewChange = useCallback((view: ViewType) => {
    setCurrentView(view);
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  const handleNewChat = useCallback(async () => {
    clearMessages();
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [clearMessages, isMobile]);

  const handleSessionSelect = useCallback(
    (sessionId: string) => {
      selectSession(sessionId);
      if (isMobile) {
        setSidebarOpen(false);
      }
    },
    [selectSession, isMobile]
  );

  const handleSessionDelete = useCallback(
    async (sessionId: string) => {
      await deleteSession(sessionId);
    },
    [deleteSession]
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: colors.bgLight }}>
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentView={currentView}
        onViewChange={handleViewChange}
        sessions={sessions}
        currentSessionId={currentSession?.id ?? null}
        onSessionSelect={handleSessionSelect}
        onSessionDelete={handleSessionDelete}
        onNewChat={handleNewChat}
      />

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          overflow: 'hidden',
          transition: theme.transitions.create(['margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          ml: sidebarOpen && !isMobile ? 0 : `-${DRAWER_WIDTH}px`,
          ...(sidebarOpen && !isMobile && {
            ml: 0,
            transition: theme.transitions.create(['margin'], {
              easing: theme.transitions.easing.easeOut,
              duration: theme.transitions.duration.enteringScreen,
            }),
          }),
        }}
      >
        {/* App Bar */}
        <AppBar
          position="static"
          elevation={0}
          sx={{
            bgcolor: colors.white,
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <Toolbar>
            <IconButton
              edge="start"
              onClick={handleSidebarToggle}
              sx={{
                mr: 2,
                color: colors.dark,
                '&:hover': {
                  bgcolor: `${colors.primary}10`,
                },
              }}
            >
              <MenuIcon />
            </IconButton>
            <Typography
              variant="h6"
              sx={{
                fontFamily: '"Asap", sans-serif',
                fontWeight: 600,
                color: colors.dark,
              }}
            >
              {currentView === 'chat'
                ? currentSession?.title || 'Nueva Conversacion'
                : 'Base de Conocimiento'}
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Content Area */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          {currentView === 'chat' ? (
            <ChatContainer sessionId={currentSession?.id} />
          ) : (
            <KnowledgeContainer />
          )}
        </Box>
      </Box>
    </Box>
  );
}

export default App;
