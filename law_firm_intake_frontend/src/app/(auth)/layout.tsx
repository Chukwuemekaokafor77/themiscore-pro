import Link from "next/link";

export const dynamic = "force-dynamic";

export default function AuthShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="flex min-h-screen">
        <aside className="hidden md:block w-64 border-r bg-white">
          <div className="px-4 py-5 border-b">
            <div className="text-lg font-semibold">Law Firm Console</div>
            <div className="text-xs text-gray-500">Staff</div>
          </div>
          <nav className="p-3 text-sm">
            <ul className="space-y-1">
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/dashboard">Dashboard</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/cases">Cases</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/clients">Clients</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/actions">Actions</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/documents">Documents</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/calendar">Calendar</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/billing">Billing</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/settings">Settings</Link></li>
              <li className="pt-2"><div className="px-3 text-xs uppercase text-gray-400">Tools</div></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/transcribe">Transcribe</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" href="/emails/drafts">Emails</Link></li>
            </ul>
          </nav>
        </aside>
        <main className="flex-1 min-w-0">
          <header className="sticky top-0 z-10 bg-white border-b">
            <div className="flex items-center gap-3 px-4 py-3">
              <span className="md:hidden rounded border px-2 py-1 text-sm select-none">Menu</span>
              <div className="text-sm text-gray-500">Staff Console</div>
            </div>
          </header>
          <div className="p-4 md:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
