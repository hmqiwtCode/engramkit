"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { vaults as vaultsApi } from "@/lib/api";

const mainNav = [
  { href: "/", label: "Overview", icon: "~" },
  { href: "/chat", label: "Chat", icon: ">" },
  { href: "/search", label: "Search", icon: "?" },
];

const dataNav = [
  { href: "/vaults", label: "Vaults", icon: "#" },
];

const systemNav = [
  { href: "/settings", label: "Settings", icon: "*" },
];

function NavItem({ item, active }: { item: { href: string; label: string; icon: string }; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={`group relative flex items-center gap-3 px-3 py-2 text-[13px] rounded-md transition-all duration-150 ${
        active
          ? "text-gray-100 bg-white/[0.04]"
          : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.02]"
      }`}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 bg-blue-500 rounded-r-full" />
      )}
      <span className={`text-sm w-5 text-center flex-shrink-0 ${active ? "text-blue-400" : "text-gray-600 group-hover:text-gray-500"}`}>
        {item.icon}
      </span>
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

function NavSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-1">
      <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-gray-600 select-none">
        {label}
      </p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname() || "/";
  const [vaultCount, setVaultCount] = useState<number | null>(null);

  useEffect(() => {
    vaultsApi.list().then((list) => setVaultCount(list.length)).catch(() => {});
  }, []);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="w-56 flex-shrink-0 bg-[#0c0c0c] border-r border-white/[0.06] flex flex-col select-none">
      {/* Brand */}
      <div className="px-4 py-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-blue-500/15 border border-blue-500/20 flex items-center justify-center">
            <span className="text-blue-400 text-[10px] font-bold font-mono">E</span>
          </div>
          <div>
            <h1 className="text-[13px] font-semibold tracking-tight text-gray-100">EngramKit</h1>
            <p className="text-[10px] text-gray-600 leading-none mt-0.5">Memory System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-4 overflow-y-auto">
        <NavSection label="Navigate">
          {mainNav.map((item) => (
            <NavItem key={item.href} item={item} active={isActive(item.href)} />
          ))}
        </NavSection>

        <NavSection label="Data">
          {dataNav.map((item) => (
            <div key={item.href} className="relative">
              <NavItem item={item} active={isActive(item.href)} />
              {vaultCount !== null && (
                <span className="absolute right-2.5 top-1/2 -translate-y-1/2 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-white/[0.06] text-[10px] font-mono text-gray-500 tabular-nums px-1">
                  {vaultCount}
                </span>
              )}
            </div>
          ))}
        </NavSection>

        <NavSection label="System">
          {systemNav.map((item) => (
            <NavItem key={item.href} item={item} active={isActive(item.href)} />
          ))}
        </NavSection>
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/[0.06]">
        <div className="flex items-center justify-between">
          <p className="text-[10px] text-gray-700 font-mono">v0.1.0</p>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500/60 animate-pulse" />
            <span className="text-[10px] text-gray-600">Active</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
