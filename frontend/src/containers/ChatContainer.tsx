/**
 * Chat container component
 * Manages chat state and renders messages with input
 * Fully responsive for all screen sizes
 */

import { useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  useMediaQuery,
  useTheme,
  alpha,
} from '@mui/material';
import { SmartToy as BotIcon, Build as ToolIcon } from '@mui/icons-material';
import { MessageBubble } from '@/components/MessageBubble';
import { ChatInput } from '@/components/ChatInput';
import { useChat } from '@/hooks/useChat';
import { colors } from '@/theme';

interface ChatContainerProps {
  sessionId?: string;
}

export function ChatContainer({ sessionId }: ChatContainerProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const {
    messages,
    isLoading,
    isStreaming,
    error,
    activeToolCall,
    sendMessage,
  } = useChat({ sessionId });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [messages, isStreaming, activeToolCall]);

  const suggestedQuestions = [
    { label: 'Conversiones hoy', query: 'Como van las conversiones hoy?' },
    { label: 'Documentos', query: 'Que documentos tengo cargados?' },
    { label: 'Usuarios activos', query: 'Cuantos usuarios activos hay ahora?' },
  ];

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
      {/* Messages Area */}
      <Box
        ref={scrollContainerRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          p: { xs: 1, sm: 2, md: 3 },
          display: 'flex',
          flexDirection: 'column',
          // Custom scrollbar for desktop
          '&::-webkit-scrollbar': {
            width: 8,
          },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: alpha(colors.textNav, 0.2),
            borderRadius: 4,
            '&:hover': {
              bgcolor: alpha(colors.textNav, 0.3),
            },
          },
          '&::-webkit-scrollbar-track': {
            bgcolor: 'transparent',
          },
        }}
      >
        {isLoading && messages.length === 0 ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CircularProgress sx={{ color: colors.primary }} size={isMobile ? 32 : 40} />
          </Box>
        ) : messages.length === 0 ? (
          /* Welcome Screen */
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              px: { xs: 2, sm: 3, md: 4 },
              py: { xs: 3, sm: 4 },
            }}
          >
            {/* Logo */}
            <Box
              sx={{
                width: { xs: 56, sm: 72, md: 80 },
                height: { xs: 56, sm: 72, md: 80 },
                borderRadius: '50%',
                background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryHover} 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: { xs: 2, sm: 3 },
                boxShadow: `0 8px 24px ${colors.primary}40`,
              }}
            >
              <BotIcon sx={{ fontSize: { xs: 28, sm: 36, md: 40 }, color: colors.white }} />
            </Box>

            {/* Title */}
            <Typography
              variant="h4"
              sx={{
                fontFamily: '"Asap", sans-serif',
                fontWeight: 700,
                fontStyle: 'italic',
                color: colors.dark,
                mb: { xs: 1, sm: 1.5 },
                fontSize: { xs: '1.25rem', sm: '1.5rem', md: '2rem' },
                lineHeight: 1.2,
              }}
            >
              Hola, soy AI-SupraAgent
            </Typography>

            {/* Description */}
            <Typography
              variant="body1"
              sx={{
                color: colors.textParagraph,
                maxWidth: { xs: '100%', sm: 450, md: 500 },
                mb: { xs: 2.5, sm: 3 },
                lineHeight: 1.6,
                fontSize: { xs: '0.85rem', sm: '0.95rem', md: '1rem' },
              }}
            >
              Puedo ayudarte a analizar datos de Google Analytics, Google Ads,
              y responder preguntas sobre tu base de conocimiento.
            </Typography>

            {/* Suggested Questions */}
            <Box
              sx={{
                display: 'flex',
                gap: { xs: 0.75, sm: 1 },
                flexWrap: 'wrap',
                justifyContent: 'center',
                maxWidth: { xs: '100%', sm: 400 },
              }}
            >
              {suggestedQuestions.map((item, idx) => (
                <Chip
                  key={idx}
                  label={item.label}
                  onClick={() => sendMessage(item.query)}
                  size={isMobile ? 'small' : 'medium'}
                  sx={{
                    bgcolor: colors.bgLight,
                    border: `1px solid ${colors.border}`,
                    fontSize: { xs: '0.75rem', sm: '0.8125rem' },
                    height: { xs: 28, sm: 32 },
                    '&:hover': {
                      bgcolor: `${colors.primary}15`,
                      borderColor: colors.primary,
                    },
                    '&:active': {
                      bgcolor: `${colors.primary}25`,
                    },
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                />
              ))}
            </Box>
          </Box>
        ) : (
          /* Messages */
          <>
            {messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
              />
            ))}

            {/* Active tool call indicator */}
            {activeToolCall && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: { xs: 1, sm: 1.5 },
                  p: { xs: 1.5, sm: 2 },
                  mx: { xs: 0, sm: 1 },
                  bgcolor: `${colors.primary}08`,
                  borderRadius: 2,
                  border: `1px solid ${colors.primary}20`,
                  mb: 2,
                }}
              >
                <CircularProgress size={isMobile ? 16 : 20} sx={{ color: colors.primary }} />
                <ToolIcon sx={{ color: colors.primary, fontSize: { xs: 18, sm: 22 } }} />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      color: colors.dark,
                      fontSize: { xs: '0.8rem', sm: '0.875rem' },
                      display: 'flex',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: 0.5,
                    }}
                  >
                    Ejecutando:
                    <Chip
                      label={activeToolCall.tool_name}
                      size="small"
                      sx={{
                        bgcolor: colors.primary,
                        color: colors.white,
                        fontWeight: 600,
                        fontSize: { xs: '0.7rem', sm: '0.75rem' },
                        height: { xs: 22, sm: 24 },
                      }}
                    />
                  </Typography>
                </Box>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </>
        )}

        {/* Error display */}
        {error && (
          <Alert
            severity="error"
            sx={{
              mb: 2,
              mx: { xs: 0, sm: 1 },
              fontSize: { xs: '0.8rem', sm: '0.875rem' },
            }}
          >
            {error.message}
          </Alert>
        )}
      </Box>

      {/* Input Area */}
      <ChatInput
        onSend={sendMessage}
        disabled={isLoading}
        isLoading={isStreaming}
        placeholder={isMobile ? 'Mensaje...' : 'Escribe tu mensaje...'}
      />
    </Box>
  );
}
