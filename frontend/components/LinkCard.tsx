"use client";

import { useState } from "react";
import Link from "next/link";
import { api, type Collection, type Link as CerebroLink } from "@/lib/api";
import { CollectionPicker } from "@/components/CollectionPicker";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { StatusBadge } from "@/components/StatusBadge";

function TrashIcon() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4"
    >
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v5M14 11v5" />
    </svg>
  );
}

interface Props {
  link: CerebroLink;
  collections: Collection[];
  onChanged: () => Promise<unknown>;
  score?: number;
}

export function LinkCard({ link, collections, onChanged, score }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const summary = link.summary;
  const title = summary?.suggested_title ?? link.title ?? link.url;

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action échouée");
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    await run(() => api.deleteLink(link.id));
    // En cas de succès la card disparaît du flux et ce composant est démonté ;
    // ces deux états ne servent qu'au cas d'échec, où la modal doit se fermer
    // pour laisser voir le message d'erreur.
    setDeleting(false);
    setConfirming(false);
  }

  return (
    <article className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {/* Le titre mène au digest interne ; l'accès à la vidéo passe par
              l'URL en dessous, pour garder une seule zone cliquable par cible. */}
          <Link href={`/links/${link.id}`} className="font-medium hover:underline">
            {title}
          </Link>
          <a
            href={link.url}
            target="_blank"
            rel="noreferrer"
            className="mt-0.5 block truncate text-xs text-zinc-500 hover:text-zinc-700 hover:underline dark:hover:text-zinc-300"
          >
            {/* Tant que le titre n'est pas extrait il vaut l'URL : l'afficher
                une seconde fois donnerait deux liens au libellé identique. */}
            {title === link.url ? "Voir sur YouTube ↗" : link.url}
          </a>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {score !== undefined && (
            <span className="text-xs tabular-nums text-zinc-500">
              {(score * 100).toFixed(0)}%
            </span>
          )}
          <StatusBadge
            status={link.status}
            processing_started_at={link.processing_started_at}
            estimated_seconds={link.estimated_seconds}
          />
        </div>
      </div>

      {link.status === "error" && (
        <div className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/50 dark:text-red-300">
          <p className="break-words">{link.error_message}</p>
          <button
            type="button"
            onClick={() => run(() => api.retryLink(link.id))}
            className="mt-2 font-medium underline underline-offset-2"
          >
            Relancer le traitement
          </button>
        </div>
      )}

      {summary && (
        <div className="mt-3 space-y-3">
          <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
            {summary.short_summary}
          </p>

          {summary.key_points.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="text-xs font-medium text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
              >
                {expanded ? "Masquer" : `Voir les ${summary.key_points.length} points clés`}
              </button>
              {expanded && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
                  {summary.key_points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {(link.creator || summary.tags.length > 0) && (
            <div className="flex flex-wrap gap-1.5">
              {/* Le créateur ouvre la liste : c'est un fait sur la vidéo, pas
                  un thème déduit par le modèle. D'où sa teinte propre — teal,
                  la plus éloignée de l'indigo du niveau de complexité, seule
                  autre couleur de cette rangée. */}
              {link.creator && (
                <span className="rounded-md bg-teal-50 px-2 py-0.5 text-xs font-medium text-teal-700 dark:bg-teal-950 dark:text-teal-300">
                  {link.creator}
                </span>
              )}
              {summary.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                >
                  {tag}
                </span>
              ))}
              {summary.complexity_level && (
                <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                  {summary.complexity_level}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        {link.collections.map((collection) => (
          <span
            key={collection.id}
            className="rounded-md bg-zinc-900 px-2 py-0.5 text-xs text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            {collection.name}
          </span>
        ))}
        <CollectionPicker
          linkId={link.id}
          assigned={link.collections}
          collections={collections}
          onChanged={onChanged}
        />
        <button
          type="button"
          onClick={() => setConfirming(true)}
          // Le pictogramme seul ne dit pas ce qui sera supprimé : le lecteur
          // d'écran doit l'entendre, et la souris le voir au survol.
          aria-label={`Supprimer « ${title} »`}
          title="Supprimer"
          className="ml-auto rounded-md p-1 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/50 dark:hover:text-red-400"
        >
          <TrashIcon />
        </button>
      </div>

      {error && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>}

      <ConfirmDialog
        open={confirming}
        pending={deleting}
        title="Supprimer ce lien ?"
        detail={title}
        onConfirm={confirmDelete}
        onCancel={() => setConfirming(false)}
      />
    </article>
  );
}
