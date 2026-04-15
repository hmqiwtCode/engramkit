"use client";

import useSWR from "swr";

import { vaults as vaultsApi } from "@/lib/api";
import type { VaultSummary } from "@/lib/types";

/** Single source of truth for the vault list — deduped + cached via SWR. */
export function useVaults() {
  const { data, error, isLoading, mutate } = useSWR<VaultSummary[]>(
    "/api/vaults",
    () => vaultsApi.list(),
    { revalidateOnFocus: false },
  );
  return {
    vaults: data ?? [],
    error,
    isLoading,
    refresh: mutate,
  };
}
