import Link from "next/link";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 border-r p-4 space-y-3">
        <div className="text-lg font-semibold">Client Portal</div>
        <nav className="flex flex-col gap-2 text-sm">
          <Link className="hover:underline" href="/portal">Dashboard</Link>
          <Link className="hover:underline" href="/portal/messages">Messages</Link>
          <Link className="hover:underline" href="/portal/documents">Documents</Link>
          <Link className="hover:underline" href="/portal/invoices">Invoices</Link>
          <Link className="hover:underline" href="/portal/payments">Payments</Link>
          <Link className="hover:underline" href="/portal/timeline">Timeline</Link>
        </nav>
      </aside>
      <main className="flex-1">{children}</main>
    </div>
  );
}
