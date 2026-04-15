"use client";

import { Menu } from "lucide-react";

import type { VaultSummary } from "@/lib/types";
import type { ChatMode } from "../types";
import { VaultDropdown } from "./VaultDropdown";

interface ChatToolbarProps {
  showSessions: boolean;
  onToggleSessions: () => void;

  vaults: VaultSummary[];
  selectedVaults: string[];
  onToggleVault: (id: string) => void;
  onClearVaults: () => void;

  mode: ChatMode;
  onSetMode: (mode: ChatMode) => void;

  nContext: number;
  onSetNContext: (n: number) => void;

  canClear: boolean;
  onClear: () => void;
}

export function ChatToolbar(props: ChatToolbarProps) {
  const {
    showSessions,
    onToggleSessions,
    vaults,
    selectedVaults,
    onToggleVault,
    onClearVaults,
    mode,
    onSetMode,
    nContext,
    onSetNContext,
    canClear,
    onClear,
  } = props;

  return (
    <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/[0.06] px-1">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSessions}
          className={`p-2 rounded-lg transition-colors ${
            showSessions
              ? "bg-blue-600 text-white"
              : "bg-[#111] text-gray-500 hover:text-gray-300 border border-white/[0.06]"
          }`}
          title="Chat history"
        >
          <Menu className="w-4 h-4" strokeWidth={1.5} />
        </button>

        <VaultDropdown
          vaults={vaults}
          selected={selectedVaults}
          onToggle={onToggleVault}
          onClear={onClearVaults}
        />

        <ModeToggle mode={mode} onChange={onSetMode} />

        {mode === "rag" && <NContextPicker value={nContext} onChange={onSetNContext} />}
      </div>

      {canClear && (
        <button
          onClick={onClear}
          className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300 bg-gray-800 hover:bg-gray-700 border border-white/[0.06] rounded-lg transition-colors font-medium"
        >
          Clear
        </button>
      )}
    </div>
  );
}

function ModeToggle({ mode, onChange }: { mode: ChatMode; onChange: (m: ChatMode) => void }) {
  const item = (target: ChatMode, label: string, first: boolean) => (
    <button
      onClick={() => onChange(target)}
      className={`px-3 py-2 text-xs font-medium transition-colors ${
        mode === target
          ? `bg-blue-600/20 text-blue-400 ${first ? "border-r border-blue-500/20" : ""}`
          : `text-gray-500 hover:text-gray-300 ${first ? "border-r border-white/[0.06]" : ""}`
      }`}
    >
      {label}
    </button>
  );
  return (
    <div className="flex items-center bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
      {item("rag", "RAG", true)}
      {item("direct", "Direct", false)}
    </div>
  );
}

function NContextPicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div className="flex items-center gap-1.5">
      <label className="text-[10px] text-gray-600 uppercase tracking-wider">Chunks</label>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="appearance-none bg-[#111] border border-white/[0.06] rounded-lg px-3 py-1.5 pr-6 text-xs text-gray-400 font-mono focus:outline-none focus:border-blue-500/50 cursor-pointer"
      >
        {[5, 10, 15, 20].map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </div>
  );
}
