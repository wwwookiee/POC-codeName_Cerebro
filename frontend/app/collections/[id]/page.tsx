"use client";

import { use } from "react";
import Link from "next/link";
import { LinkCard } from "@/components/LinkCard";
import { useCollections, useLinks } from "@/lib/hooks";

export default function Page({ params }: PageProps<"/collections/[id]">) {
  const { id } = use(params);
  const {
    collections,
    isLoading: collectionsLoading,
    mutate: mutateCollections,
  } = useCollections();
  const { links, error, isLoading, mutate: mutateLinks } = useLinks(id);

  const collection = collections.find((item) => item.id === id);

  function refresh() {
    return Promise.all([mutateLinks(), mutateCollections()]);
  }

  // La liste des collections porte déjà le nom et la description : pas d'appel dédié.
  if (!collectionsLoading && !collection) {
    return (
      <>
        <Link
          href="/collections"
          className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
          ← Collections
        </Link>
        <p className="py-12 text-center text-sm text-zinc-500">Collection introuvable.</p>
      </>
    );
  }

  return (
    <>
      <div className="mb-6">
        <Link
          href="/collections"
          className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
          ← Collections
        </Link>
        <h1 className="mt-2 text-xl font-semibold tracking-tight">
          {collection?.name ?? "…"}
        </h1>
        {collection?.description && (
          <p className="mt-1 text-sm text-zinc-500">{collection.description}</p>
        )}
        <p className="mt-1 text-sm text-zinc-500">
          {links.length} lien{links.length > 1 ? "s" : ""}
        </p>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error instanceof Error ? error.message : "Backend injoignable"}
        </p>
      )}

      {!isLoading && !error && links.length === 0 && (
        <p className="py-12 text-center text-sm text-zinc-500">
          Aucun lien dans cette collection.
        </p>
      )}

      <div className="space-y-3">
        {links.map((link) => (
          <LinkCard
            key={link.id}
            link={link}
            collections={collections}
            onChanged={refresh}
          />
        ))}
      </div>
    </>
  );
}
