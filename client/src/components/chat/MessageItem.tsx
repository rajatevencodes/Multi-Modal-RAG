import { User, Bot } from "lucide-react";
import Markdown from "react-markdown";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  created_at: string;
  chat_id: string;
  clerk_id: string;
  citations?: Array<{
    filename: string;
    page: number;
  }>;
}

interface MessageItemProps {
  message: Message;
  onFeedback?: (messageId: string, type: "like" | "dislike") => void;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";
  const time = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} group`}>
      <div className={`max-w-[85%] ${isUser ? "ml-12" : "mr-12"} relative`}>
        {/* Avatar & Message Container */}
        <div className="flex items-start gap-3">
          {/* Avatar - Only show for assistant */}
          {!isUser && (
            <div className="shrink-0 w-7 h-7 bg-[#252525] border border-gray-700 rounded-lg flex items-center justify-center mt-1">
              <Bot size={14} className="text-gray-400" />
            </div>
          )}

          {/* Message Bubble */}
          <div
            className={`rounded-lg p-4 border transition-colors ${
              isUser
                ? "bg-white text-gray-900 border-gray-300"
                : "bg-[#202020] text-gray-200 border-gray-800 hover:border-gray-700"
            }`}
          >
            <div
              className={`markdown-content ${
                isUser ? "text-gray-900" : "text-gray-200"
              }`}
            >
              <Markdown>{message.content}</Markdown>
            </div>
          </div>

          {/* User Avatar - Only show for user */}
          {isUser && (
            <div className="shrink-0 w-7 h-7 bg-[#252525] border border-gray-700 rounded-lg flex items-center justify-center mt-1">
              <User size={14} className="text-gray-400" />
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div
          className={`flex items-center gap-2 mt-2 px-1 ${
            isUser ? "justify-end" : "justify-start ml-10"
          }`}
        >
          <span className="text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity">
            {time}
          </span>
          {!isUser && (
            <div className="w-1 h-1 bg-gray-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
          )}
        </div>
      </div>
    </div>
  );
}
