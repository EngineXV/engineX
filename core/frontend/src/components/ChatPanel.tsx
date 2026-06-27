import { useEffect, useRef } from "react";
import ChartBlock, { type ChartBlockProps } from "./ChartBlock";
import { IconSend } from "./Icons";

export interface ChatLine {
  id: string;
  role: "user" | "agent" | "system";
  text: string;
  timestamp?: string;
  chart?: ChartBlockProps;
}

interface ChatPanelProps {
  lines: ChatLine[];
  streamingText: string;
  input: string;
  busy: boolean;
  waitingForInput: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
}

function formatTime(iso?: string) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function ChatPanel({
  lines,
  streamingText,
  input,
  busy,
  waitingForInput,
  onInputChange,
  onSend,
}: ChatPanelProps) {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines, streamingText]);

  return (
    <div className="chat-panel">
      <div className="chat-log" ref={logRef}>
        {lines.length === 0 && !streamingText && (
          <div className="chat-empty">
            Send a message to start the agent, or wait for the intro prompt.
          </div>
        )}
        {lines.map((line) => (
          <div key={line.id} className={`chat-row chat-${line.role}`}>
            {line.role === "agent" && <div className="chat-avatar agent">AI</div>}
            {line.role === "user" && <div className="chat-avatar user">You</div>}
            <div className="chat-bubble-wrap">
              {line.role === "user" ? (
                <div className="chat-bubble user">{line.text}</div>
              ) : line.role === "system" ? (
                <div className="chat-system">{line.text}</div>
              ) : (
                <div className="chat-bubble agent">
                  {line.chart ? <ChartBlock {...line.chart} /> : null}
                  {line.text}
                </div>
              )}
              {line.timestamp && <div className="chat-time">{formatTime(line.timestamp)}</div>}
            </div>
          </div>
        ))}
        {streamingText && (
          <div className="chat-row chat-agent">
            <div className="chat-avatar agent">AI</div>
            <div className="chat-bubble-wrap">
              <div className="chat-bubble agent streaming">{streamingText}</div>
            </div>
          </div>
        )}
        {busy && !streamingText && (
          <div className="chat-row chat-agent">
            <div className="chat-avatar agent">AI</div>
            <div className="typing-indicator"><span /><span /><span /></div>
          </div>
        )}
      </div>

      <div className="chat-composer">
        <textarea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder={
            waitingForInput
              ? "The agent is waiting for your reply…"
              : "Message the agent — Enter to send, Shift+Enter for newline"
          }
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
        />
        <button
          type="button"
          className="send-btn"
          disabled={busy || !input.trim()}
          onClick={onSend}
          title="Send message"
          aria-label="Send message"
        >
          <IconSend size={18} />
        </button>
      </div>
    </div>
  );
}
