export type ProcessingStatus = "pending" | "processing" | "done" | "error";

export interface CollectionRef {
  id: string;
  name: string;
}

export interface Collection extends CollectionRef {
  description: string | null;
  created_at: string;
  link_count: number;
}

export interface Summary {
  suggested_title: string | null;
  short_summary: string;
  key_points: string[];
  tags: string[];
  complexity_level: string | null;
}

export interface Link {
  id: string;
  url: string;
  source: string;
  title: string | null;
  /** Chaîne YouTube. `null` quand elle est inconnue. */
  creator: string | null;
  status: ProcessingStatus;
  error_message: string | null;
  created_at: string;
  /** Départ du traitement en cours. `null` hors traitement. */
  processing_started_at: string | null;
  /** Estimation serveur, déduite des traitements passés. `null` hors traitement. */
  estimated_seconds: number | null;
  summary: Summary | null;
  collections: CollectionRef[];
}

export interface DigestSection {
  titre: string;
  puces: string[];
}

export interface SummaryDetail extends Summary {
  transcript: string;
  /** `null` tant que le digest n'a pas été demandé pour ce lien. */
  digest_notes: DigestSection[] | null;
}

export interface LinkDetail extends Omit<Link, "summary"> {
  summary: SummaryDetail | null;
}

export interface SearchResult {
  link: Link;
  score: number;
}

export interface OpenAIKeyStatus {
  configured: boolean;
  /** `interface` : collée dans l'app, en mémoire du backend. `env` : `OPENAI_API_KEY`. */
  source: "interface" | "env" | null;
  /** Les 4 derniers caractères, jamais la clé entière. */
  hint: string | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && typeof body.detail[0]?.msg === "string") {
      return body.detail[0].msg.replace(/^Value error, /, "");
    }
  } catch {
    // réponse sans corps JSON exploitable
  }
  return `Erreur ${response.status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) throw new Error(await readError(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  listLinks: (collectionId?: string) => {
    const suffix = collectionId ? `?collection_id=${collectionId}` : "";
    return request<Link[]>(`/api/links${suffix}`);
  },

  getLink: (id: string) => request<LinkDetail>(`/api/links/${id}`),

  generateDigest: (id: string) =>
    request<{ digest_notes: DigestSection[] }>(`/api/links/${id}/digest`, { method: "POST" }),

  createLink: (url: string) =>
    request<Link>("/api/links", { method: "POST", body: JSON.stringify({ url }) }),

  deleteLink: (id: string) => request<void>(`/api/links/${id}`, { method: "DELETE" }),

  retryLink: (id: string) => request<Link>(`/api/links/${id}/retry`, { method: "POST" }),

  setLinkCollections: (id: string, collectionIds: string[]) =>
    request<Link>(`/api/links/${id}/collections`, {
      method: "PUT",
      body: JSON.stringify({ collection_ids: collectionIds }),
    }),

  listCollections: () => request<Collection[]>("/api/collections"),

  createCollection: (name: string, description?: string) =>
    request<Collection>("/api/collections", {
      method: "POST",
      body: JSON.stringify({ name, description: description || null }),
    }),

  updateCollection: (id: string, values: { name?: string; description?: string | null }) =>
    request<Collection>(`/api/collections/${id}`, {
      method: "PATCH",
      body: JSON.stringify(values),
    }),

  deleteCollection: (id: string) =>
    request<void>(`/api/collections/${id}`, { method: "DELETE" }),

  getOpenAIKey: () => request<OpenAIKeyStatus>("/api/settings/openai-key"),

  setOpenAIKey: (apiKey: string) =>
    request<OpenAIKeyStatus>("/api/settings/openai-key", {
      method: "PUT",
      body: JSON.stringify({ api_key: apiKey }),
    }),

  clearOpenAIKey: () =>
    request<OpenAIKeyStatus>("/api/settings/openai-key", { method: "DELETE" }),

  search: (q: string) =>
    request<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`),
};
