"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { LinkCard } from "@/components/LinkCard";
import { api, type SearchResult } from "@/lib/api";
import { useCollections } from "@/lib/hooks";

function Results() {
  // La requête vit dans l'URL : le champ est porté par la nav, et une
  // recherche se partage ou se remet en favori telle quelle.
  const query = useSearchParams().get("q")?.trim() ?? "";
  const { collections, mutate: mutateCollections } = useCollections();

  const {
    data: results,
    error,
    isLoading,
    mutate: mutateResults,
  } = useSWR<SearchResult[]>(
    query ? ["search", query] : null,
    () => api.search(query),
    { keepPreviousData: true },
  );

  // Un lien supprimé ou relancé depuis les résultats doit disparaître de la liste.
  async function refreshAfterChange() {
    await Promise.all([mutateResults(), mutateCollections()]);
  }

  if (!query) {
    return (
      <p className="py-12 text-center text-sm text-zinc-500">
        Utilise la loupe, en haut à droite, pour chercher dans tes liens.
      </p>
    );
  }

  return (
    <>
      <p className="mb-6 text-sm text-zinc-500">
        Résultats pour <span className="text-zinc-900 dark:text-zinc-100">« {query} »</span>
      </p>

      {error && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error instanceof Error ? error.message : "Échec de la recherche"}
        </p>
      )}

      {isLoading && !results && (
        <p className="py-12 text-center text-sm text-zinc-500">Recherche…</p>
      )}

      {results !== undefined && results.length === 0 && !error && (
        <p className="py-12 text-center text-sm text-zinc-500">Aucun résultat.</p>
      )}

      <div className="space-y-3">
        {results?.map((result) => (
          <LinkCard
            key={result.link.id}
            link={result.link}
            collections={collections}
            onChanged={refreshAfterChange}
            score={result.score}
          />
        ))}
      </div>
    </>
  );
}

export default function Page() {
  // `useSearchParams` impose une frontière de suspense, sans quoi la page
  // entière basculerait en rendu dynamique.
  return (
    <Suspense fallback={<p className="py-12 text-center text-sm text-zinc-500">Recherche…</p>}>
      <Results />
    </Suspense>
  );
}
