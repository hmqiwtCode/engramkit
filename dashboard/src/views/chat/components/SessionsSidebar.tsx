"use client";

import { formatDistanceToNowStrict } from "date-fns";
import { X } from "lucide-react";
import type { MouseEvent } from "react";

import type { ChatSession } from "../types";

interface SessionsSidebarProps {
  sessions: ChatSession[];
  activeId: string;
  onCreate: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
}

export function SessionsSidebar({
  sessions,
  activeId,
  onCreate,
  onSwitch,
  onDelete,
}: SessionsSidebarProps) {
  return (
    <div className="w-64 flex-shrink-0 border-r border-white/[0.06] flex flex-col bg-[#0c0c0c]">
      <div className="flex items-center justify-between px-3 py-3 border-b border-white/[0.06]">
        <span className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">
          Chat History
        </span>
        <button
          onClick={onCreate}
          className="text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
        >
          + New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {[...sessions].reverse().map((s) => (
          <SessionRow
            key={s.id}
            session={s}
            active={s.id === activeId}
            onClick={() => onSwitch(s.id)}
            onDelete={(e) => {
              e.stopPropagation();
              onDelete(s.id);
            }}
          />
        ))}
      </div>
    </div>
  );
}

function SessionRow({
  session,
  active,
  onClick,
  onDelete,
}: {
  session: ChatSession;
  active: boolean;
  onClick: () => void;
  onDelete: (e: MouseEvent<HTMLButtonElement>) => void;
}) {
  const when = formatWhen(session.updatedAt);
  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors ${
        active
          ? "bg-white/[0.04] text-gray-200"
          : "text-gray-500 hover:bg-white/[0.02] hover:text-gray-300"
      }`}
    >
      <div className="flex-1 min-w-0" onClick={onClick}>
        <p className="text-xs truncate">{session.title || "New Chat"}</p>
        <p className="text-[10px] text-gray-600 mt-0.5">
          {session.messages.length} msgs · {when}
        </p>
      </div>
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all p-1"
        aria-label="Delete session"
      >
        <X className="w-3 h-3" strokeWidth={2} />
      </button>
    </div>
  );
}

function formatWhen(iso: string): string {
  try {
    return formatDistanceToNowStrict(new Date(iso), { addSuffix: true });
  } catch {
    return new Date(iso).toLocaleDateString();
  }
}
