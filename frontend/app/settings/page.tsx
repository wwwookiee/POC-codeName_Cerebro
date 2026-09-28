"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useOpenAIKey } from "@/lib/hooks";

const SOURCE_LABEL = {
  interface: "collée ici",
  env: "lue dans OPENAI_API_KEY",
} as const;

export default function Page() {
  const { status, error: loadError, mutate } = useOpenAIKey();
  const [apiKey, setApiKey] = useState("");
  const [visible, setVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await mutate(api.setOpenAIKey(apiKey), { revalidate: false });
      setApiKey("");
      setVisible(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }

  async function handleClear() {
    setError(null);
    try {
      await mutate(api.clearOpenAIKey(), { revalidate: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la suppression");
    }
  }

  return (
    <>
      <h1 className="mb-1 text-lg font-semibold tracking-tight">Clé API OpenAI</h1>
      <p className="mb-6 text-sm text-zinc-500">
        Pour un test local : la clé collée ici alimente la transcription, le résumé et la
        recherche. Elle reste en mémoire du backend — jamais écrite en base ni sur disque — et
        s&apos;efface à son redémarrage.
      </p>

      <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-4 text-sm dark:border-zinc-800 dark:bg-zinc-900">
        {loadError ? (
          <p className="text-red-600 dark:text-red-400">Backend injoignable</p>
        ) : !status ? (
          <p className="text-zinc-500">Chargement…</p>
        ) : status.configured && status.source ? (
          <div className="flex items-center justify-between gap-3">
            <p>
              <span className="mr-2 inline-block size-2 rounded-full bg-emerald-500" aria-hidden />
              Clé active <span className="font-mono">{status.hint}</span>{" "}
              <span className="text-zinc-500">— {SOURCE_LABEL[status.source]}</span>
            </p>
            {status.source === "interface" && (
              <button
                type="button"
                onClick={handleClear}
                className="text-xs text-zinc-500 underline-offset-2 hover:text-red-600 hover:underline"
              >
                Oublier
              </button>
            )}
          </div>
        ) : (
          <p>
            <span className="mr-2 inline-block size-2 rounded-full bg-amber-500" aria-hidden />
            Aucune clé : les traitements et la recherche sont indisponibles.
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        <label htmlFor="openai-key" className="mb-1 block text-sm font-medium">
          {status?.configured ? "Remplacer la clé" : "Coller ta clé"}
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              id="openai-key"
              type={visible ? "text" : "password"}
              required
              autoComplete="off"
              spellCheck={false}
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="sk-…"
              className="w-full rounded-lg border border-zinc-300 bg-white py-2 pl-3 pr-16 font-mono text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-300"
            />
            <button
              type="button"
              onClick={() => setVisible((v) => !v)}
              className="absolute inset-y-0 right-2 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            >
              {visible ? "Masquer" : "Afficher"}
            </button>
          </div>
          <button
            type="submit"
            disabled={saving || apiKey.trim() === ""}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {saving ? "Vérification…" : "Enregistrer"}
          </button>
        </div>
        <p className="mt-2 text-xs text-zinc-500">
          La clé est vérifiée auprès d&apos;OpenAI avant d&apos;être retenue.
        </p>
        {error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>
    </>
  );
}
