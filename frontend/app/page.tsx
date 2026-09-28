"use client";

import Link from "next/link";
import { useState } from "react";
import { AddLinkForm } from "@/components/AddLinkForm";
import { LinkCard } from "@/components/LinkCard";
import { useCollections, useLinks, useOpenAIKey } from "@/lib/hooks";

export default function Page() {
  const [collectionFilter, setCollectionFilter] = useState("");
  const { collections, mutate: mutateCollections } = useCollections();
  const { links, error, isLoading, mutate: mutateLinks } = useLinks(collectionFilter);
  const { status: keyStatus } = useOpenAIKey();

  function refresh() {
    return Promise.all([mutateLinks(), mutateCollections()]);
  }

  return (
    <>
      {keyStatus && !keyStatus.configured && (
        <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
          Aucune clé OpenAI configurée.{" "}
          <Link href="/settings" className="font-medium underline underline-offset-2">
            Colle ta clé
          </Link>{" "}
          pour lancer les traitements.
        </p>
      )}

      <AddLinkForm onAdded={refresh} />

      <div className="mb-4 flex items-center justify-between gap-3">
        <h1 className="text-sm font-medium text-zinc-500">
          {links.length} lien{links.length > 1 ? "s" : ""}
        </h1>
        <select
          value={collectionFilter}
          onChange={(event) => setCollectionFilter(event.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        >
          <option value="">Toutes les collections</option>
          {collections.map((collection) => (
            <option key={collection.id} value={collection.id}>
              {collection.name} ({collection.link_count})
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error instanceof Error ? error.message : "Backend injoignable"}
        </p>
      )}

      {!isLoading && !error && links.length === 0 && (
        <p className="py-12 text-center text-sm text-zinc-500">
          Aucun lien pour l&apos;instant. Colle une URL YouTube pour commencer.
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
