"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useRef, useState } from "react";

const routes = [
  { href: "/", label: "Flux" },
  { href: "/collections", label: "Collections" },
  { href: "/settings", label: "Clé API" },
];

// Le backend refuse une requête d'un seul caractère : autant ne pas l'envoyer.
const MIN_QUERY_LENGTH = 2;

function SearchIcon() {
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
      <path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14M20 20l-4.1-4.1" />
    </svg>
  );
}

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Sur la page de résultats le champ reste déployé : le replier masquerait
  // l'outil qui a produit ce qu'on est en train de lire.
  const onSearchPage = pathname === "/search";
  const expanded = open || onSearchPage;

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY_LENGTH) return;
    router.push(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  function toggle() {
    if (expanded && !onSearchPage) {
      setOpen(false);
      return;
    }
    setOpen(true);
    // Le champ est toujours monté, seulement rogné à zéro : il est donc
    // focusable immédiatement, sans attendre la fin de l'animation.
    inputRef.current?.focus();
  }

  return (
    <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex w-full max-w-3xl items-center gap-6 px-4 py-3">
        <Link href="/" className="font-semibold tracking-tight">
          Cerebro
        </Link>
        <nav className="flex gap-1 text-sm">
          {routes.map((route) => {
            const active = pathname === route.href;
            return (
              <Link
                key={route.href}
                href={route.href}
                className={`rounded-md px-3 py-1.5 transition-colors ${
                  active
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                }`}
              >
                {route.label}
              </Link>
            );
          })}
        </nav>

        <form onSubmit={handleSubmit} className="ml-auto flex items-center">
          <div
            className={`overflow-hidden transition-all duration-200 ease-out ${
              expanded ? "w-36 opacity-100 sm:w-56" : "w-0 opacity-0"
            }`}
          >
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape" && !onSearchPage) {
                  setOpen(false);
                  inputRef.current?.blur();
                }
              }}
              onBlur={() => {
                // Un champ vide qu'on quitte se referme ; s'il porte une
                // requête, la refermer effacerait un travail en cours.
                if (query.trim() === "") setOpen(false);
              }}
              placeholder="la vidéo qui parlait de pgvector…"
              aria-label="Recherche en langage naturel"
              // Hors déploiement le champ est rogné, donc invisible : le
              // retirer du parcours clavier évite un arrêt sur du vide.
              tabIndex={expanded ? undefined : -1}
              className="w-full rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-300"
            />
          </div>
          <button
            type={expanded ? "submit" : "button"}
            onClick={expanded ? undefined : toggle}
            aria-label={expanded ? "Lancer la recherche" : "Ouvrir la recherche"}
            aria-expanded={expanded}
            className="ml-1 rounded-md p-1.5 text-zinc-600 transition-colors hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            <SearchIcon />
          </button>
        </form>
      </div>
    </header>
  );
}
