import ClientRouter from "./client";

// Under `output: "export"`, Next 16 requires every reachable path to be listed
// here — an empty slug alone only covers `/`, so hits on `/chat`, `/search`, etc.
// 500 at request time. Vault-specific pages are reached via client-side <Link>
// so they don't need static entries.
export function generateStaticParams() {
  return [
    { slug: [] as string[] },
    { slug: ["chat"] },
    { slug: ["search"] },
    { slug: ["settings"] },
    { slug: ["vaults"] },
  ];
}

export default function CatchAllPage() {
  return <ClientRouter />;
}
