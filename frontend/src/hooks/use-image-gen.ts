"use client";

import { useState, useCallback } from "react";
import {
  apiClient,
  type ImageGenTemplate,
  type ImageGenSession,
  type ImageGenMessage,
} from "@/lib/api";

export function useImageGen() {
  const [templates, setTemplates] = useState<ImageGenTemplate[]>([]);
  const [sessions, setSessions] = useState<ImageGenSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ImageGenSession | null>(null);
  const [messages, setMessages] = useState<ImageGenMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      setSessions((prev) => [result, ...prev]);
      setCurrentSession(result);
      setMessages([]);
      return result;
    },
    []
  );

  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    try {
      const session = await apiClient.getImageGenSession(sessionId);
      setCurrentSession(session);
      setMessages(session.messages || []);
      return session;
    } catch (e) {
      setError(e instanceof Error ? e.message : "セッションの読み込みに失敗しました");
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Generation ──

  const generateImage = useCallback(
    async (
      prompt: string,
      options?: { aspect_ratio?: string; image_size?: string }
    ) => {
      if (!currentSession) {
        setError("セッションが選択されていません");
        return null;
      }

      setIsGenerating(true);
      setError(null);

      // Optimistically add user message
      const userMsg: ImageGenMessage = {
        id: `temp-${Date.now()}`,
        session_id: currentSession.id,
        role: "user",
        text_content: prompt,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const result = await apiClient.generateImage(currentSession.id, {
          prompt,
          ...options,
        });

        // Replace optimistic user message and add assistant message
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== userMsg.id);
          // The API returns the assistant message, but we also need the saved user message
          // Re-fetch full session messages for accuracy
          return [...filtered, { ...userMsg, id: `user-${Date.now()}` }, result];
        });

        return result;
      } catch (e) {
        setError(e instanceof Error ? e.message : "画像生成に失敗しました");
        // Remove optimistic message on error
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
        return null;
      } finally {
        setIsGenerating(false);
      }
    },
    [currentSession]
  );

  return {
    // State
    templates,
    sessions,
    currentSession,
    messages,
    isLoading,
    isGenerating,
    error,
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
    // Generation
    generateImage,
    // Utility
    setError,
  };
}
