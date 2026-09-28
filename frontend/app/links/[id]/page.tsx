"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, type DigestSection } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { useLink } from "@/lib/hooks";

// 230 mots/minute : moyenne haute de lecture d'écran, cohérente avec la cible
// de ~450 mots donnée au modèle.
const WORDS_PER_MINUTE = 230;

function readingMinutes(sections: DigestSection[]): number {
  const words = sections
    .flatMap((section) => [section.titre, ...section.puces])
    .join(" ")
    .split(/\s+/)
    .filter(Boolean).length;
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

export default function LinkDigestPage({ params }: PageProps<"/links/[id]">) {
  const { id } = use(params);
  const { link, error, isLoading, mutate } = useLink(id);

  const [generating, setGenerating] = useState(false);
  const [digestError, setDigestError] = useState<string | null>(null);
  // Empêche une seconde génération : le double rendu du mode strict rejouerait
  // l'effet, et chaque appel coûte une requête au modèle.
  const requested = useRef(false);

  const summary = link?.summary ?? null;
  const digest = summary?.digest_notes ?? null;

  const runGeneration = useCallback(async () => {
    setGenerating(true);
    setDigestError(null);
    try {
      const { digest_notes } = await api.generateDigest(id);
      await mutate(
        (current) =>
          current && current.summary
            ? { ...current, summary: { ...current.summary, digest_notes } }
            : current,
        { revalidate: false },
      );
    } catch (err) {
      setDigestError(err instanceof Error ? err.message : "Génération du digest échouée");
    } finally {
      setGenerating(false);
    }
  }, [id, mutate]);

  useEffect(() => {
    if (!summary || summary.digest_notes || requested.current) return;
    requested.current = true;
    void runGeneration();
  }, [summary, runGeneration]);

  if (isLoading && !link) {
    return <p className="py-12 text-center text-sm text-zinc-500">Chargement…</p>;
  }

  if (error || !link) {
    return (
      <div className="space-y-4">
        <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200">
          ← Retour au flux
        </Link>
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error instanceof Error ? error.message : "Lien introuvable"}
        </p>
      </div>
    );
  }

  const title = summary?.suggested_title ?? link.title ?? link.url;

  return (
    <article className="space-y-6">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200">
        ← Retour au flux
      </Link>

      <header className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <StatusBadge
            status={link.status}
            processing_started_at={link.processing_started_at}
            estimated_seconds={link.estimated_seconds}
          />
        </div>
        <a
          href={link.url}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-xs text-zinc-500 hover:underline"
        >
          Voir sur YouTube ↗
        </a>

        {(link.collections.length > 0 || summary) && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {link.collections.map((collection) => (
              <span
                key={collection.id}
                className="rounded-md bg-zinc-900 px-2 py-0.5 text-xs text-white dark:bg-zinc-100 dark:text-zinc-900"
              >
                {collection.name}
              </span>
            ))}
            {summary?.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
              >
                {tag}
              </span>
            ))}
            {summary?.complexity_level && (
              <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                {summary.complexity_level}
              </span>
            )}
          </div>
        )}
      </header>

      {link.status === "error" && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          <p className="break-words">{link.error_message}</p>
          <button
            type="button"
            onClick={() => api.retryLink(link.id).then(() => mutate())}
            className="mt-2 text-xs font-medium underline underline-offset-2"
          >
            Relancer le traitement
          </button>
        </div>
      )}

      {(link.status === "pending" || link.status === "processing") && (
        <p className="rounded-lg bg-zinc-100 p-3 text-sm text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
          Traitement en cours. Le digest sera disponible une fois la vidéo résumée.
        </p>
      )}

      {summary && (
        <>
          <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            {summary.short_summary}
          </p>

          <section className="space-y-3 border-t border-zinc-200 pt-6 dark:border-zinc-800">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-sm font-medium text-zinc-500">Notes</h2>
              {digest && (
                <span className="text-xs text-zinc-400">
                  ~{readingMinutes(digest)} min de lecture
                </span>
              )}
            </div>

            {generating && (
              <p className="text-sm text-zinc-500">Génération du digest en cours…</p>
            )}

            {digestError && !generating && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
                <p className="break-words">{digestError}</p>
                <button
                  type="button"
                  onClick={() => void runGeneration()}
                  className="mt-2 text-xs font-medium underline underline-offset-2"
                >
                  Réessayer
                </button>
              </div>
            )}

            {digest && (
              <div className="space-y-5">
                {digest.map((section, index) => (
                  <div key={index}>
                    <h3 className="text-[15px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
                      {section.titre}
                    </h3>
                    <ul className="mt-1.5 space-y-1.5">
                      {section.puces.map((puce, puceIndex) => (
                        <li
                          key={puceIndex}
                          className="flex gap-2.5 text-[15px] leading-6 text-zinc-700 dark:text-zinc-300"
                        >
                          <span aria-hidden className="mt-2 size-1 shrink-0 rounded-full bg-zinc-400" />
                          <span>{puce}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>

          {summary.key_points.length > 0 && (
            <section className="space-y-2 border-t border-zinc-200 pt-6 dark:border-zinc-800">
              <h2 className="text-sm font-medium text-zinc-500">Points clés</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
                {summary.key_points.map((point, index) => (
                  <li key={index}>{point}</li>
                ))}
              </ul>
            </section>
          )}

          {summary.transcript && (
            <details className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
              <summary className="cursor-pointer text-sm font-medium text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200">
                Transcription complète
              </summary>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                {summary.transcript}
              </p>
            </details>
          )}
        </>
      )}
    </article>
  );
}
