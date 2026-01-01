"use client";

import { use, useEffect, useState, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { ChatWithMessages, Message } from "@/types";
import { apiClient } from "@/lib/index";
import { MessageFeedbackModal } from "@/components/chat/MessageFeedbackModel";
import toast from "react-hot-toast";
import { NotFound } from "@/components/ui/NotFound";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_SERVER_URL || "http://localhost:8000";

interface ProjectChatPageProps {
  params: Promise<{
    id: string;
    chatId: string;
  }>;
}

export default function ProjectChatPage({ params }: ProjectChatPageProps) {
  const { id: projectId, chatId } = use(params);

  const [currentChatData, setCurrentChatData] =
    useState<ChatWithMessages | null>(null);

  const [isLoadingChatData, setIsLoadingChatData] = useState(true);

  const [sendMessageError, setSendMessageError] = useState<string | null>(null);
  const [isMessageSending, setIsMessageSending] = useState(false);

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState("");
  const [agentStatus, setAgentStatus] = useState("");

  // Ref to abort streaming if needed
  const abortControllerRef = useRef<AbortController | null>(null);

  const [feedbackModal, setFeedbackModal] = useState<{
    messageId: string;
    type: "like" | "dislike";
  } | null>(null);

  const { getToken, userId } = useAuth();

  /*
   ! Business Logic Functions - Core operations for this project:
   * handleSendMessage: Send a message to the chat
  */
  // Send message function with streaming
  const handleSendMessage = async (content: string) => {
    if (!currentChatData || !userId) {
      setSendMessageError("Chat or user not found");
      return;
    }

    try {
      setSendMessageError(null);
      setIsMessageSending(true);

      // Streaming init
      setIsStreaming(true);
      setStreamingMessage("");
      setAgentStatus("");
      abortControllerRef.current = new AbortController();

      // Create optimistic user message to show immediately
      const optimisticUserMessage: Message = {
        id: `temp-${Date.now()}`,
        chat_id: currentChatData.id,
        content: content,
        role: "user",
        clerk_id: userId,
        created_at: new Date().toISOString(),
        citations: [],
      };

      // Add user message to UI immediately
      setCurrentChatData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: [...prev.messages, optimisticUserMessage],
        };
      });

      const token = await getToken();

      // Use fetch for streaming
      const response = await fetch(
        `${API_BASE_URL}/api/chat/${projectId}/chats/${currentChatData.id}/messages/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const events = buffer.split("\n\n");
        // Keep the last incomplete part in buffer
        buffer = events.pop() || "";

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          const lines = eventBlock.split("\n");
          let eventType = "";
          let dataStr = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.slice(6);
            }
          }

          if (!eventType || !dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (eventType === "token") {
              setStreamingMessage((prev) => prev + data.content);
            } else if (eventType === "status") {
              setAgentStatus(data.status);
            } else if (eventType === "error") {
              throw new Error(data.message || "Unknown error");
            } else if (eventType === "done") {
              setCurrentChatData((prev) => {
                if (!prev) return prev;
                if (data.aiMessage && data.userMessage) {
                  return {
                    ...prev,
                    messages: [
                      ...prev.messages.filter(
                        (m) => m.id !== optimisticUserMessage.id
                      ),
                      data.userMessage,
                      data.aiMessage,
                    ],
                  };
                }
                return prev;
              });
            }
          } catch (e) {
            console.warn("Failed to parse SSE message", e);
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }

      const errorMessage =
        err instanceof Error ? err.message : "Failed to send message";
      setSendMessageError(errorMessage);
      toast.error(errorMessage);

      // Remove optimistic message on error
      setCurrentChatData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: prev.messages.filter((msg) => !msg.id.startsWith("temp-")),
        };
      });
    } finally {
      setIsMessageSending(false);
      setIsStreaming(false);
      setStreamingMessage("");
      setAgentStatus("");
      abortControllerRef.current = null;
    }
  };

  /*
   ! User Interaction Functions:
   * handleFeedbackOpen: Open the feedback modal
   * handleFeedbackSubmit: Submit the feedback
  */

  const handleFeedbackOpen = (messageId: string, type: "like" | "dislike") => {
    setFeedbackModal({ messageId, type });
  };

  const handleFeedbackSubmit = async (feedback: {
    rating: "like" | "dislike";
    comment?: string;
    category?: string;
  }) => {
    if (!userId || !feedbackModal) return;

    try {
      const token = await getToken();

      await apiClient.post(
        "/api/feedback",
        {
          message_id: feedbackModal.messageId,
          rating: feedback.rating,
          comment: feedback.comment,
          category: feedback.category,
        },
        token
      );

      toast.success("Thanks for your feedback!");
    } catch {
      toast.error("Failed to submit feedback. Please try again.");
    } finally {
      setFeedbackModal(null);
    }
  };

  useEffect(() => {
    const loadChat = async () => {
      if (!userId) return;

      setIsLoadingChatData(true);

      try {
        const token = await getToken();
        const result = await apiClient.get(`/api/chat/${chatId}`, token);
        const chatData = result.data;

        setCurrentChatData(chatData);
        toast.success("Chat loaded");
      } catch {
        toast.error("Failed to load chat. Please try again.");
      } finally {
        setIsLoadingChatData(false);
      }
    };

    loadChat();
  }, [userId, chatId, getToken]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  if (isLoadingChatData) {
    return <LoadingSpinner message="Loading chat..." />;
  }

  if (!currentChatData) {
    return <NotFound message="Chat not found" />;
  }

  return (
    <>
      <ChatInterface
        chat={currentChatData}
        projectId={projectId}
        onSendMessage={handleSendMessage}
        onFeedback={handleFeedbackOpen}
        isLoading={isMessageSending}
        error={sendMessageError}
        onDismissError={() => setSendMessageError(null)}
        isStreaming={isStreaming}
        streamingMessage={streamingMessage}
        agentStatus={agentStatus}
      />
      <MessageFeedbackModal
        isOpen={!!feedbackModal}
        feedbackType={feedbackModal?.type}
        onSubmit={handleFeedbackSubmit}
        onCancel={() => setFeedbackModal(null)}
      />
    </>
  );
}
