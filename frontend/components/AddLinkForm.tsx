"use client";

import { useState, useSyncExternalStore } from "react";
import { api } from "@/lib/api";

/** Le support ne change jamais en cours de vie de la page : rien à écouter. */
const neverChanges = () => () => {};

const supportsClipboardRead = () =>
  typeof navigator !== "undefined" && typeof navigator.clipboard?.readText === "function";

export function AddLinkForm({ onAdded }: { onAdded: () => void }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pasteHint, setPasteHint] = useState<string | null>(null);

  // `navigator` n'existe pas au rendu serveur, et l'API n'est exposée qu'en
  // contexte sécurisé. useSyncExternalStore rend `false` côté serveur puis la
  // valeur réelle après hydratation, sans décalage entre les deux rendus.
  const canPaste = useSyncExternalStore(neverChanges, supportsClipboardRead, () => false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createLink(url);
      setUrl("");
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de l'ajout");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePaste() {
    setPasteHint(null);
    try {
      const texte = (await navigator.clipboard.readText()).trim();
      if (!texte) {
        setPasteHint("Le presse-papiers est vide.");
        return;
      }
      setUrl(texte);
    } catch {
      // Permission refusée, ou navigateur qui n'autorise pas la lecture hors
      // d'un geste de collage : on renvoie l'utilisateur au raccourci clavier.
      setPasteHint("Lecture du presse-papiers refusée — utilise Ctrl+V dans le champ.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-8">
      <div className="flex gap-2">
        <input
          type="url"
          required
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
          aria-label="URL YouTube à ajouter"
          className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-300"
        />
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {submitting ? "Ajout…" : "Ajouter"}
        </button>
      </div>

      {canPaste && (
        <div className="mt-2 text-center">
          <button
            type="button"
            onClick={handlePaste}
            className="text-xs text-zinc-500 underline-offset-2 transition-colors hover:text-zinc-900 hover:underline dark:hover:text-zinc-100"
          >
            Coller depuis le presse-papiers
          </button>
          {pasteHint && (
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{pasteHint}</p>
          )}
        </div>
      )}

      {error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  );
}
