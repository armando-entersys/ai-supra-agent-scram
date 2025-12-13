/**
 * Chat message bubble component
 * Displays user and assistant messages with SCRAM styling
 */

import { memo } from 'react';
import { Box, Typography, Paper, Chip, CircularProgress } from '@mui/material';
import {
  SmartToy as BotIcon,
  Person as UserIcon,
  Build as ToolIcon,
} from '@mui/icons-material';
import { colors } from '@/theme';
import type { ChatMessage, ToolCall } from '@/types';

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

function ToolCallIndicator({ toolCall }: { toolCall: ToolCall }) {
  const isRunning = toolCall.status === 'running' || toolCall.status === 'pending';

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        mt: 1,
        p: 1.5,
        bgcolor: 'rgba(255, 153, 0, 0.08)',
        borderRadius: 2,
        border: `1px solid ${colors.primary}20`,
      }}
    >
      {isRunning ? (
        <CircularProgress size={16} sx={{ color: colors.primary }} />
      ) : (
        <ToolIcon sx={{ fontSize: 16, color: colors.primary }} />
      )}
      <Typography variant="caption" sx={{ fontWeight: 500, color: colors.dark }}>
        {isRunning ? 'Ejecutando' : 'Completado'}:
      </Typography>
      <Chip
        label={toolCall.tool_name}
        size="small"
        sx={{
          bgcolor: colors.primary,
          color: colors.white,
          fontWeight: 600,
          fontSize: '0.7rem',
        }}
      />
    </Box>
  );
}

export const MessageBubble = memo(function MessageBubble({
  message,
  isStreaming = false,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        gap: 1.5,
        mb: 2,
        maxWidth: '100%',
      }}
    >
      {/* Avatar */}
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: isUser ? colors.dark : colors.primary,
          flexShrink: 0,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
        }}
      >
        {isUser ? (
          <UserIcon sx={{ fontSize: 20, color: colors.white }} />
        ) : (
          <BotIcon sx={{ fontSize: 20, color: colors.white }} />
        )}
      </Box>

      {/* Message Content */}
      <Paper
        elevation={0}
        sx={{
          maxWidth: '75%',
          p: 2,
          borderRadius: 3,
          bgcolor: isUser ? colors.dark : colors.bgLight,
          color: isUser ? colors.white : colors.dark,
          position: 'relative',
          '&::before': isUser
            ? {
                content: '""',
                position: 'absolute',
                right: -8,
                top: 12,
                width: 0,
                height: 0,
                borderTop: '8px solid transparent',
                borderBottom: '8px solid transparent',
                borderLeft: `8px solid ${colors.dark}`,
              }
            : {
                content: '""',
                position: 'absolute',
                left: -8,
                top: 12,
                width: 0,
                height: 0,
                borderTop: '8px solid transparent',
                borderBottom: '8px solid transparent',
                borderRight: `8px solid ${colors.bgLight}`,
              },
        }}
      >
        <Typography
          variant="body1"
          sx={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            color: isUser ? colors.white : colors.textParagraph,
            lineHeight: 1.6,
            '& code': {
              bgcolor: isUser ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.05)',
              px: 0.5,
              py: 0.25,
              borderRadius: 1,
              fontFamily: 'monospace',
              fontSize: '0.875em',
            },
            '& pre': {
              bgcolor: isUser ? 'rgba(255,255,255,0.1)' : colors.dark,
              color: isUser ? colors.white : colors.bgLight,
              p: 1.5,
              borderRadius: 2,
              overflow: 'auto',
              '& code': {
                bgcolor: 'transparent',
              },
            },
          }}
        >
          {message.content}
          {isStreaming && isAssistant && (
            <Box
              component="span"
              sx={{
                display: 'inline-block',
                width: 8,
                height: 16,
                bgcolor: colors.primary,
                ml: 0.5,
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
          <ToolCallIndicator key={index} toolCall={toolCall} />
        ))}
      </Paper>
    </Box>
  );
});
