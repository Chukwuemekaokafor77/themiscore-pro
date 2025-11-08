import { redirect } from "next/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PortalInvoicesPage() {
  let invoices;
  try {
    invoices = await api.portal.invoices();
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/portal/login");
    throw e;
  }
  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Invoices</h1>
      <div className="overflow-x-auto rounded-xl border bg-card shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Invoice #</th>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Total</th>
              <th className="px-4 py-2">Balance Due</th>
              <th className="px-4 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id} className="border-t">
                <td className="px-4 py-2">{inv.invoice_number ?? "—"}</td>
                <td className="px-4 py-2">{inv.case.title ?? "—"}</td>
                <td className="px-4 py-2">{inv.status ?? "—"}</td>
                <td className="px-4 py-2">${inv.total_amount.toFixed(2)}</td>
                <td className="px-4 py-2">${inv.balance_due.toFixed(2)}</td>
                <td className="px-4 py-2">{inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
