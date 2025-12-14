/**
 * Main App component
 * Integrates sidebar navigation with chat and knowledge views
 * Full responsive design for mobile, tablet, and desktop
 */

import { useState, useCallback, useEffect } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  useMediaQuery,
  useTheme,
  SwipeableDrawer,
} from '@mui/material';
import { Menu as MenuIcon, Close as CloseIcon } from '@mui/icons-material';
import { Sidebar } from '@/components/Sidebar';
import { ChatContainer } from '@/containers/ChatContainer';
import { KnowledgeContainer } from '@/containers/KnowledgeContainer';
import { useChat } from '@/hooks/useChat';
import { colors } from '@/theme';
import type { ViewType } from '@/types';

const DRAWER_WIDTH_DESKTOP = 280;
const DRAWER_WIDTH_MOBILE = 300;

function App() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'));

  const [sidebarOpen, setSidebarOpen] = useState(isDesktop);
  const [currentView, setCurrentView] = useState<ViewType>('chat');

  const {
    sessions,
    currentSession,
    selectSession,
    deleteSession,
    createSession,
    clearMessages,
  } = useChat();

  // Close sidebar on mobile when screen size changes
  useEffect(() => {
    if (isMobile || isTablet) {
      setSidebarOpen(false);
    } else {
      setSidebarOpen(true);
    }
  }, [isMobile, isTablet]);

  const handleSidebarToggle = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const handleSidebarClose = useCallback(() => {
    if (isMobile || isTablet) {
      setSidebarOpen(false);
    }
  }, [isMobile, isTablet]);

  const handleViewChange = useCallback((view: ViewType) => {
    setCurrentView(view);
    handleSidebarClose();
  }, [handleSidebarClose]);

  const handleNewChat = useCallback(async () => {
    clearMessages();
    handleSidebarClose();
  }, [clearMessages, handleSidebarClose]);

  const handleSessionSelect = useCallback(
    (sessionId: string) => {
      selectSession(sessionId);
      handleSidebarClose();
    },
    [selectSession, handleSidebarClose]
  );

  const handleSessionDelete = useCallback(
    async (sessionId: string) => {
      await deleteSession(sessionId);
    },
    [deleteSession]
  );

  const drawerWidth = isMobile ? DRAWER_WIDTH_MOBILE : DRAWER_WIDTH_DESKTOP;

  const sidebarContent = (
    <Sidebar
      open={sidebarOpen}
      onClose={handleSidebarClose}
      currentView={currentView}
      onViewChange={handleViewChange}
      sessions={sessions}
      currentSessionId={currentSession?.id ?? null}
      onSessionSelect={handleSessionSelect}
      onSessionDelete={handleSessionDelete}
      onNewChat={handleNewChat}
      isMobile={isMobile || isTablet}
    />
  );

  return (
    <Box sx={{ display: 'flex', height: '100dvh', bgcolor: colors.bgLight }}>
      {/* Mobile/Tablet: Swipeable Drawer */}
      {(isMobile || isTablet) ? (
        <SwipeableDrawer
          open={sidebarOpen}
          onClose={handleSidebarClose}
          onOpen={() => setSidebarOpen(true)}
          disableSwipeToOpen={false}
          swipeAreaWidth={20}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              maxWidth: '85vw',
              boxSizing: 'border-box',
              borderRight: 'none',
              boxShadow: '4px 0 20px rgba(0, 0, 0, 0.15)',
            },
          }}
        >
          {sidebarContent}
        </SwipeableDrawer>
      ) : (
        /* Desktop: Persistent Drawer */
        <Box
          sx={{
            width: sidebarOpen ? drawerWidth : 0,
            flexShrink: 0,
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          }}
        >
          <Box
            sx={{
              width: drawerWidth,
              height: '100%',
              position: 'fixed',
              left: sidebarOpen ? 0 : -drawerWidth,
              transition: theme.transitions.create('left', {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
              boxShadow: '4px 0 20px rgba(0, 0, 0, 0.05)',
              zIndex: theme.zIndex.drawer,
            }}
          >
            {sidebarContent}
          </Box>
        </Box>
      )}

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100dvh',
          width: '100%',
          minWidth: 0,
          overflow: 'hidden',
        }}
      >
        {/* App Bar */}
        <AppBar
          position="static"
          elevation={0}
          sx={{
            bgcolor: colors.white,
            borderBottom: `1px solid ${colors.border}`,
            zIndex: theme.zIndex.appBar,
          }}
        >
          <Toolbar
            sx={{
              minHeight: { xs: 52, sm: 56, md: 64 },
              px: { xs: 1, sm: 1.5, md: 2 },
              gap: { xs: 0.5, sm: 1 },
            }}
          >
            <IconButton
              edge="start"
              onClick={handleSidebarToggle}
              aria-label="toggle sidebar"
              sx={{
                color: colors.dark,
                p: { xs: 1, sm: 1.25 },
                '&:hover': {
                  bgcolor: `${colors.primary}10`,
                },
              }}
            >
              {sidebarOpen && (isMobile || isTablet) ? (
                <CloseIcon sx={{ fontSize: { xs: 22, sm: 24 } }} />
              ) : (
                <MenuIcon sx={{ fontSize: { xs: 22, sm: 24 } }} />
              )}
            </IconButton>
            <Typography
              variant="h6"
              noWrap
              sx={{
                fontFamily: '"Asap", sans-serif',
                fontWeight: 600,
                color: colors.dark,
                fontSize: { xs: '0.9rem', sm: '1rem', md: '1.25rem' },
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {currentView === 'chat'
                ? currentSession?.title || 'Nueva Conversacion'
                : 'Base de Conocimiento'}
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Content Area */}
        <Box sx={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
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
