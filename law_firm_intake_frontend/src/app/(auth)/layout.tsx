"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import TeamLogoutButton from "./TeamLogoutButton";
import ThemeToggle from "@/components/ThemeToggle";

export const dynamic = "force-dynamic";

export default function AuthShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const links = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/cases", label: "Cases" },
    { href: "/clients", label: "Clients" },
    { href: "/actions", label: "Actions" },
    { href: "/documents", label: "Documents" },
    { href: "/calendar", label: "Calendar" },
    { href: "/billing", label: "Billing" },
    { href: "/settings", label: "Settings" },
  ];
  const tools = [
    { href: "/transcribe", label: "Transcribe" },
    { href: "/emails/drafts", label: "Emails" },
  ];
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="hidden md:block w-64 border-r bg-[--sidebar] text-[--sidebar-foreground]">
          <div className="px-4 py-5 border-b border-[--sidebar-border]">
            <div className="text-base font-semibold">Law Firm Console</div>
            <div className="text-xs opacity-75">Staff</div>
          </div>
          <nav className="p-2 text-sm">
            <ul className="space-y-1">
              {links.map((l) => {
                const active = pathname === l.href;
                return (
                  <li key={l.href}>
                    <Link
                      className={
                        `block rounded px-3 py-2 transition-colors ` +
                        (active
                          ? "bg-[--sidebar-primary] text-[--sidebar-primary-foreground]"
                          : "hover:bg-[--sidebar-accent] text-[--sidebar-foreground]")
                      }
                      href={l.href}
                    >
                      {l.label}
                    </Link>
                  </li>
                );
              })}
              <li className="pt-2"><div className="px-3 text-xs uppercase text-[--sidebar-accent-foreground]/80">Tools</div></li>
              {tools.map((l) => {
                const active = pathname === l.href;
                return (
                  <li key={l.href}>
                    <Link
                      className={
                        `block rounded px-3 py-2 transition-colors ` +
                        (active
                          ? "bg-[--sidebar-primary] text-[--sidebar-primary-foreground]"
                          : "hover:bg-[--sidebar-accent] text-[--sidebar-foreground]")
                      }
                      href={l.href}
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
            <div className="flex items-center justify-between px-4 py-3 gap-3">
              <div className="flex items-center gap-3">
                <span className="md:hidden rounded border px-2 py-1 text-sm select-none">Menu</span>
                <div className="text-sm text-muted-foreground">Staff Console</div>
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <TeamLogoutButton />
              </div>
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
