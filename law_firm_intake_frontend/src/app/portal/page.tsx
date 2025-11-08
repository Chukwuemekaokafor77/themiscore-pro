import { api } from "@/lib/api";
import { redirect } from "next/navigation";
import VoiceIntake from "./VoiceIntake";
import PortalLogoutButton from "./PortalLogoutButton";

export const dynamic = "force-dynamic";

export default async function PortalDashboardPage() {
  let documents = [] as Awaited<ReturnType<typeof api.portal.documents>>;
  let invoices = [] as Awaited<ReturnType<typeof api.portal.invoices>>;
  let payments = [] as Awaited<ReturnType<typeof api.portal.payments>>;
  try {
    const [docs, invs, pays] = await Promise.all([
      api.portal.documents(),
      api.portal.invoices(),
      api.portal.payments(),
    ]);
    documents = docs;
    invoices = invs;
    payments = pays;
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/login");
    throw e;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Client Portal</h1>
        <PortalLogoutButton />
      </div>

      {/* Compact stats */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border bg-card shadow-sm p-4">
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <span aria-hidden>📄</span> Documents
          </div>
          <div className="text-2xl font-semibold mt-1">{documents.length}</div>
        </div>
        <div className="rounded-xl border bg-card shadow-sm p-4">
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <span aria-hidden>🧾</span> Invoices
          </div>
          <div className="text-2xl font-semibold mt-1">{invoices.length}</div>
        </div>
        <div className="rounded-xl border bg-card shadow-sm p-4">
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <span aria-hidden>💳</span> Payments
          </div>
          <div className="text-2xl font-semibold mt-1">{payments.length}</div>
        </div>
      </section>

      <VoiceIntake />

      <section className="rounded-xl border bg-card shadow-sm">
        <div className="px-4 py-3 border-b font-medium">Recent Documents</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.slice(0, 10).map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="px-4 py-2">{d.document?.name ?? "—"}</td>
                  <td className="px-4 py-2">{d.document?.file_type ?? "—"}</td>
                  <td className="px-4 py-2">{d.document?.created_at ? new Date(d.document.created_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
              {documents.length === 0 && (
                <tr><td className="px-4 py-6 text-gray-500" colSpan={3}>No documents yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3 border-t">
          <a href="/portal/documents" className="inline-flex items-center px-3 py-2 bg-primary text-primary-foreground hover:opacity-90 rounded-md text-sm">View all documents</a>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border bg-card shadow-sm">
          <div className="px-4 py-3 border-b font-medium">Recent Invoices</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-muted-foreground"><tr><th className="px-4 py-2">Invoice #</th><th className="px-4 py-2">Amount</th><th className="px-4 py-2">Status</th></tr></thead>
              <tbody>
                {invoices.slice(0, 5).map((i) => (
                  <tr key={i.id} className="border-t">
                    <td className="px-4 py-2">{i.invoice_number ?? i.id}</td>
                    <td className="px-4 py-2">{typeof i.total_amount === 'number' ? i.total_amount.toFixed(2) : i.total_amount ?? '—'}</td>
                    <td className="px-4 py-2">{i.status ?? '—'}</td>
                  </tr>
                ))}
                {invoices.length === 0 && (
                  <tr><td className="px-4 py-6 text-gray-500" colSpan={3}>No invoices yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="rounded-xl border bg-card shadow-sm">
          <div className="px-4 py-3 border-b font-medium">Recent Payments</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-muted-foreground"><tr><th className="px-4 py-2">Amount</th><th className="px-4 py-2">Date</th><th className="px-4 py-2">Status</th></tr></thead>
              <tbody>
                {payments.slice(0, 5).map((p) => (
                  <tr key={p.id} className="border-t">
                    <td className="px-4 py-2">{typeof p.amount === 'number' ? p.amount.toFixed(2) : p.amount ?? '—'}</td>
                    <td className="px-4 py-2">{p.payment_date ? new Date(p.payment_date).toLocaleString() : '—'}</td>
                    <td className="px-4 py-2">{p.status ?? '—'}</td>
                  </tr>
                ))}
                {payments.length === 0 && (
                  <tr><td className="px-4 py-6 text-gray-500" colSpan={3}>No payments yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

