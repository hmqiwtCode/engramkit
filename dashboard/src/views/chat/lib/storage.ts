import type { ChatSession } from "../types";

const STORAGE_KEY = "engramkit_chat_sessions";
const SESSION_CAP = 20;
export const MESSAGE_CAP_PER_SESSION = 50;

export function loadSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved ? (JSON.parse(saved) as ChatSession[]) : [];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(sessions.slice(-SESSION_CAP)),
    );
  } catch {
    // ignore quota or serialisation errors — state lives in memory anyway
  }
}

export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}
