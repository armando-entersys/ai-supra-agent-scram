/**
 * Custom hook for chat functionality with streaming
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatService } from '@/services/chat';
import type { ChatMessage, ChatSession, ToolCall, StreamEvent } from '@/types';

interface UseChatOptions {
  sessionId?: string;
  useRag?: boolean;
  useAnalytics?: boolean;
}

interface UseChatReturn {
  messages: ChatMessage[];
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: Error | null;
  activeToolCall: ToolCall | null;
  sendMessage: (content: string) => Promise<void>;
  createSession: (title?: string) => Promise<ChatSession>;
  selectSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => Promise<void>;
  clearMessages: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { sessionId: initialSessionId, useRag = true, useAnalytics = true } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(initialSessionId ?? null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolCall, setActiveToolCall] = useState<ToolCall | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const queryClient = useQueryClient();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Sync internal state when external sessionId prop changes
  useEffect(() => {
    const newSessionId = initialSessionId ?? null;
    setCurrentSessionId(newSessionId);
    setMessages([]);
  }, [initialSessionId]);

  // Fetch sessions
  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => chatService.listSessions(),
  });

  // Fetch current session details
  const { data: currentSession } = useQuery({
    queryKey: ['chat-session', currentSessionId],
    queryFn: () => (currentSessionId ? chatService.getSession(currentSessionId) : null),
    enabled: !!currentSessionId,
  });

  // Fetch messages when session changes
  const { data: fetchedMessages, isLoading: messagesLoading } = useQuery({
    queryKey: ['chat-messages', currentSessionId],
    queryFn: () => currentSessionId ? chatService.getMessages(currentSessionId) : Promise.resolve([]),
    enabled: !!currentSessionId,
    staleTime: 0,
    gcTime: 0, // Don't cache old messages
  });

  // Update messages state when fetched messages change
  useEffect(() => {
    if (fetchedMessages && fetchedMessages.length > 0) {
      setMessages(fetchedMessages);
    }
  }, [fetchedMessages]);

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: (title?: string) => chatService.createSession(title),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
      setCurrentSessionId(session.id);
      setMessages([]);
    },
  });

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => chatService.deleteSession(sessionId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
      if (currentSessionId === deletedId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    },
  });

  // Send message with streaming
  const sendMessage = useCallback(
    async (content: string) => {
      setError(null);
      setIsStreaming(true);

      // Add optimistic user message
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        session_id: currentSessionId || '',
        role: 'user',
        content,
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Add placeholder assistant message
      const assistantMessageId = crypto.randomUUID();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        session_id: currentSessionId || '',
        role: 'assistant',
        content: '',
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      try {
        const stream = chatService.streamChat({
          message: content,
          session_id: currentSessionId || undefined,
          use_rag: useRag,
          use_analytics: useAnalytics,
        });

        let fullContent = '';
        const toolCalls: ToolCall[] = [];

        for await (const event of stream) {
          if (event.event === 'text') {
            fullContent += event.data as string;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: fullContent }
                  : msg
              )
            );
          } else if (event.event === 'tool_call') {
            const toolCall = event.data as ToolCall;
            if (toolCall.status === 'running') {
              setActiveToolCall(toolCall);
            } else if (toolCall.status === 'completed' || toolCall.status === 'error') {
              toolCalls.push(toolCall);
              setActiveToolCall(null);
            }
          } else if (event.event === 'done') {
            // Always clear tool call on done
            setActiveToolCall(null);
            const doneData = event.data as { session_id: string };
            if (!currentSessionId && doneData.session_id) {
              setCurrentSessionId(doneData.session_id);
              queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
            }
          } else if (event.event === 'error') {
            throw new Error(event.data as string);
          }
        }

        // Update final message with tool calls
        if (toolCalls.length > 0) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, tool_calls: { calls: toolCalls } }
                : msg
            )
          );
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Stream failed'));
        // Remove failed assistant message
        setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
      } finally {
        setIsStreaming(false);
        setActiveToolCall(null);
      }
    },
    [currentSessionId, useRag, useAnalytics, queryClient]
  );

  const createSession = useCallback(
    async (title?: string) => {
      return createSessionMutation.mutateAsync(title);
    },
    [createSessionMutation]
  );

  const selectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
    setMessages([]);
  }, []);

  const deleteSession = useCallback(
    async (sessionId: string) => {
      await deleteSessionMutation.mutateAsync(sessionId);
    },
    [deleteSessionMutation]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentSessionId(null);
  }, []);

  return {
    messages,
    sessions,
    currentSession: currentSession ?? null,
    isLoading: sessionsLoading || messagesLoading,
    isStreaming,
    error,
    activeToolCall,
    sendMessage,
    createSession,
    selectSession,
    deleteSession,
    clearMessages,
  };
}
