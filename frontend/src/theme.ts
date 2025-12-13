import { createTheme, alpha } from '@mui/material/styles';

/**
 * SCRAM Corporate Theme for AI-SupraAgent
 * Based on GUIA_ESTILOS_SCRAM_PARA_IA.md
 */

// SCRAM Color Palette
const scramColors = {
  // Primary
  primary: '#ff9900',
  primaryHover: '#ff8c00',
  primaryLight: '#ffb84d',
  primaryDark: '#cc7a00',

  // Secondary
  dark: '#1a1a1a',
  darkLight: '#404040',

  // Accent
  green: '#44ce6f',
  greenDark: '#007a3d',
  purple: '#c679e3',

  // Neutrals
  white: '#ffffff',
  bgLight: '#f7fafd',
  bgLightAlt: '#f9f6f6',
  textNav: '#4a6f8a',
  textParagraph: '#6084a4',
  border: '#e0e0e0',

  // Semantic
  success: '#00A859',
  warning: '#ff9900',
  error: '#eb6b3d',
  info: '#4a6f8a',
};

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: scramColors.primary,
      light: scramColors.primaryLight,
      dark: scramColors.primaryDark,
      contrastText: scramColors.white,
    },
    secondary: {
      main: scramColors.dark,
      light: scramColors.darkLight,
      contrastText: scramColors.white,
    },
    success: {
      main: scramColors.success,
      contrastText: scramColors.white,
    },
    warning: {
      main: scramColors.warning,
      contrastText: scramColors.white,
    },
    error: {
      main: scramColors.error,
      contrastText: scramColors.white,
    },
    info: {
      main: scramColors.info,
      contrastText: scramColors.white,
    },
    background: {
      default: scramColors.white,
      paper: scramColors.bgLight,
    },
    text: {
      primary: scramColors.dark,
      secondary: scramColors.textParagraph,
    },
    divider: scramColors.border,
  },
  typography: {
    fontFamily: '"Cabin", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontFamily: '"Asap", sans-serif',
      fontWeight: 700,
      fontStyle: 'italic',
      fontSize: '2.625rem', // 42px
      lineHeight: 1.2,
      letterSpacing: '-0.02em',
      color: scramColors.dark,
    },
    h2: {
      fontFamily: '"Asap", sans-serif',
      fontWeight: 700,
      fontStyle: 'italic',
      fontSize: '2rem', // 32px
      lineHeight: 1.2,
      letterSpacing: '-0.01em',
      color: scramColors.dark,
    },
    h3: {
      fontFamily: '"Asap", sans-serif',
      fontWeight: 600,
      fontSize: '1.5rem', // 24px
      lineHeight: 1.3,
      letterSpacing: '-0.01em',
      color: scramColors.dark,
    },
    h4: {
      fontFamily: '"Asap", sans-serif',
      fontWeight: 600,
      fontSize: '1.375rem', // 22px
      lineHeight: 1.5,
      color: scramColors.dark,
    },
    h5: {
      fontFamily: '"Asap", sans-serif',
      fontWeight: 600,
      fontSize: '1.25rem', // 20px
      lineHeight: 1.5,
      color: scramColors.dark,
    },
    h6: {
      fontFamily: '"Asap", sans-serif',
      fontWeight: 600,
      fontSize: '1.125rem', // 18px
      lineHeight: 1.5,
      color: scramColors.dark,
    },
    body1: {
      fontSize: '1rem', // 16px
      lineHeight: 1.7,
      color: scramColors.textParagraph,
    },
    body2: {
      fontSize: '0.875rem', // 14px
      lineHeight: 1.6,
      color: scramColors.textParagraph,
    },
    button: {
      fontFamily: '"Cabin", sans-serif',
      fontWeight: 600,
      fontSize: '1rem',
      textTransform: 'none',
    },
    caption: {
      fontSize: '0.75rem', // 12px
      lineHeight: 1.4,
      color: scramColors.textNav,
    },
  },
  shape: {
    borderRadius: 12, // Default medium radius
  },
  shadows: [
    'none',
    '0 2px 4px rgba(0, 0, 0, 0.04)',
    '0 4px 8px rgba(0, 0, 0, 0.06)',
    '0 5px 15px rgba(0, 0, 0, 0.08)', // Card shadow
    '0 8px 20px rgba(0, 0, 0, 0.10)',
    '0 10px 25px rgba(0, 0, 0, 0.12)', // Card hover shadow
    '0 12px 28px rgba(0, 0, 0, 0.14)',
    '0 14px 32px rgba(0, 0, 0, 0.16)',
    '0 16px 36px rgba(0, 0, 0, 0.18)',
    '0 18px 40px rgba(0, 0, 0, 0.20)',
    '0 20px 44px rgba(0, 0, 0, 0.22)',
    '0 22px 48px rgba(0, 0, 0, 0.24)',
    '0 24px 52px rgba(0, 0, 0, 0.26)',
    '0 26px 56px rgba(0, 0, 0, 0.28)',
    '0 28px 60px rgba(0, 0, 0, 0.30)',
    '0 30px 64px rgba(0, 0, 0, 0.32)',
    '0 32px 68px rgba(0, 0, 0, 0.34)',
    '0 34px 72px rgba(0, 0, 0, 0.36)',
    '0 36px 76px rgba(0, 0, 0, 0.38)',
    '0 38px 80px rgba(0, 0, 0, 0.40)',
    '0 40px 84px rgba(0, 0, 0, 0.42)',
    '0 42px 88px rgba(0, 0, 0, 0.44)',
    '0 44px 92px rgba(0, 0, 0, 0.46)',
    '0 46px 96px rgba(0, 0, 0, 0.48)',
    '0 48px 100px rgba(0, 0, 0, 0.50)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: scramColors.white,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 100, // Pill shape
          padding: '10px 28px',
          fontWeight: 600,
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-2px)',
          },
        },
        contained: {
          boxShadow: `0 4px 12px ${alpha(scramColors.primary, 0.25)}`,
          '&:hover': {
            boxShadow: `0 6px 16px ${alpha(scramColors.primary, 0.35)}`,
          },
        },
        containedPrimary: {
          background: `linear-gradient(135deg, ${scramColors.primary} 0%, ${scramColors.primaryHover} 100%)`,
          '&:hover': {
            background: `linear-gradient(135deg, ${scramColors.primaryHover} 0%, ${scramColors.primaryDark} 100%)`,
          },
        },
        outlined: {
          borderWidth: 2,
          '&:hover': {
            borderWidth: 2,
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 5px 15px rgba(0, 0, 0, 0.08)',
          transition: 'all 0.3s ease',
          '&:hover': {
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.12)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        rounded: {
          borderRadius: 16,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            transition: 'all 0.3s ease',
            '&:hover': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: scramColors.primary,
              },
            },
            '&.Mui-focused': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: scramColors.primary,
                borderWidth: 2,
              },
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 100,
          fontWeight: 500,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          transition: 'all 0.3s ease',
          '&:hover': {
            backgroundColor: alpha(scramColors.primary, 0.1),
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: 'none',
          boxShadow: '4px 0 20px rgba(0, 0, 0, 0.08)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: scramColors.white,
          color: scramColors.dark,
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 100,
          backgroundColor: alpha(scramColors.primary, 0.2),
        },
        bar: {
          borderRadius: 100,
          background: `linear-gradient(135deg, ${scramColors.primary} 0%, ${scramColors.primaryHover} 100%)`,
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: scramColors.primary,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
        standardSuccess: {
          backgroundColor: alpha(scramColors.success, 0.1),
          color: scramColors.greenDark,
        },
        standardError: {
          backgroundColor: alpha(scramColors.error, 0.1),
          color: scramColors.error,
        },
        standardWarning: {
          backgroundColor: alpha(scramColors.warning, 0.1),
          color: scramColors.primaryDark,
        },
        standardInfo: {
          backgroundColor: alpha(scramColors.info, 0.1),
          color: scramColors.info,
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: scramColors.dark,
          borderRadius: 8,
          fontSize: '0.75rem',
          padding: '8px 12px',
        },
      },
    },
    MuiLink: {
      styleOverrides: {
        root: {
          color: scramColors.primary,
          textDecoration: 'none',
          transition: 'all 0.3s ease',
          '&:hover': {
            color: scramColors.primaryHover,
            textDecoration: 'underline',
          },
        },
      },
    },
  },
});

// Export SCRAM colors for direct use
export const colors = scramColors;
