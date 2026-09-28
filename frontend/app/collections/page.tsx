"use client";

import { useState } from "react";
import Link from "next/link";
import { api, type Collection } from "@/lib/api";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useCollections } from "@/lib/hooks";

export default function Page() {
  const { collections, mutate } = useCollections();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Collection | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.createCollection(name.trim(), description.trim());
      setName("");
      setDescription("");
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la création");
    }
  }

  async function handleRename(collection: Collection) {
    const next = window.prompt("Nouveau nom", collection.name);
    if (!next || next === collection.name) return;
    try {
      await api.updateCollection(collection.id, { name: next });
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec du renommage");
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteCollection(pendingDelete.id);
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la suppression");
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  }

  return (
    <>
      <form onSubmit={handleCreate} className="mb-8 space-y-2">
        <div className="flex gap-2">
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Nom de la collection"
            aria-label="Nom de la collection"
            className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-300"
          />
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 dark:bg-zinc-100 dark:text-zinc-900"
          >
            Créer
          </button>
        </div>
        <input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Description (optionnelle)"
          aria-label="Description de la collection"
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-300"
        />
      </form>

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error}
        </p>
      )}

      {collections.length === 0 && (
        <p className="py-12 text-center text-sm text-zinc-500">Aucune collection.</p>
      )}

      <ul className="space-y-2">
        {collections.map((collection) => (
          <li
            key={collection.id}
            className="relative flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-4 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600"
          >
            {/* before:inset-0 étend le lien à toute la carte ; les éléments en relative restent cliquables au-dessus. */}
            <Link
              href={`/collections/${collection.id}`}
              className="min-w-0 flex-1 before:absolute before:inset-0 before:rounded-xl"
            >
              <p className="font-medium">{collection.name}</p>
              {collection.description && (
                <p className="truncate text-sm text-zinc-500">{collection.description}</p>
              )}
            </Link>
            <span className="relative shrink-0 text-xs text-zinc-500">
              {collection.link_count} lien{collection.link_count > 1 ? "s" : ""}
            </span>
            <button
              type="button"
              onClick={() => handleRename(collection)}
              className="relative text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            >
              Renommer
            </button>
            <button
              type="button"
              onClick={() => setPendingDelete(collection)}
              className="relative text-xs text-zinc-400 hover:text-red-600 dark:hover:text-red-400"
            >
              Supprimer
            </button>
          </li>
        ))}
      </ul>

      <ConfirmDialog
        open={pendingDelete !== null}
        pending={deleting}
        title="Supprimer cette collection ?"
        detail={
          pendingDelete
            ? `« ${pendingDelete.name} » — ${pendingDelete.link_count} lien${
                pendingDelete.link_count > 1 ? "s" : ""
              } y ${pendingDelete.link_count > 1 ? "sont rattachés" : "est rattaché"}. ` +
              "Les liens eux-mêmes ne sont pas supprimés."
            : undefined
        }
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
