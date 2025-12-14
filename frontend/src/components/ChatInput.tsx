/**
 * Chat input component with send button
 * SCRAM styled with pill shape and gradient
 * Optimized for mobile with safe area support
 */

import { useState, useCallback, type KeyboardEvent, type ChangeEvent } from 'react';
import {
  Box,
  TextField,
  IconButton,
  CircularProgress,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { colors } from '@/theme';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  isLoading = false,
  placeholder = 'Escribe tu mensaje...',
}: ChatInputProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const [message, setMessage] = useState('');

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setMessage(e.target.value);
  }, []);

  const handleSend = useCallback(() => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled && !isLoading) {
      onSend(trimmedMessage);
      setMessage('');
    }
  }, [message, onSend, disabled, isLoading]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const isDisabled = disabled || isLoading;
  const canSend = message.trim().length > 0 && !isDisabled;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: { xs: 0.75, sm: 1 },
        p: { xs: 1, sm: 1.5, md: 2 },
        bgcolor: colors.white,
        borderTop: `1px solid ${colors.border}`,
        // Safe area for iOS
        pb: { xs: 'max(env(safe-area-inset-bottom, 8px), 8px)', sm: 1.5, md: 2 },
      }}
    >
      <TextField
        fullWidth
        multiline
        maxRows={isMobile ? 3 : 4}
        value={message}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isDisabled}
        variant="outlined"
        size="small"
        autoComplete="off"
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: { xs: 2.5, sm: 3 },
            bgcolor: colors.bgLight,
            transition: 'all 0.2s ease',
            '& fieldset': {
              borderColor: 'transparent',
              borderWidth: 1,
            },
            '&:hover fieldset': {
              borderColor: `${colors.primary}50`,
            },
            '&.Mui-focused fieldset': {
              borderColor: colors.primary,
              borderWidth: 2,
            },
          },
          '& .MuiInputBase-input': {
            py: { xs: 1.25, sm: 1.5 },
            px: { xs: 1.5, sm: 2 },
            fontSize: { xs: '0.9rem', sm: '1rem' },
            lineHeight: 1.5,
            '&::placeholder': {
              color: colors.textNav,
              opacity: 0.8,
            },
          },
        }}
      />

      <IconButton
        onClick={handleSend}
        disabled={!canSend}
        aria-label="Enviar mensaje"
        sx={{
          width: { xs: 42, sm: 46, md: 48 },
          height: { xs: 42, sm: 46, md: 48 },
          minWidth: { xs: 42, sm: 46, md: 48 },
          flexShrink: 0,
          background: canSend
            ? `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryHover} 100%)`
            : colors.border,
          color: colors.white,
          borderRadius: '50%',
          boxShadow: canSend ? `0 4px 12px rgba(255, 153, 0, 0.35)` : 'none',
          transition: 'all 0.2s ease',
          '&:hover': {
            background: canSend
              ? `linear-gradient(135deg, ${colors.primaryHover} 0%, ${colors.primaryDark} 100%)`
              : colors.border,
            transform: canSend ? 'scale(1.05)' : 'none',
            boxShadow: canSend ? `0 6px 16px rgba(255, 153, 0, 0.45)` : 'none',
          },
          '&:active': {
            transform: canSend ? 'scale(0.95)' : 'none',
          },
          '&.Mui-disabled': {
            color: colors.textNav,
            bgcolor: colors.border,
          },
        }}
      >
        {isLoading ? (
          <CircularProgress
            size={isMobile ? 18 : 22}
            sx={{ color: colors.white }}
          />
        ) : (
          <SendIcon sx={{ fontSize: { xs: 20, sm: 22, md: 24 } }} />
        )}
      </IconButton>
    </Box>
  );
}
