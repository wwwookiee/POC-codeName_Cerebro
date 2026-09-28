"use client";

import { useOptimistic, useState, useTransition } from "react";
import { api, type Collection, type CollectionRef } from "@/lib/api";

interface Props {
  linkId: string;
  assigned: CollectionRef[];
  collections: Collection[];
  onChanged: () => Promise<unknown>;
}

export function CollectionPicker({ linkId, assigned, collections, onChanged }: Props) {
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  // La case doit réagir au clic sans attendre l'aller-retour serveur. La transition
  // ne se termine qu'après revalidation, sinon l'état optimiste retombe trop tôt.
  const [assignedIds, setAssignedIds] = useOptimistic(assigned.map((item) => item.id));

  function toggle(collectionId: string) {
    const next = assignedIds.includes(collectionId)
      ? assignedIds.filter((id) => id !== collectionId)
      : [...assignedIds, collectionId];

    startTransition(async () => {
      setAssignedIds(next);
      setError(null);
      try {
        await api.setLinkCollections(linkId, next);
        await onChanged();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Échec de l'assignation");
      }
    });
  }

  function createAndAssign(event: React.FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return;

    startTransition(async () => {
      setError(null);
      try {
        const created = await api.createCollection(name);
        await api.setLinkCollections(linkId, [...assignedIds, created.id]);
        setNewName("");
        await onChanged();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Échec de la création");
      }
    });
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen(!open)}
        className="rounded-md border border-dashed border-zinc-300 px-2 py-0.5 text-xs text-zinc-500 transition-colors hover:border-zinc-500 hover:text-zinc-700 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-500 dark:hover:text-zinc-200"
      >
        + Collection
      </button>

      {open && (
        <div
          onKeyDown={(event) => event.key === "Escape" && setOpen(false)}
          className="absolute left-0 top-7 z-20 w-60 rounded-lg border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
        >
          <div className="max-h-48 overflow-y-auto">
            {collections.length === 0 && (
              <p className="px-2 py-1.5 text-xs text-zinc-500">Aucune collection</p>
            )}
            {collections.map((collection) => (
              <label
                key={collection.id}
                className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <input
                  type="checkbox"
                  checked={assignedIds.includes(collection.id)}
                  disabled={pending}
                  onChange={() => toggle(collection.id)}
                />
                <span className="truncate">{collection.name}</span>
              </label>
            ))}
          </div>

          <form
            onSubmit={createAndAssign}
            className="mt-2 border-t border-zinc-200 pt-2 dark:border-zinc-700"
          >
            <input
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder="Nouvelle collection"
              aria-label="Nouvelle collection"
              className="w-full rounded border border-zinc-300 bg-white px-2 py-1 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:focus:border-zinc-300"
            />
          </form>

          {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
        </div>
      )}
    </div>
  );
}
