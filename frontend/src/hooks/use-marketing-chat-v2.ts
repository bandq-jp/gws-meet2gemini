"use client";

/**
 * Native Marketing Chat Hook
 *
 * Replaces ChatKit with direct SSE streaming to OpenAI Agents SDK.
 * Handles stream events, activity items, and conversation state.
 */

import { useCallback, useRef, useState, useEffect } from "react";
import type {
  Message,
  ActivityItem,
  TextActivityItem,
  ToolActivityItem,
  ReasoningActivityItem,
  SubAgentActivityItem,
  ChartActivityItem,
  StreamEvent,
  ChatStreamRequest,
  ModelAsset,
} from "@/lib/marketing/types";

// Token management
type TokenState = {
  secret: string | null;
  expiresAt: number;
};

export type UseMarketingChatOptions = {
  initialConversationId?: string | null;
  onConversationChange?: (conversationId: string | null) => void;
  onError?: (error: string) => void;
};

export type UseMarketingChatReturn = {
  messages: Message[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  setConversationId: (id: string | null) => void;
  loadConversation: (id: string) => Promise<void>;
};

// Generate unique ID
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export function useMarketingChat(
  options: UseMarketingChatOptions = {}
): UseMarketingChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(
    options.initialConversationId ?? null
  );

  // Pending conversation ID for deferred callback (fixes React setState-during-render)
  const [pendingConversationId, setPendingConversationId] = useState<string | null | undefined>(undefined);

  // Track if initial conversation has been loaded
  const initialLoadDoneRef = useRef(false);

  // Context items for multi-turn conversation
  const contextItemsRef = useRef<Array<Record<string, unknown>> | null>(null);

  // Token management
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });

  // Sequence counter for activity items
  const seqRef = useRef(0);

  // Current text item ID for accumulating text deltas
  const currentTextIdRef = useRef<string | null>(null);

  // Abort controller for cancelling streams
  const abortControllerRef = useRef<AbortController | null>(null);

  // Refs for options callbacks
  const onConversationChangeRef = useRef(options.onConversationChange);
  const onErrorRef = useRef(options.onError);

  useEffect(() => {
    onConversationChangeRef.current = options.onConversationChange;
    onErrorRef.current = options.onError;
  }, [options.onConversationChange, options.onError]);

  // Deferred callback execution (fixes React setState-during-render)
  useEffect(() => {
    if (pendingConversationId !== undefined) {
      onConversationChangeRef.current?.(pendingConversationId);
      setPendingConversationId(undefined);
    }
  }, [pendingConversationId]);

  // Ensure we have a valid token
  const ensureToken = useCallback(async (): Promise<string> => {
    const now = Date.now();
    if (tokenRef.current.secret && tokenRef.current.expiresAt - 5_000 > now) {
      return tokenRef.current.secret;
    }

    const hasSecret = Boolean(tokenRef.current.secret);
    const endpoint = hasSecret
      ? "/api/marketing-v2/chatkit/refresh"
      : "/api/marketing-v2/chatkit/start";

    const response = await fetch(endpoint, {
      method: "POST",
      body: hasSecret
        ? JSON.stringify({ currentClientSecret: tokenRef.current.secret })
        : undefined,
      headers: hasSecret ? { "Content-Type": "application/json" } : undefined,
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail?.error || "Failed to fetch client secret");
    }

    const data = await response.json();
    tokenRef.current = {
      secret: data.client_secret,
      expiresAt: now + (data.expires_in ?? 900) * 1000,
    };

    return tokenRef.current.secret!;
  }, []);

  // Process stream event and update messages
  const processEvent = useCallback(
    (event: StreamEvent, assistantMessageId: string) => {
      setMessages((prev) => {
        const updated = [...prev];
        const assistantIdx = updated.findIndex(
          (m) => m.id === assistantMessageId
        );
        if (assistantIdx === -1) return prev;

        const assistant = { ...updated[assistantIdx] };
        const items = [...assistant.activityItems];

        switch (event.type) {
          case "text_delta": {
            // Accumulate text into current text item or create new one
            if (currentTextIdRef.current) {
              const textIdx = items.findIndex(
                (i) => i.id === currentTextIdRef.current
              );
              if (textIdx !== -1) {
                // Update existing text item
                const textItem = items[textIdx] as TextActivityItem;
                items[textIdx] = {
                  ...textItem,
                  content: textItem.content + event.content,
                };
              } else {
                // Item not found (edge case) - create new item to prevent silent no-op
                const newId = generateId();
                currentTextIdRef.current = newId;
                items.push({
                  id: newId,
                  kind: "text",
                  sequence: seqRef.current++,
                  content: event.content,
                } as TextActivityItem);
              }
            } else {
              // Create new text item
              const newId = generateId();
              currentTextIdRef.current = newId;
              items.push({
                id: newId,
                kind: "text",
                sequence: seqRef.current++,
                content: event.content,
              } as TextActivityItem);
            }
            // Update assistant content for display
            assistant.content =
              items
                .filter((i) => i.kind === "text")
                .map((i) => (i as TextActivityItem).content)
                .join("") || "";
            break;
          }

          case "response_created": {
            // New response boundary - reset text accumulation
            currentTextIdRef.current = null;
            break;
          }

          case "tool_call": {
            // Reset text accumulation when tool call starts
            currentTextIdRef.current = null;
            items.push({
              id: event.call_id || generateId(),
              kind: "tool",
              sequence: seqRef.current++,
              name: event.name || "unknown",
              callId: event.call_id,
              arguments: event.arguments,
              // output: undefined means "running", output: string means "complete"
            } as ToolActivityItem);
            break;
          }

          case "tool_result": {
            // Find matching tool call - search from end (most recent first)
            // Match by call_id AND no output yet (to handle duplicate call_ids)
            let toolIdx = -1;
            if (event.call_id) {
              // Search backwards for matching call_id without output
              for (let i = items.length - 1; i >= 0; i--) {
                const item = items[i];
                if (
                  item.kind === "tool" &&
                  (item as ToolActivityItem).callId === event.call_id &&
                  !(item as ToolActivityItem).output
                ) {
                  toolIdx = i;
                  break;
                }
              }
            }
            // Fallback: find any tool without output
            if (toolIdx === -1) {
              for (let i = items.length - 1; i >= 0; i--) {
                const item = items[i];
                if (item.kind === "tool" && !(item as ToolActivityItem).output) {
                  toolIdx = i;
                  break;
                }
              }
            }

            if (toolIdx !== -1) {
              const toolItem = items[toolIdx] as ToolActivityItem;
              items[toolIdx] = {
                ...toolItem,
                output: event.output || "(completed)",
              };
            }
            break;
          }

          case "reasoning": {
            items.push({
              id: generateId(),
              kind: "reasoning",
              sequence: seqRef.current++,
              content: event.content,
            } as ReasoningActivityItem);
            break;
          }

          case "chart": {
            items.push({
              id: generateId(),
              kind: "chart",
              sequence: seqRef.current++,
              spec: event.spec,
            } as ChartActivityItem);
            break;
          }

          case "sub_agent_event": {
            // Find existing sub-agent card for this agent (running or not)
            const existingIdx = items.findIndex(
              (i) =>
                i.kind === "sub_agent" &&
                (i as SubAgentActivityItem).agent === event.agent
            );

            if (event.event_type === "started") {
              // Sub-agent started - create card immediately if not exists
              if (existingIdx === -1) {
                items.push({
                  id: generateId(),
                  kind: "sub_agent",
                  sequence: seqRef.current++,
                  agent: event.agent,
                  eventType: event.event_type,
                  data: event.data,
                  isRunning: true,
                  toolCalls: [],
                } as SubAgentActivityItem);
              } else {
                // Mark as running if exists
                const subItem = items[existingIdx] as SubAgentActivityItem;
                items[existingIdx] = {
                  ...subItem,
                  isRunning: true,
                };
              }
            } else if (event.event_type === "tool_called") {
              const toolName = event.data?.tool_name || "unknown";
              const callId = event.data?.call_id || generateId();

              if (existingIdx !== -1) {
                // Update existing sub-agent card with new tool call
                const subItem = items[existingIdx] as SubAgentActivityItem;
                const toolCalls = subItem.toolCalls || [];
                items[existingIdx] = {
                  ...subItem,
                  eventType: event.event_type,
                  isRunning: true,
                  toolCalls: [
                    ...toolCalls,
                    { callId, toolName, isComplete: false },
                  ],
                };
              } else {
                // Create new sub-agent card
                items.push({
                  id: generateId(),
                  kind: "sub_agent",
                  sequence: seqRef.current++,
                  agent: event.agent,
                  eventType: event.event_type,
                  data: event.data,
                  isRunning: true,
                  toolCalls: [{ callId, toolName, isComplete: false }],
                } as SubAgentActivityItem);
              }
            } else if (event.event_type === "tool_output") {
              // Mark specific tool call as complete
              if (existingIdx !== -1) {
                const subItem = items[existingIdx] as SubAgentActivityItem;
                const callId = event.data?.call_id;
                const toolCalls = (subItem.toolCalls || []).map((tc) =>
                  tc.callId === callId ? { ...tc, isComplete: true } : tc
                );
                items[existingIdx] = {
                  ...subItem,
                  eventType: event.event_type,
                  toolCalls,
                  outputPreview: event.data?.output_preview || subItem.outputPreview,
                };
              }
            } else if (event.event_type === "reasoning") {
              // Sub-agent reasoning - update or create card
              const reasoningContent = event.data?.content || "";
              if (existingIdx !== -1) {
                const subItem = items[existingIdx] as SubAgentActivityItem;
                items[existingIdx] = {
                  ...subItem,
                  eventType: event.event_type,
                  isRunning: true,
                  reasoningContent: (subItem.reasoningContent || "") + "\n\n" + reasoningContent,
                };
              } else {
                items.push({
                  id: generateId(),
                  kind: "sub_agent",
                  sequence: seqRef.current++,
                  agent: event.agent,
                  eventType: event.event_type,
                  data: event.data,
                  isRunning: true,
                  reasoningContent,
                } as SubAgentActivityItem);
              }
            } else if (event.event_type === "text_delta") {
              // Sub-agent generating output - keep card but show progress
              if (existingIdx !== -1) {
                const subItem = items[existingIdx] as SubAgentActivityItem;
                items[existingIdx] = {
                  ...subItem,
                  eventType: event.event_type,
                  // Still running while generating text
                };
              }
            } else if (event.event_type === "message_output") {
              // Sub-agent finished - mark as complete
              if (existingIdx !== -1) {
                const subItem = items[existingIdx] as SubAgentActivityItem;
                items[existingIdx] = {
                  ...subItem,
                  eventType: event.event_type,
                  isRunning: false,
                };
              }
            }
            break;
          }

          case "agent_updated": {
            // Agent switch - could add visual indicator
            break;
          }

          case "progress": {
            // Keepalive - no UI update needed
            break;
          }

          case "_context_items": {
            // Save context for next turn
            contextItemsRef.current = event.items;
            break;
          }

          case "done": {
            // Update conversation ID (defer callback to avoid setState-during-render)
            if (event.conversation_id) {
              setConversationId(event.conversation_id);
              setPendingConversationId(event.conversation_id);
            }

            // Safety net: Mark any unfinished tools and sub-agents as complete
            // This handles cases where tool_result events are missing
            for (let i = 0; i < items.length; i++) {
              const item = items[i];
              if (item.kind === "tool") {
                const toolItem = item as ToolActivityItem;
                if (!toolItem.output) {
                  items[i] = { ...toolItem, output: "(completed)" };
                }
              } else if (item.kind === "sub_agent") {
                const subItem = item as SubAgentActivityItem;
                if (subItem.isRunning) {
                  // Mark all sub-agent tool calls as complete
                  const completedToolCalls = (subItem.toolCalls || []).map((tc) =>
                    tc.isComplete ? tc : { ...tc, isComplete: true }
                  );
                  items[i] = {
                    ...subItem,
                    isRunning: false,
                    toolCalls: completedToolCalls,
                  };
                }
              }
            }
            break;
          }

          case "error": {
            setError(event.message);
            onErrorRef.current?.(event.message);
            break;
          }
        }

        assistant.activityItems = items;
        updated[assistantIdx] = assistant;
        return updated;
      });
    },
    []
  );

  // Send message and start streaming
  const sendMessage = useCallback(
    async (content: string) => {
      if (isStreaming) return;
      if (!content.trim()) return;

      setError(null);
      setIsStreaming(true);

      // Reset sequence and text tracking for new message
      seqRef.current = 0;
      currentTextIdRef.current = null;

      // Create user message
      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content,
        activityItems: [],
        isStreaming: false,
        createdAt: new Date(),
      };

      // Create assistant placeholder
      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        activityItems: [],
        isStreaming: true,
        createdAt: new Date(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      try {
        const token = await ensureToken();

        // Create abort controller
        abortControllerRef.current = new AbortController();

        // Build request
        const requestBody: ChatStreamRequest = {
          message: content,
          conversation_id: conversationId,
          context_items: contextItemsRef.current,
        };

        const response = await fetch("/api/marketing-v2/chat/stream", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-marketing-client-secret": token,
          },
          body: JSON.stringify(requestBody),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        // Read SSE stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

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
            try {
              const event: StreamEvent = JSON.parse(line.slice(6));
              // Debug logging for sub-agent events
              if (event.type === "sub_agent_event") {
                console.log("[Sub-agent event]", event);
              }
              processEvent(event, assistantMessage.id);
            } catch (parseError) {
              console.warn("Failed to parse SSE event:", line, parseError);
            }
          }
        }

        // Mark assistant message as complete
        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.findIndex((m) => m.id === assistantMessage.id);
          if (idx !== -1) {
            updated[idx] = { ...updated[idx], isStreaming: false };
          }
          return updated;
        });
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          // Cancelled by user
          setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === assistantMessage.id);
            if (idx !== -1) {
              updated[idx] = { ...updated[idx], isStreaming: false };
            }
            return updated;
          });
        } else {
          const message = err instanceof Error ? err.message : "Unknown error";
          setError(message);
          onErrorRef.current?.(message);

          // Update assistant message with error
          setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === assistantMessage.id);
            if (idx !== -1) {
              updated[idx] = {
                ...updated[idx],
                content: `Error: ${message}`,
                isStreaming: false,
              };
            }
            return updated;
          });
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [isStreaming, conversationId, ensureToken, processEvent]
  );

  // Clear messages and reset state
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setConversationId(null);
    contextItemsRef.current = null;
    seqRef.current = 0;
    currentTextIdRef.current = null;

    // Cancel any ongoing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Defer callback to avoid setState-during-render
    setPendingConversationId(null);
  }, []);

  // Update conversation ID
  const handleSetConversationId = useCallback((id: string | null) => {
    setConversationId(id);
    // Defer callback to avoid setState-during-render
    setPendingConversationId(id);
  }, []);

  // Load conversation from DB
  const loadConversation = useCallback(
    async (id: string) => {
      if (!id) return;

      setIsLoading(true);
      setError(null);

      try {
        const token = await ensureToken();

        const response = await fetch(`/api/marketing-v2/threads/${id}`, {
          headers: {
            "x-marketing-client-secret": token,
          },
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Conversation not found");
          }
          if (response.status === 403) {
            throw new Error("Access denied");
          }
          throw new Error(`Failed to load conversation: ${response.status}`);
        }

        const data = await response.json();

        // Restore messages with activity items
        const restoredMessages: Message[] = (data.messages || []).map(
          (msg: {
            id: string;
            role: string;
            content: string;
            activity_items?: ActivityItem[];
            created_at?: string;
          }) => {
            // Restore activity items with new IDs, sorted by sequence
            const activityItems: ActivityItem[] = (msg.activity_items || [])
              .map((item: ActivityItem, idx: number) => ({
                ...item,
                id: item.id || generateId(),
                sequence: item.sequence ?? idx,
              }))
              .sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));

            return {
              id: msg.id,
              role: msg.role as "user" | "assistant",
              content: msg.content || "",
              activityItems,
              isStreaming: false,
              createdAt: msg.created_at ? new Date(msg.created_at) : new Date(),
            };
          }
        );

        setMessages(restoredMessages);
        setConversationId(id);

        // Restore context items for next turn
        if (data.context_items) {
          contextItemsRef.current = data.context_items;
        }

        // Defer callback to avoid setState-during-render
        setPendingConversationId(id);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load conversation";
        setError(message);
        onErrorRef.current?.(message);
      } finally {
        setIsLoading(false);
      }
    },
    [ensureToken]
  );

  // Auto-load initial conversation
  useEffect(() => {
    if (
      options.initialConversationId &&
      !initialLoadDoneRef.current &&
      messages.length === 0
    ) {
      initialLoadDoneRef.current = true;
      loadConversation(options.initialConversationId);
    }
  }, [options.initialConversationId, messages.length, loadConversation]);

  return {
    messages,
    isStreaming,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearMessages,
    setConversationId: handleSetConversationId,
    loadConversation,
  };
}
