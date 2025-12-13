/**
 * Chat API service
 */

import { apiClient } from './api';
import type {
  ChatSession,
  ChatMessage,
  ChatStreamRequest,
  StreamEvent,
} from '@/types';

export const chatService = {
  /**
   * Create a new chat session
   */
  createSession: async (title?: string, userId?: string): Promise<ChatSession> => {
    return apiClient.post<ChatSession>('/api/v1/chat/sessions', {
      title,
      user_id: userId,
    });
  },

  /**
   * List chat sessions
   */
  listSessions: async (
    userId?: string,
    limit = 20,
    offset = 0
  ): Promise<ChatSession[]> => {
    return apiClient.get<ChatSession[]>('/api/v1/chat/sessions', {
      user_id: userId,
      limit,
      offset,
    });
  },

  /**
   * Get a specific session
   */
  getSession: async (sessionId: string): Promise<ChatSession> => {
    return apiClient.get<ChatSession>(`/api/v1/chat/sessions/${sessionId}`);
  },

  /**
   * Get messages from a session
   */
  getMessages: async (sessionId: string, limit = 50): Promise<ChatMessage[]> => {
    return apiClient.get<ChatMessage[]>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      { limit }
    );
  },

  /**
   * Delete a session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/chat/sessions/${sessionId}`);
  },

  /**
   * Stream chat response using fetch with ReadableStream
   */
  streamChat: async function* (
    request: ChatStreamRequest
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'https://api.ai.scram2k.com'}/api/v1/chat/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const event = JSON.parse(jsonStr) as StreamEvent;
              yield event;
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};
