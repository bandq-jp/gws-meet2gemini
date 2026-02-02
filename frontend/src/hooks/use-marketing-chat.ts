"use client";

import { useState, useCallback, useRef } from "react";
import type {
  Message,
  StreamEvent,
  ToolActivityItem,
  TextActivityItem,
  AskUserActivityItem,
  PendingQuestionGroup,
  Conversation,
  MessageRecord,
  ActivityItemRecord,
} from "@/lib/marketing-types";

/**
 * Custom chat hook for marketing AI assistant.
 * Uses manual SSE parsing via fetch + ReadableStream.
 */
export function useMarketingChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<
    string | null
  >(null);
  const [pendingQuestionGroup, setPendingQuestionGroup] =
    useState<PendingQuestionGroup | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const seqRef = useRef(0);
  const assistantIdRef = useRef<string | null>(null);
  const currentTextItemIdRef = useRef<string | null>(null);
  const clientSecretRef = useRef<string | null>(null);
  const clientSecretExpiresRef = useRef<number>(0);

  // --- Token management ---

  const ensureClientSecret = useCallback(async (): Promise<string> => {
    const now = Math.floor(Date.now() / 1000);
    if (clientSecretRef.current && clientSecretExpiresRef.current > now + 5) {
      return clientSecretRef.current;
    }
    const endpoint = clientSecretRef.current
      ? "/api/marketing/chatkit/refresh"
      : "/api/marketing/chatkit/start";
    const res = await fetch(endpoint, { method: "POST" });
    if (!res.ok) throw new Error(`Token fetch failed: ${res.status}`);
    const data = await res.json();
    clientSecretRef.current = data.client_secret;
    clientSecretExpiresRef.current = now + (data.expires_in || 900);
    return data.client_secret;
  }, []);

  // --- Load existing messages ---

  const loadMessages = useCallback((msgs: Message[]) => {
    setMessages(msgs);
  }, []);

  const setConversationId = useCallback((id: string | null) => {
    setCurrentConversationId(id);
  }, []);

  /**
   * Load a conversation from the API and populate messages.
   */
  const loadConversation = useCallback(
    async (threadId: string) => {
      const token = await ensureClientSecret();
      const res = await fetch(`/api/marketing/chat/threads/${threadId}`, {
        headers: { "x-marketing-client-secret": token },
      });
      if (!res.ok) return;
      const data = await res.json();
      setCurrentConversationId(threadId);

      // Convert DB records to Message[]
      const converted: Message[] = (data.messages || []).map(
        (m: MessageRecord) => {
          let textContent = "";
          const raw = m.content;
          // content is JSONB — may arrive as object (dict) or string
          if (typeof raw === "object" && raw !== null) {
            if ("text" in (raw as Record<string, unknown>))
              textContent = (raw as Record<string, unknown>).text as string;
            else if (Array.isArray(raw)) {
              textContent = (raw as Record<string, unknown>[])
                .filter((item) => item.type === "text")
                .map((item) => (item.text as string) || "")
                .join("\n");
            } else {
              textContent = JSON.stringify(raw);
            }
          } else if (typeof raw === "string") {
            // Legacy or plain text
            try {
              const parsed = JSON.parse(raw);
              if (typeof parsed === "object" && parsed !== null && "text" in parsed)
                textContent = parsed.text;
              else textContent = raw;
            } catch {
              textContent = raw;
            }
          }

          // Convert activity_items records
          const activityItems = m.activity_items
            ? m.activity_items.map((ai: ActivityItemRecord) => ({
                id: crypto.randomUUID(),
                ...ai,
              }))
            : undefined;

          return {
            id: m.id,
            role: m.role as "user" | "assistant",
            content: textContent,
            activityItems,
            isStreaming: false,
          };
        }
      );
      setMessages(converted);
      return data;
    },
    [ensureClientSecret]
  );

  // --- Respond to ask_user questions ---

  const respondToQuestions = useCallback(
    async (groupId: string, responses: Record<string, string>) => {
      const token = await ensureClientSecret();

      // Mark the ask_user activity item as responded
      const currentAssistantId = assistantIdRef.current;
      if (currentAssistantId) {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== currentAssistantId) return m;
            const items = (m.activityItems || []).map((it) =>
              it.kind === "ask_user" &&
              (it as AskUserActivityItem).groupId === groupId
                ? ({ ...it, responses } as AskUserActivityItem)
                : it
            );
            return { ...m, activityItems: items };
          })
        );
      }

      setPendingQuestionGroup(null);

      try {
        await fetch("/api/marketing/chat/respond", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-marketing-client-secret": token,
          },
          body: JSON.stringify({ group_id: groupId, responses }),
        });
      } catch (err) {
        console.error("Failed to respond to questions:", err);
      }
    },
    [ensureClientSecret]
  );

  // --- Send message ---

  const sendMessage = useCallback(
    async (content: string, modelAssetId: string = "standard") => {
      seqRef.current = 0;
      currentTextItemIdRef.current = null;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);

      const assistantId = crypto.randomUUID();
      assistantIdRef.current = assistantId;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          isStreaming: true,
          activityItems: [],
        },
      ]);

      const token = await ensureClientSecret();
      abortRef.current = new AbortController();

      try {
        const response = await fetch("/api/marketing/chat/stream", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-marketing-client-secret": token,
            "x-model-asset-id": modelAssetId,
          },
          body: JSON.stringify({
            message: content,
            conversation_id: currentConversationId,
            model_asset_id: modelAssetId,
          }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            let event: StreamEvent;
            try {
              event = JSON.parse(line.slice(6));
            } catch {
              continue;
            }

            if (event.type === "text_delta" && event.content) {
              if (!currentTextItemIdRef.current) {
                const textId = crypto.randomUUID();
                const seq = ++seqRef.current;
                currentTextItemIdRef.current = textId;
                const newTextItem: TextActivityItem = {
                  id: textId,
                  kind: "text",
                  sequence: seq,
                  content: event.content,
                };
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          content: m.content + event.content,
                          activityItems: [
                            ...(m.activityItems || []),
                            newTextItem,
                          ],
                        }
                      : m
                  )
                );
              } else {
                const textId = currentTextItemIdRef.current;
                setMessages((prev) =>
                  prev.map((m) => {
                    if (m.id !== assistantId) return m;
                    const items = (m.activityItems || []).map((it) =>
                      it.id === textId
                        ? ({
                            ...it,
                            content:
                              (it as TextActivityItem).content + event.content,
                          } as TextActivityItem)
                        : it
                    );
                    return {
                      ...m,
                      content: m.content + event.content,
                      activityItems: items,
                    };
                  })
                );
              }
            } else if (event.type === "response_created") {
              currentTextItemIdRef.current = null;
            } else if (event.type === "tool_call") {
              currentTextItemIdRef.current = null;
              const seq = ++seqRef.current;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        activityItems: [
                          ...(m.activityItems || []),
                          {
                            id: crypto.randomUUID(),
                            kind: "tool" as const,
                            sequence: seq,
                            name: event.name || "unknown",
                            call_id: event.call_id,
                            arguments: event.arguments,
                            output: undefined,
                          },
                        ],
                      }
                    : m
                )
              );
            } else if (event.type === "tool_result") {
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  const items = [...(m.activityItems || [])];
                  const idx = event.call_id
                    ? items.findIndex(
                        (it) =>
                          it.kind === "tool" &&
                          (it as ToolActivityItem).call_id === event.call_id &&
                          !(it as ToolActivityItem).output
                      )
                    : items.findIndex(
                        (it) =>
                          it.kind === "tool" &&
                          !(it as ToolActivityItem).output
                      );
                  if (idx !== -1) {
                    items[idx] = {
                      ...items[idx],
                      output: event.output,
                    } as ToolActivityItem;
                  }
                  return { ...m, activityItems: items };
                })
              );
            } else if (event.type === "reasoning" && event.content) {
              currentTextItemIdRef.current = null;
              const seq = ++seqRef.current;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        activityItems: [
                          ...(m.activityItems || []),
                          {
                            id: crypto.randomUUID(),
                            kind: "reasoning" as const,
                            sequence: seq,
                            content: event.content!,
                          },
                        ],
                      }
                    : m
                )
              );
            } else if (
              event.type === "ask_user" &&
              event.group_id &&
              event.questions
            ) {
              currentTextItemIdRef.current = null;
              const seq = ++seqRef.current;
              const askItem: AskUserActivityItem = {
                id: crypto.randomUUID(),
                kind: "ask_user",
                sequence: seq,
                groupId: event.group_id,
                questions: event.questions,
              };
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        activityItems: [
                          ...(m.activityItems || []),
                          askItem,
                        ],
                      }
                    : m
                )
              );
              setPendingQuestionGroup({
                groupId: event.group_id,
                questions: event.questions,
              });
            } else if (event.type === "keepalive") {
              // Keepalive events are informational only, no state update needed
            } else if (event.type === "done") {
              currentTextItemIdRef.current = null;
              if (event.conversation_id) {
                setCurrentConversationId(event.conversation_id);
                window.history.replaceState(
                  {},
                  "",
                  `/marketing/${event.conversation_id}`
                );
              }
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  const items = (m.activityItems || []).map((it) =>
                    it.kind === "tool" && !(it as ToolActivityItem).output
                      ? ({
                          ...it,
                          output: "(completed)",
                        } as ToolActivityItem)
                      : it
                  );
                  return {
                    ...m,
                    isStreaming: false,
                    activityItems: items,
                  };
                })
              );
              setPendingQuestionGroup(null);
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content:
                          m.content +
                          `\n\nエラーが発生しました: ${event.message}`,
                        isStreaming: false,
                      }
                    : m
                )
              );
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: "接続エラーが発生しました。再度お試しください。",
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      } finally {
        setIsStreaming(false);
        assistantIdRef.current = null;
      }
    },
    [currentConversationId, ensureClientSecret]
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentConversationId(null);
    setPendingQuestionGroup(null);
    window.history.replaceState({}, "", "/marketing");
  }, []);

  return {
    messages,
    sendMessage,
    isStreaming,
    stopStreaming,
    clearMessages,
    loadMessages,
    loadConversation,
    currentConversationId,
    setConversationId,
    pendingQuestionGroup,
    respondToQuestions,
    ensureClientSecret,
  };
}
