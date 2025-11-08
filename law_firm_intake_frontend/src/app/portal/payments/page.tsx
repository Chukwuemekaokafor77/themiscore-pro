import { redirect } from "next/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PortalPaymentsPage() {
  let payments;
  try {
    payments = await api.portal.payments();
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/portal/login");
    throw e;
  }
  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Payments</h1>
      <div className="overflow-x-auto rounded-xl border bg-card shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Method</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Reference</th>
              <th className="px-4 py-2">Invoice #</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id} className="border-t">
                <td className="px-4 py-2">{p.payment_date ? new Date(p.payment_date).toLocaleDateString() : "—"}</td>
                <td className="px-4 py-2">${p.amount.toFixed(2)}</td>
                <td className="px-4 py-2">{p.payment_method ?? "—"}</td>
                <td className="px-4 py-2">{p.status ?? "—"}</td>
                <td className="px-4 py-2">{p.reference_number ?? "—"}</td>
                <td className="px-4 py-2">{p.invoice.invoice_number ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
