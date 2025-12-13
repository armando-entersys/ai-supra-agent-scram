/**
 * Chat input component with send button
 * SCRAM styled with pill shape and gradient
 */

import { useState, useCallback, type KeyboardEvent, type ChangeEvent } from 'react';
import {
  Box,
  TextField,
  IconButton,
  CircularProgress,
  InputAdornment,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachIcon,
} from '@mui/icons-material';
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
        gap: { xs: 0.5, sm: 1 },
        p: { xs: 1, sm: 2 },
        bgcolor: colors.white,
        borderTop: `1px solid ${colors.border}`,
      }}
    >
      <TextField
        fullWidth
        multiline
        maxRows={4}
        value={message}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isDisabled}
        variant="outlined"
        size="small"
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: { xs: 2, sm: 3 },
            bgcolor: colors.bgLight,
            transition: 'all 0.3s ease',
            '& fieldset': {
              borderColor: 'transparent',
            },
            '&:hover fieldset': {
              borderColor: colors.primary,
            },
            '&.Mui-focused fieldset': {
              borderColor: colors.primary,
              borderWidth: 2,
            },
          },
          '& .MuiInputBase-input': {
            py: { xs: 1, sm: 1.5 },
            fontSize: { xs: '0.875rem', sm: '1rem' },
          },
        }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start" sx={{ display: { xs: 'none', sm: 'flex' } }}>
              <Tooltip title="Adjuntar archivo (pronto)">
                <span>
                  <IconButton
                    size="small"
                    disabled
                    sx={{
                      color: colors.textNav,
                      '&:hover': {
                        color: colors.primary,
                      },
                    }}
                  >
                    <AttachIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
            </InputAdornment>
          ),
        }}
      />

      <IconButton
        onClick={handleSend}
        disabled={!canSend}
        sx={{
          width: { xs: 40, sm: 48 },
          height: { xs: 40, sm: 48 },
          minWidth: { xs: 40, sm: 48 },
          background: canSend
            ? `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryHover} 100%)`
            : colors.border,
          color: colors.white,
          borderRadius: '50%',
          boxShadow: canSend ? `0 4px 12px rgba(255, 153, 0, 0.35)` : 'none',
          transition: 'all 0.3s ease',
          '&:hover': {
            background: canSend
              ? `linear-gradient(135deg, ${colors.primaryHover} 0%, ${colors.primaryDark} 100%)`
              : colors.border,
            transform: canSend ? 'translateY(-2px)' : 'none',
            boxShadow: canSend ? `0 6px 16px rgba(255, 153, 0, 0.45)` : 'none',
          },
          '&.Mui-disabled': {
            color: colors.textNav,
          },
        }}
      >
        {isLoading ? (
          <CircularProgress size={20} sx={{ color: colors.white }} />
        ) : (
          <SendIcon sx={{ fontSize: { xs: 20, sm: 24 } }} />
        )}
      </IconButton>
    </Box>
  );
}
