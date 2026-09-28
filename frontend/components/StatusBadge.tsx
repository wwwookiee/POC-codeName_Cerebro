"use client";

import { useSyncExternalStore } from "react";
import type { Link, ProcessingStatus } from "@/lib/api";

const labels: Record<Exclude<ProcessingStatus, "done">, { text: string; className: string }> = {
  pending: {
    text: "En attente",
    className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  },
  processing: {
    text: "Traitement…",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  },
  error: {
    text: "Erreur",
    className: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  },
};

// Horloge partagée : un seul intervalle pour toute la page, et tous les
// compteurs affichent donc la même seconde. `getSnapshot` doit rendre une
// valeur stable entre deux tics — lire `Date.now()` à chaque appel ferait
// croire à React que le store change à chaque rendu, et boucler.
let clockNow = Date.now();
let clockTimer: ReturnType<typeof setInterval> | null = null;
const clockListeners = new Set<() => void>();

function subscribeToClock(listener: () => void): () => void {
  clockListeners.add(listener);
  if (clockTimer === null) {
    // Remis à l'heure à l'abonnement : entre deux traitements, plus personne
    // ne fait avancer `clockNow`, qui peut dater de longtemps.
    clockNow = Date.now();
    clockTimer = setInterval(() => {
      clockNow = Date.now();
      clockListeners.forEach((l) => l());
    }, 1000);
  }
  return () => {
    clockListeners.delete(listener);
    if (clockListeners.size === 0 && clockTimer !== null) {
      clearInterval(clockTimer);
      clockTimer = null;
    }
  };
}

const getClock = () => clockNow;
// Aucune horloge au rendu serveur : le compteur n'y apparaît pas, et le
// premier rendu client lui est donc identique.
const getServerClock = () => null;

/** `95` -> `1:35`. Au-delà de l'heure, `1:02:03`. */
function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

type Props = Pick<Link, "status" | "processing_started_at" | "estimated_seconds">;

export function StatusBadge({ status, processing_started_at, estimated_seconds }: Props) {
  const now = useSyncExternalStore(subscribeToClock, getClock, getServerClock);

  // Un lien terminé n'affiche plus rien : le résumé présent sur la card dit
  // déjà que le traitement a abouti.
  if (status === "done") return null;

  const { text, className } = labels[status];

  const startedAt =
    status === "pending" || status === "processing" ? processing_started_at : null;
  const start = startedAt === null ? NaN : new Date(startedAt).getTime();
  const elapsed = now !== null && !Number.isNaN(start) ? (now - start) / 1000 : null;

  // L'estimation n'a de sens que tant qu'elle est devant nous. Dépassée, elle
  // est tue plutôt que de promettre une échéance déjà manquée.
  const estimate =
    estimated_seconds !== null && elapsed !== null && estimated_seconds > elapsed
      ? estimated_seconds
      : null;

  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium tabular-nums ${className}`}
      // Le compteur change chaque seconde : annoncé une fois, il n'a pas à
      // être relu en boucle par un lecteur d'écran.
      aria-live="off"
    >
      {text}
      {elapsed !== null && ` ${formatDuration(elapsed)}`}
      {estimate !== null && ` / ~${formatDuration(estimate)}`}
    </span>
  );
}
