"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const links = [
    { href: "/portal", label: "Dashboard" },
    { href: "/portal/messages", label: "Messages" },
    { href: "/portal/documents", label: "Documents" },
    { href: "/portal/invoices", label: "Invoices" },
    { href: "/portal/payments", label: "Payments" },
    { href: "/portal/timeline", label: "Timeline" },
    { href: "/portal/intake", label: "Voice Intake" },
  ];
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="w-64 shrink-0 border-r bg-[--sidebar] text-[--sidebar-foreground]">
          <div className="px-4 py-5 border-b border-[--sidebar-border]">
            <div className="text-base font-semibold">Client Portal</div>
            <div className="text-xs opacity-75">Welcome</div>
          </div>
          <nav className="p-2 text-sm">
            <ul className="space-y-1">
              {links.map((l) => {
                const active = pathname === l.href;
                return (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className={
                        `block rounded px-3 py-2 transition-colors ` +
                        (active
                          ? "bg-[--sidebar-primary] text-[--sidebar-primary-foreground]"
                          : "hover:bg-[--sidebar-accent] text-[--sidebar-foreground]")
                      }
                    >
                      {l.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </aside>
        <main className="flex-1 min-w-0">
          <header className="sticky top-0 z-10 bg-card/90 backdrop-blur border-b">
            <div className="px-4 py-3 flex items-center justify-between gap-3">
              <div className="text-sm text-muted-foreground">Secure Client Portal</div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <div className="text-xs text-muted-foreground hidden sm:block">Powered by ThemisCore</div>
              </div>
            </div>
          </header>
          <div className="p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
