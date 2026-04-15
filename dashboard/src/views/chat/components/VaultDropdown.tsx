"use client";

import { Check, ChevronDown, Database } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { VaultSummary } from "@/lib/types";

interface VaultDropdownProps {
  vaults: VaultSummary[];
  selected: string[];
  onToggle: (id: string) => void;
  onClear: () => void;
}

export function VaultDropdown({ vaults, selected, onToggle, onClear }: VaultDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const label =
    selected.length === 0
      ? "All vaults"
      : selected.length === 1
        ? vaults.find((v) => v.vault_id === selected[0])?.repo_path?.split("/").pop() ?? selected[0]
        : `${selected.length} vaults`;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono hover:border-white/[0.12] transition-colors"
      >
        <Database className="w-3.5 h-3.5 text-gray-500" strokeWidth={1.5} />
        {label}
        <ChevronDown className="w-3 h-3 text-gray-600" strokeWidth={2} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-[#111] border border-white/[0.06] rounded-lg shadow-2xl shadow-black/50 z-50 py-1 max-h-64 overflow-y-auto">
          <DropdownItem label="All vaults" checked={selected.length === 0} onClick={onClear} />
          {vaults.map((v) => (
            <DropdownItem
              key={v.vault_id}
              label={v.repo_path?.split("/").pop() || v.vault_id}
              trailing={v.total_chunks}
              checked={selected.includes(v.vault_id)}
              onClick={() => onToggle(v.vault_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DropdownItem({
  label,
  trailing,
  checked,
  onClick,
}: {
  label: string;
  trailing?: number;
  checked: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-white/[0.02] transition-colors ${
        checked ? "text-blue-400" : "text-gray-400"
      }`}
    >
      <span
        className={`w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 ${
          checked ? "bg-blue-600 border-blue-500" : "border-white/[0.12]"
        }`}
      >
        {checked && <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />}
      </span>
      <span className="font-mono truncate">{label}</span>
      {trailing !== undefined && (
        <span className="text-[10px] text-gray-600 ml-auto font-mono tabular-nums">{trailing}</span>
      )}
    </button>
  );
}
