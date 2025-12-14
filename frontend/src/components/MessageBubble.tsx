/**
 * Chat message bubble component
 * Displays user and assistant messages with SCRAM styling
 * Fully responsive with optimized mobile layout
 */

import { memo } from 'react';
import { Box, Typography, Paper, Chip, CircularProgress, useMediaQuery, useTheme } from '@mui/material';
import {
  SmartToy as BotIcon,
  Person as UserIcon,
  Build as ToolIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { colors } from '@/theme';
import type { ChatMessage, ToolCall } from '@/types';

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

function ToolCallIndicator({ toolCall, isMobile }: { toolCall: ToolCall; isMobile: boolean }) {
  const isRunning = toolCall.status === 'running' || toolCall.status === 'pending';

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: { xs: 0.75, sm: 1 },
        mt: 1,
        p: { xs: 1, sm: 1.5 },
        bgcolor: 'rgba(255, 153, 0, 0.08)',
        borderRadius: 1.5,
        border: `1px solid ${colors.primary}20`,
      }}
    >
      {isRunning ? (
        <CircularProgress size={isMobile ? 14 : 16} sx={{ color: colors.primary }} />
      ) : (
        <CheckIcon sx={{ fontSize: isMobile ? 14 : 16, color: colors.success }} />
      )}
      <Typography
        variant="caption"
        sx={{
          fontWeight: 500,
          color: colors.dark,
          fontSize: { xs: '0.7rem', sm: '0.75rem' },
        }}
      >
        {isRunning ? 'Ejecutando' : 'Completado'}:
      </Typography>
      <Chip
        label={toolCall.tool_name}
        size="small"
        sx={{
          bgcolor: isRunning ? colors.primary : colors.success,
          color: colors.white,
          fontWeight: 600,
          fontSize: { xs: '0.65rem', sm: '0.7rem' },
          height: { xs: 20, sm: 22 },
          '& .MuiChip-label': {
            px: { xs: 1, sm: 1.5 },
          },
        }}
      />
    </Box>
  );
}

export const MessageBubble = memo(function MessageBubble({
  message,
  isStreaming = false,
}: MessageBubbleProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        gap: { xs: 0.75, sm: 1.5 },
        mb: { xs: 1, sm: 1.5, md: 2 },
        maxWidth: '100%',
        px: { xs: 0, sm: 0.5 },
      }}
    >
      {/* Avatar */}
      <Box
        sx={{
          width: { xs: 28, sm: 32, md: 36 },
          height: { xs: 28, sm: 32, md: 36 },
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: isUser ? colors.dark : colors.primary,
          flexShrink: 0,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.12)',
          alignSelf: 'flex-start',
          mt: 0.5,
        }}
      >
        {isUser ? (
          <UserIcon sx={{ fontSize: { xs: 14, sm: 16, md: 18 }, color: colors.white }} />
        ) : (
          <BotIcon sx={{ fontSize: { xs: 14, sm: 16, md: 18 }, color: colors.white }} />
        )}
      </Box>

      {/* Message Content */}
      <Paper
        elevation={0}
        sx={{
          maxWidth: { xs: 'calc(100% - 40px)', sm: '80%', md: '75%' },
          minWidth: { xs: 60, sm: 80 },
          p: { xs: 1.25, sm: 1.5, md: 2 },
          borderRadius: { xs: 2, sm: 2.5, md: 3 },
          bgcolor: isUser ? colors.dark : colors.bgLight,
          color: isUser ? colors.white : colors.dark,
          position: 'relative',
          wordBreak: 'break-word',
        }}
      >
        <Typography
          component="div"
          sx={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            color: isUser ? colors.white : colors.textParagraph,
            lineHeight: 1.6,
            fontSize: { xs: '0.85rem', sm: '0.9rem', md: '1rem' },
            '& code': {
              bgcolor: isUser ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.06)',
              px: 0.5,
              py: 0.25,
              borderRadius: 0.5,
              fontFamily: '"Fira Code", "Monaco", monospace',
              fontSize: '0.85em',
            },
            '& pre': {
              bgcolor: isUser ? 'rgba(255,255,255,0.1)' : colors.dark,
              color: isUser ? colors.white : colors.bgLight,
              p: { xs: 1, sm: 1.5 },
              borderRadius: 1.5,
              overflow: 'auto',
              fontSize: { xs: '0.75rem', sm: '0.8rem', md: '0.875rem' },
              my: 1,
              '& code': {
                bgcolor: 'transparent',
                p: 0,
              },
            },
            // Markdown-like formatting
            '& strong, & b': {
              fontWeight: 600,
            },
            '& em, & i': {
              fontStyle: 'italic',
            },
          }}
        >
          {message.content}
          {isStreaming && isAssistant && (
            <Box
              component="span"
              sx={{
                display: 'inline-block',
                width: { xs: 6, sm: 8 },
                height: { xs: 14, sm: 16 },
                bgcolor: colors.primary,
                ml: 0.5,
                borderRadius: 0.5,
                animation: 'blink 1s infinite',
                '@keyframes blink': {
                  '0%, 50%': { opacity: 1 },
                  '51%, 100%': { opacity: 0 },
                },
              }}
            />
          )}
        </Typography>

        {/* Tool calls */}
        {message.tool_calls?.calls?.map((toolCall, index) => (
          <ToolCallIndicator key={index} toolCall={toolCall} isMobile={isMobile} />
        ))}
      </Paper>
    </Box>
  );
});
