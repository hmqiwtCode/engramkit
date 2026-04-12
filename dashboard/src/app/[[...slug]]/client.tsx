"use client";

import { usePathname } from "next/navigation";
import { useMemo } from "react";

import DashboardPage from "@/views/dashboard";
import ChatPage from "@/views/chat";
import SearchPage from "@/views/search";
import SettingsPage from "@/views/settings";
import VaultsPage from "@/views/vaults";
import VaultDetailPage from "@/views/vault-detail";
import ChunksPage from "@/views/chunks";
import ChunkDetailPage from "@/views/chunk-detail";
import FilesPage from "@/views/files";
import GCPage from "@/views/gc";
import KGPage from "@/views/kg";
import MinePage from "@/views/mine";

export default function ClientRouter() {
  const pathname = usePathname() || "/";

  const page = useMemo(() => {
    const segments = pathname.split("/").filter(Boolean);
    const [s1, s2, s3, s4] = segments;

    if (segments.length === 0) return <DashboardPage />;
    if (s1 === "chat") return <ChatPage />;
    if (s1 === "search") return <SearchPage />;
    if (s1 === "settings") return <SettingsPage />;
    if (s1 === "vaults" && !s2) return <VaultsPage />;
    if (s1 === "vaults" && s2 && !s3) return <VaultDetailPage vaultId={s2} />;
    if (s1 === "vaults" && s2 && s3 === "chunks" && !s4) return <ChunksPage vaultId={s2} />;
    if (s1 === "vaults" && s2 && s3 === "chunks" && s4) return <ChunkDetailPage vaultId={s2} hash={s4} />;
    if (s1 === "vaults" && s2 && s3 === "files") return <FilesPage vaultId={s2} />;
    if (s1 === "vaults" && s2 && s3 === "gc") return <GCPage vaultId={s2} />;
    if (s1 === "vaults" && s2 && s3 === "kg") return <KGPage vaultId={s2} />;
    if (s1 === "vaults" && s2 && s3 === "mine") return <MinePage vaultId={s2} />;

    return (
      <div className="text-center py-20">
        <p className="text-lg text-gray-400">Page not found</p>
        <p className="text-sm text-gray-600 mt-2 font-mono">{pathname}</p>
      </div>
    );
  }, [pathname]);

  return (
    <div
      key={pathname}
      className="animate-in fade-in duration-150"
      style={{ animation: "fadeIn 150ms ease-out" }}
    >
      {page}
    </div>
  );
}
