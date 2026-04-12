const BASE_URL = process.env.NEXT_PUBLIC_ENGRAMKIT_API_URL || "";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text);
  }
  return res.json();
}

// ── Vaults ──

export const vaults = {
  list: () => api<any[]>("/api/vaults"),
  get: (id: string) => api<any>(`/api/vaults/${id}`),
  create: (repoPath: string) =>
    api<any>("/api/vaults", { method: "POST", body: JSON.stringify({ repo_path: repoPath }) }),
  delete: (id: string) => api<void>(`/api/vaults/${id}`, { method: "DELETE" }),
};

// ── Search ──

export const search = {
  global: (query: string, n_results = 5, wing?: string, room?: string) =>
    api<any>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, n_results, wing, room }),
    }),
  inVault: (vaultId: string, query: string, n_results = 5, wing?: string, room?: string) =>
    api<any>(`/api/vaults/${vaultId}/search`, {
      method: "POST",
      body: JSON.stringify({ query, n_results, wing, room }),
    }),
};

// ── Files & Chunks ──

export const files = {
  list: (vaultId: string) => api<any[]>(`/api/vaults/${vaultId}/files`),
};

export const chunks = {
  list: (vaultId: string, params?: Record<string, any>) => {
    const query = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => v != null && query.set(k, String(v)));
    return api<any>(`/api/vaults/${vaultId}/chunks?${query}`);
  },
  get: (vaultId: string, hash: string) => api<any>(`/api/vaults/${vaultId}/chunks/${hash}`),
  update: (vaultId: string, hash: string, data: any) =>
    api<any>(`/api/vaults/${vaultId}/chunks/${hash}`, { method: "PATCH", body: JSON.stringify(data) }),
};

// ── Mining ──

export const mining = {
  start: (vaultId: string, options?: any) =>
    api<any>(`/api/vaults/${vaultId}/mine`, { method: "POST", body: JSON.stringify(options || {}) }),
};

// ── GC ──

export const gc = {
  run: (vaultId: string, retentionDays = 30, dryRun = false) =>
    api<any>(`/api/vaults/${vaultId}/gc`, {
      method: "POST",
      body: JSON.stringify({ retention_days: retentionDays, dry_run: dryRun }),
    }),
  log: (vaultId: string) => api<any[]>(`/api/vaults/${vaultId}/gc/log`),
};

// ── Knowledge Graph ──

export const kg = {
  stats: (vaultId: string) => api<any>(`/api/vaults/${vaultId}/kg/stats`),
  entities: (vaultId: string) => api<any[]>(`/api/vaults/${vaultId}/kg/entities`),
  entity: (vaultId: string, name: string, asOf?: string) =>
    api<any>(`/api/vaults/${vaultId}/kg/entity/${name}${asOf ? `?as_of=${asOf}` : ""}`),
  timeline: (vaultId: string, entity?: string) =>
    api<any>(`/api/vaults/${vaultId}/kg/timeline${entity ? `?entity=${entity}` : ""}`),
  graph: (vaultId: string) => api<any>(`/api/vaults/${vaultId}/kg/graph`),
  addTriple: (vaultId: string, data: any) =>
    api<any>(`/api/vaults/${vaultId}/kg/triples`, { method: "POST", body: JSON.stringify(data) }),
  invalidate: (vaultId: string, data: any) =>
    api<any>(`/api/vaults/${vaultId}/kg/triples/invalidate`, { method: "PATCH", body: JSON.stringify(data) }),
};

// ── Memory ──

export const memory = {
  wakeup: (vaultId: string, wing?: string, l1Tokens = 1000) =>
    api<any>(`/api/vaults/${vaultId}/memory/wakeup?l1_tokens=${l1Tokens}${wing ? `&wing=${wing}` : ""}`),
  recall: (vaultId: string, wing?: string, room?: string) =>
    api<any>(`/api/vaults/${vaultId}/memory/recall${wing ? `?wing=${wing}` : ""}${room ? `&room=${room}` : ""}`),
};

// ── Save ──

export const save = {
  content: (vaultId: string, content: string, wing?: string, room = "general", importance = 3.0) =>
    api<any>(`/api/vaults/${vaultId}/save`, {
      method: "POST",
      body: JSON.stringify({ content, wing, room, importance }),
    }),
  diary: (vaultId: string, content: string, wing = "diary") =>
    api<any>(`/api/vaults/${vaultId}/diary`, { method: "POST", body: JSON.stringify({ content, wing }) }),
};

// ── Config ──

export const config = {
  global: () => api<any>("/api/config"),
  vault: (vaultId: string) => api<any>(`/api/vaults/${vaultId}/config`),
  update: (vaultId: string, key: string, value: string) =>
    api<any>(`/api/vaults/${vaultId}/config`, { method: "PATCH", body: JSON.stringify({ key, value }) }),
};
