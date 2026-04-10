"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  apiClient,
  type ImageGenTemplate,
  type ImageGenSession,
  type ImageGenMessage,
} from "@/lib/api";

export interface ImageGenUsage {
  used: number;
  limit: number;
  remaining: number | null;
  is_unlimited: boolean;
  period: string;
}

export function useImageGen() {
  const [templates, setTemplates] = useState<ImageGenTemplate[]>([]);
  const [sessions, setSessions] = useState<ImageGenSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ImageGenSession | null>(null);
  const [messages, setMessages] = useState<ImageGenMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<ImageGenUsage | null>(null);
  const sessionCacheRef = useRef<Record<string, ImageGenSession>>({});
  const messagesRef = useRef<ImageGenMessage[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const applySessionState = useCallback((session: ImageGenSession) => {
    setCurrentSession(session);
    setMessages(session.messages || []);
  }, []);

  const cacheSession = useCallback((session: ImageGenSession) => {
    sessionCacheRef.current[session.id] = session;
  }, []);

  // ── Usage / Quota ──

  const fetchUsage = useCallback(async () => {
    try {
      const data = await apiClient.getImageGenUsage();
      setUsage(data);
    } catch {
      // Non-critical, don't block UI
    }
  }, []);

  // ── Templates ──

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.listImageGenTemplates();
      setTemplates(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "テンプレートの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createTemplate = useCallback(
    async (data: {
      name: string;
      description?: string;
      category?: string;
      aspect_ratio?: string;
      image_size?: string;
      system_prompt?: string;
      visibility?: string;
      created_by?: string;
      created_by_email?: string;
    }) => {
      const result = await apiClient.createImageGenTemplate(data as ImageGenTemplate);
      setTemplates((prev) => [result, ...prev]);
      return result;
    },
    []
  );

  const updateTemplate = useCallback(
    async (id: string, data: Partial<ImageGenTemplate>) => {
      const result = await apiClient.updateImageGenTemplate(id, data);
      setTemplates((prev) => prev.map((t) => (t.id === id ? { ...t, ...result } : t)));
      return result;
    },
    []
  );

  const deleteTemplate = useCallback(
    async (id: string) => {
      await apiClient.deleteImageGenTemplate(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    },
    []
  );

  // ── References ──

  const uploadReference = useCallback(
    async (templateId: string, file: File, label: string = "style") => {
      const result = await apiClient.uploadImageGenReference(templateId, file, label);
      // Refresh template to get updated references
      const updated = await apiClient.getImageGenTemplate(templateId);
      setTemplates((prev) => prev.map((t) => (t.id === templateId ? updated : t)));
      return result;
    },
    []
  );

  const deleteReference = useCallback(
    async (referenceId: string, templateId: string) => {
      await apiClient.deleteImageGenReference(referenceId);
      const updated = await apiClient.getImageGenTemplate(templateId);
      setTemplates((prev) => prev.map((t) => (t.id === templateId ? updated : t)));
    },
    []
  );

  // ── Sessions ──

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.listImageGenSessions();
      setSessions(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "セッションの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createSession = useCallback(
    async (data: {
      template_id?: string;
      title?: string;
      aspect_ratio?: string;
      image_size?: string;
      created_by?: string;
      created_by_email?: string;
    }) => {
      const result = await apiClient.createImageGenSession(data);
      cacheSession(result);
      setSessions((prev) => [result, ...prev]);
      applySessionState(result);
      return result;
    },
    [applySessionState, cacheSession]
  );

  const loadSession = useCallback(async (
    sessionId: string,
    options?: { seedSession?: ImageGenSession }
  ) => {
    const cached = sessionCacheRef.current[sessionId];
    if (cached) {
      applySessionState(cached);
      return cached;
    }

    if (options?.seedSession) {
      setCurrentSession(options.seedSession);
      setMessages([]);
    }

    setLoadingSessionId(sessionId);
    setIsLoading(true);
    try {
      const session = await apiClient.getImageGenSession(sessionId);
      cacheSession(session);
      applySessionState(session);
      setSessions((prev) =>
        prev.map((item) =>
          item.id === session.id ? { ...item, ...session, messages: undefined } : item
        )
      );
      return session;
    } catch (e) {
      setError(e instanceof Error ? e.message : "セッションの読み込みに失敗しました");
      return null;
    } finally {
      setLoadingSessionId((prev) => (prev === sessionId ? null : prev));
      setIsLoading(false);
    }
  }, [applySessionState, cacheSession]);

  // ── Update Session Template ──

  const updateSessionTemplate = useCallback(
    async (sessionId: string, templateId: string | null) => {
      try {
        // Update session's template_id on the backend
        await apiClient.updateImageGenSession(sessionId, {
          template_id: templateId,
        });
        // Update local state
        setCurrentSession((prev) =>
          prev ? { ...prev, template_id: templateId } : prev
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : "セッションの更新に失敗しました");
      }
    },
    []
  );

  // ── Generation ──

  const generateImage = useCallback(
    async (
      prompt: string,
      options?: { aspect_ratio?: string; image_size?: string; sessionId?: string }
    ) => {
      const targetSessionId = options?.sessionId || currentSession?.id;
      if (!targetSessionId) {
        setError("セッションが選択されていません");
        return null;
      }

      setIsGenerating(true);
      setError(null);

      // Optimistically add user message
      const userMsg: ImageGenMessage = {
        id: `temp-${Date.now()}`,
        session_id: targetSessionId,
        role: "user",
        text_content: prompt,
        created_at: new Date().toISOString(),
      };
      const optimisticMessages = [...messagesRef.current, userMsg];
      messagesRef.current = optimisticMessages;
      setMessages(optimisticMessages);

      try {
        const result = await apiClient.generateImage(targetSessionId, {
          prompt,
          ...options,
        });

        const nextMessages = [
          ...messagesRef.current.filter((m) => m.id !== userMsg.id),
          { ...userMsg, id: `user-${Date.now()}` },
          result,
        ];
        messagesRef.current = nextMessages;
        setMessages(nextMessages);

        const baseSession =
          sessionCacheRef.current[targetSessionId]
          || (currentSession?.id === targetSessionId ? currentSession : null);
        if (baseSession) {
          const updatedSession = { ...baseSession, messages: nextMessages };
          cacheSession(updatedSession);
          if (currentSession?.id === targetSessionId) {
            setCurrentSession(updatedSession);
          }
        }

        // Refresh usage after successful generation
        fetchUsage();

        return result;
      } catch (e) {
        setError(e instanceof Error ? e.message : "画像生成に失敗しました");
        // Remove optimistic message on error
        const revertedMessages = messagesRef.current.filter((m) => m.id !== userMsg.id);
        messagesRef.current = revertedMessages;
        setMessages(revertedMessages);
        return null;
      } finally {
        setIsGenerating(false);
      }
    },
    [currentSession, fetchUsage]
  );

  return {
    // State
    templates,
    sessions,
    currentSession,
    messages,
    isLoading,
    isGenerating,
    loadingSessionId,
    error,
    usage,
    // Template actions
    fetchTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    // Reference actions
    uploadReference,
    deleteReference,
    // Session actions
    fetchSessions,
    createSession,
    loadSession,
    setCurrentSession,
    updateSessionTemplate,
    // Generation
    generateImage,
    // Usage
    fetchUsage,
    // Utility
    setError,
  };
}
