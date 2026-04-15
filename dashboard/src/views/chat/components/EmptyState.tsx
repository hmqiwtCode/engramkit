"use client";

import { MessageSquare } from "lucide-react";

import type { ChatMode } from "../types";

export function EmptyState({ mode }: { mode: ChatMode }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-5">
        <MessageSquare className="w-6 h-6 text-blue-400" strokeWidth={1.5} />
      </div>
      <p className="text-sm text-gray-300 font-medium mb-1.5">Start a conversation</p>
      <p className="text-xs text-gray-600 max-w-sm leading-relaxed">
        {mode === "rag"
          ? "Your message seeds a hybrid search, then the agent iterates over engramkit memory and files until it can answer."
          : "Direct mode — the agent starts clean and pulls context on demand via engramkit tools."}
      </p>
    </div>
  );
}
