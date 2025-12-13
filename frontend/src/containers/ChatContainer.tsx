/**
 * Chat container component
 * Manages chat state and renders messages with input
 */

import { useRef, useEffect } from 'react';
import { Box, Typography, CircularProgress, Alert, Chip } from '@mui/material';
import { SmartToy as BotIcon, Build as ToolIcon } from '@mui/icons-material';
import { MessageBubble } from '@/components/MessageBubble';
import { ChatInput } from '@/components/ChatInput';
import { useChat } from '@/hooks/useChat';
import { colors } from '@/theme';

interface ChatContainerProps {
  sessionId?: string;
}

export function ChatContainer({ sessionId }: ChatContainerProps) {
  const {
    messages,
    isLoading,
    isStreaming,
    error,
    activeToolCall,
    sendMessage,
  } = useChat({ sessionId });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: colors.white,
      }}
    >
      {/* Messages Area */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: { xs: 1.5, sm: 3 },
          display: 'flex',
          flexDirection: 'column',
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
            <CircularProgress sx={{ color: colors.primary }} />
          </Box>
        ) : messages.length === 0 ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              px: { xs: 2, sm: 4 },
            }}
          >
            <Box
              sx={{
                width: { xs: 60, sm: 80 },
                height: { xs: 60, sm: 80 },
                borderRadius: '50%',
                background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryHover} 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: { xs: 2, sm: 3 },
                boxShadow: `0 8px 24px ${colors.primary}40`,
              }}
            >
              <BotIcon sx={{ fontSize: { xs: 30, sm: 40 }, color: colors.white }} />
            </Box>
            <Typography
              variant="h4"
              sx={{
                fontFamily: '"Asap", sans-serif',
                fontWeight: 700,
                fontStyle: 'italic',
                color: colors.dark,
                mb: { xs: 1, sm: 2 },
                fontSize: { xs: '1.5rem', sm: '2.125rem' },
              }}
            >
              Hola, soy AI-SupraAgent
            </Typography>
            <Typography
              variant="body1"
              sx={{
                color: colors.textParagraph,
                maxWidth: 500,
                mb: { xs: 2, sm: 3 },
                lineHeight: 1.7,
                fontSize: { xs: '0.875rem', sm: '1rem' },
                px: { xs: 1, sm: 0 },
              }}
            >
              Puedo ayudarte a analizar datos de Google Analytics, responder preguntas
              sobre tu base de conocimiento y mucho mas. Escribe tu pregunta para comenzar.
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center', px: { xs: 1, sm: 0 } }}>
              <Chip
                label="Como van las conversiones hoy?"
                onClick={() => sendMessage('Como van las conversiones hoy?')}
                size="small"
                sx={{
                  bgcolor: colors.bgLight,
                  '&:hover': { bgcolor: `${colors.primary}15` },
                  cursor: 'pointer',
                  fontSize: { xs: '0.75rem', sm: '0.8125rem' },
                }}
              />
              <Chip
                label="Que documentos tengo cargados?"
                onClick={() => sendMessage('Que documentos tengo cargados?')}
                size="small"
                sx={{
                  bgcolor: colors.bgLight,
                  '&:hover': { bgcolor: `${colors.primary}15` },
                  cursor: 'pointer',
                  fontSize: { xs: '0.75rem', sm: '0.8125rem' },
                }}
              />
              <Chip
                label="Usuarios activos ahora"
                onClick={() => sendMessage('Cuantos usuarios activos hay ahora mismo?')}
                size="small"
                sx={{
                  bgcolor: colors.bgLight,
                  '&:hover': { bgcolor: `${colors.primary}15` },
                  cursor: 'pointer',
                  fontSize: { xs: '0.75rem', sm: '0.8125rem' },
                }}
              />
            </Box>
          </Box>
        ) : (
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
                  gap: 1.5,
                  p: 2,
                  bgcolor: `${colors.primary}08`,
                  borderRadius: 2,
                  border: `1px solid ${colors.primary}20`,
                  mb: 2,
                }}
              >
                <CircularProgress size={20} sx={{ color: colors.primary }} />
                <ToolIcon sx={{ color: colors.primary }} />
                <Typography variant="body2" sx={{ color: colors.dark }}>
                  Ejecutando:{' '}
                  <Chip
                    label={activeToolCall.tool_name}
                    size="small"
                    sx={{
                      bgcolor: colors.primary,
                      color: colors.white,
                      fontWeight: 600,
                      ml: 0.5,
                    }}
                  />
                </Typography>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </>
        )}

        {/* Error display */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error.message}
          </Alert>
        )}
      </Box>

      {/* Input Area */}
      <ChatInput
        onSend={sendMessage}
        disabled={isLoading}
        isLoading={isStreaming}
        placeholder="Escribe tu mensaje..."
      />
    </Box>
  );
}
