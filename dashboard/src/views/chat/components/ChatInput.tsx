"use client";

import { ArrowUp, Square } from "lucide-react";
import { forwardRef, type FormEvent, type KeyboardEvent } from "react";

import type { ChatMode } from "../types";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  streaming: boolean;
  mode: ChatMode;
}

export const ChatInput = forwardRef<HTMLInputElement, ChatInputProps>(function ChatInput(
  { value, onChange, onSubmit, onStop, streaming, mode },
  ref,
) {
  const handleForm = (e: FormEvent) => {
    e.preventDefault();
    if (!value.trim() || streaming) return;
    onSubmit();
  };
  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!value.trim() || streaming) return;
      onSubmit();
    }
  };

  return (
    <div className="pt-4 border-t border-white/[0.06]">
      <form onSubmit={handleForm} className="relative">
        <div className="flex items-end gap-2 bg-[#111] border border-white/[0.06] rounded-xl px-3 py-2 focus-within:border-blue-500/30 transition-colors">
          <input
            ref={ref}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={mode === "rag" ? "Ask a question (RAG)..." : "Ask a question (Direct)..."}
            className="flex-1 bg-transparent py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none"
            disabled={streaming}
            onKeyDown={handleKey}
          />

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="flex-shrink-0 w-8 h-8 rounded-lg bg-red-500/15 border border-red-500/20 flex items-center justify-center text-red-400 hover:bg-red-500/25 transition-colors mb-0.5"
              title="Stop streaming"
            >
              <Square className="w-3.5 h-3.5" fill="currentColor" strokeWidth={0} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!value.trim()}
              className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 flex items-center justify-center text-white transition-colors disabled:cursor-not-allowed mb-0.5"
              title="Send"
            >
              <ArrowUp className="w-4 h-4" strokeWidth={2} />
            </button>
          )}
        </div>
      </form>
    </div>
  );
});
