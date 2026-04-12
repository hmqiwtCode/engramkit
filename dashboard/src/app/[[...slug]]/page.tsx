import ClientRouter from "./client";

export function generateStaticParams() {
  return [{ slug: [] }];
}

export default function CatchAllPage() {
  return <ClientRouter />;
}
