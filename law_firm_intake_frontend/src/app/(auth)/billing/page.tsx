import { api } from "@/lib/api";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function BillingPage() {
  let data;
  try {
    data = await api.staff.billing();
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/login");
    throw e;
  }
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-semibold">Billing</h1>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Recent Invoices</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr>
              <th className="px-4 py-2">Invoice #</th>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Total</th>
              <th className="px-4 py-2">Balance Due</th>
              <th className="px-4 py-2">Created</th>
            </tr></thead>
            <tbody>
              {data.invoices.map((i) => (
                <tr key={i.id} className="border-t">
                  <td className="px-4 py-2">{i.invoice_number ?? '—'}</td>
                  <td className="px-4 py-2">{i.case?.title ?? '—'}</td>
                  <td className="px-4 py-2">{i.status ?? '—'}</td>
                  <td className="px-4 py-2">${'{'}i.total_amount.toFixed(2){'}'}</td>
                  <td className="px-4 py-2">${'{'}i.balance_due.toFixed(2){'}'}</td>
                  <td className="px-4 py-2">{i.created_at ? new Date(i.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Recent Time Entries</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Hours</th>
              <th className="px-4 py-2">Rate</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Created</th>
            </tr></thead>
            <tbody>
              {data.time_entries.map((t) => (
                <tr key={t.id} className="border-t">
                  <td className="px-4 py-2">{t.case?.title ?? '—'}</td>
                  <td className="px-4 py-2">{t.hours.toFixed(2)}</td>
                  <td className="px-4 py-2">${'{'}t.rate.toFixed(2){'}'}</td>
                  <td className="px-4 py-2">${'{'}(t.hours*t.rate).toFixed(2){'}'}</td>
                  <td className="px-4 py-2">{t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Recent Expenses</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2">Created</th>
            </tr></thead>
            <tbody>
              {data.expenses.map((e) => (
                <tr key={e.id} className="border-t">
                  <td className="px-4 py-2">{e.case?.title ?? '—'}</td>
                  <td className="px-4 py-2">${'{'}e.amount.toFixed(2){'}'}</td>
                  <td className="px-4 py-2">{e.description ?? '—'}</td>
                  <td className="px-4 py-2">{e.created_at ? new Date(e.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
