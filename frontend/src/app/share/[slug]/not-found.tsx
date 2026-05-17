import Link from "next/link";

export default function NotFound() {
  return (
    <main className="container mx-auto max-w-xl pt-32 pb-20 px-6 text-center">
      <h1 className="text-2xl font-bold mb-3">This share link isn&apos;t live</h1>
      <p className="text-sm text-muted-foreground mb-6">
        It may have been revoked, or it never existed.
      </p>
      <Link href="/" className="rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium">
        Home
      </Link>
    </main>
  );
}
