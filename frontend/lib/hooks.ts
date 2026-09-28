"use client";

import useSWR from "swr";
import {
  api,
  type Collection,
  type Link,
  type LinkDetail,
  type OpenAIKeyStatus,
} from "@/lib/api";

export function useCollections() {
  const { data, error, isLoading, mutate } = useSWR<Collection[]>(
    "collections",
    api.listCollections,
  );
  return { collections: data ?? [], error, isLoading, mutate };
}

export function useLink(id: string) {
  const { data, error, isLoading, mutate } = useSWR<LinkDetail>(
    ["link", id],
    () => api.getLink(id),
    {
      // Un lien encore en traitement n'a pas de résumé : on suit son statut.
      refreshInterval: (link) =>
        link?.status === "pending" || link?.status === "processing" ? 5000 : 0,
    },
  );

  return { link: data, error, isLoading, mutate };
}

export function useLinks(collectionId?: string) {
  const { data, error, isLoading, mutate } = useSWR<Link[]>(
    ["links", collectionId ?? ""],
    () => api.listLinks(collectionId || undefined),
    {
      // Changer de filtre change la clé SWR : sans ça la liste se vide le temps du fetch.
      keepPreviousData: true,
      // Tant qu'un traitement tourne, on rafraîchit pour suivre le changement de statut.
      refreshInterval: (links) =>
        links?.some((link) => link.status === "pending" || link.status === "processing")
          ? 5000
          : 0,
    },
  );

  return { links: data ?? [], error, isLoading, mutate };
}

export function useOpenAIKey() {
  const { data, error, isLoading, mutate } = useSWR<OpenAIKeyStatus>(
    "openai-key",
    api.getOpenAIKey,
  );
  return { status: data, error, isLoading, mutate };
}
