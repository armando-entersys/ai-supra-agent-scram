/**
 * Chat message bubble component
 * Displays user and assistant messages with SCRAM styling
 * Fully responsive with optimized mobile layout
 */

import { memo } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import {
  SmartToy as BotIcon,
  Person as UserIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { colors } from '@/theme';
import type { ChatMessage } from '@/types';

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
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
        <Box
          sx={{
            color: isUser ? colors.white : colors.textParagraph,
            lineHeight: 1.6,
            fontSize: { xs: '0.85rem', sm: '0.9rem', md: '1rem' },
            '& p': {
              margin: 0,
              marginBottom: 1,
              '&:last-child': { marginBottom: 0 },
            },
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
            '& strong, & b': {
              fontWeight: 600,
            },
            '& em, & i': {
              fontStyle: 'italic',
            },
            '& ul, & ol': {
              pl: 2,
              my: 1,
            },
            '& li': {
              mb: 0.5,
            },
            // Table styling
            '& table': {
              width: '100%',
              borderCollapse: 'collapse',
              my: 2,
              fontSize: { xs: '0.75rem', sm: '0.8rem', md: '0.875rem' },
              display: 'block',
              overflowX: 'auto',
            },
            '& th, & td': {
              border: `1px solid ${isUser ? 'rgba(255,255,255,0.3)' : colors.border}`,
              px: { xs: 1, sm: 1.5 },
              py: { xs: 0.5, sm: 0.75 },
              textAlign: 'left',
              whiteSpace: 'nowrap',
            },
            '& th': {
              bgcolor: isUser ? 'rgba(255,255,255,0.1)' : `${colors.primary}15`,
              fontWeight: 600,
              color: isUser ? colors.white : colors.dark,
            },
            '& tr:nth-of-type(even)': {
              bgcolor: isUser ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
            },
            '& tr:hover': {
              bgcolor: isUser ? 'rgba(255,255,255,0.1)' : `${colors.primary}08`,
            },
          }}
        >
          {isUser ? (
            <Typography sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {message.content}
            </Typography>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
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
        </Box>

        {/* Tool calls - hidden for cleaner UX */}
      </Paper>
    </Box>
  );
});
