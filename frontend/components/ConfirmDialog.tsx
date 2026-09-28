"use client";

import { useEffect, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  /** Ce qui va disparaître, rappelé à l'utilisateur avant qu'il confirme. */
  detail?: string;
  confirmLabel?: string;
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Confirmation d'une action destructrice, bâtie sur `<dialog>`.
 *
 * L'élément natif apporte le piège de focus, la fermeture à la touche Échap et
 * l'inertie de l'arrière-plan — de quoi éviter une dépendance UI dans un projet
 * qui n'en a aucune.
 */
export function ConfirmDialog({
  open,
  title,
  detail,
  confirmLabel = "Supprimer",
  pending = false,
  onConfirm,
  onCancel,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    // showModal() sur un dialog déjà ouvert lève une InvalidStateError, et
    // close() sur un dialog fermé émet un `close` parasite.
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="confirm-dialog-title"
      onCancel={(event) => {
        // Échap fermerait le dialog sans prévenir le parent, qui garde l'état.
        event.preventDefault();
        if (!pending) onCancel();
      }}
      onClick={(event) => {
        if (event.target === ref.current && !pending) onCancel();
      }}
      className="m-auto w-[min(26rem,calc(100vw-2rem))] rounded-xl border border-zinc-200 bg-white p-5 text-zinc-900 shadow-xl backdrop:bg-zinc-900/40 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100"
    >
      <h2 id="confirm-dialog-title" className="text-sm font-semibold">
        {title}
      </h2>
      {detail && (
        <p className="mt-1.5 text-sm break-words text-zinc-600 dark:text-zinc-400">{detail}</p>
      )}
      <p className="mt-3 text-xs text-zinc-500">Cette action est irréversible.</p>

      <div className="mt-5 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={pending}
          className="rounded-lg px-3 py-1.5 text-sm text-zinc-600 transition-colors hover:bg-zinc-100 disabled:opacity-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
        >
          Annuler
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={pending}
          className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Suppression…" : confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
