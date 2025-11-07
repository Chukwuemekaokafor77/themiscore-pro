import { api } from "@/lib/api";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let data;
  try {
    data = await api.staff.dashboard();
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/login");
    throw e;
  }
  const s = data.stats;
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded border p-4 bg-white"><div className="text-sm text-gray-500">Active Cases</div><div className="text-2xl font-semibold">{s.active_cases}</div></div>
        <div className="rounded border p-4 bg-white"><div className="text-sm text-gray-500">Active Clients</div><div className="text-2xl font-semibold">{s.active_clients}</div></div>
        <div className="rounded border p-4 bg-white"><div className="text-sm text-gray-500">Pending Actions</div><div className="text-2xl font-semibold">{s.pending_actions}</div></div>
        <div className="rounded border p-4 bg-white"><div className="text-sm text-gray-500">Documents</div><div className="text-2xl font-semibold">{s.documents_count}</div></div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded border bg-white">
          <div className="px-4 py-3 border-b font-medium">Recent Cases</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-left"><tr><th className="px-4 py-2">Title</th><th className="px-4 py-2">Client</th><th className="px-4 py-2">Created</th></tr></thead>
              <tbody>
                {data.recent_cases.map((c) => (
                  <tr key={c.id} className="border-t">
                    <td className="px-4 py-2">{c.title}</td>
                    <td className="px-4 py-2">{c.client.name ?? "—"}</td>
                    <td className="px-4 py-2">{c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="rounded border bg-white">
          <div className="px-4 py-3 border-b font-medium">Upcoming Actions</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-left"><tr><th className="px-4 py-2">Title</th><th className="px-4 py-2">Due</th><th className="px-4 py-2">Status</th></tr></thead>
              <tbody>
                {data.upcoming_actions.map((a) => (
                  <tr key={a.id} className="border-t">
                    <td className="px-4 py-2">{a.title}</td>
                    <td className="px-4 py-2">{a.due_date ? new Date(a.due_date).toLocaleString() : "—"}</td>
                    <td className="px-4 py-2">{a.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Upcoming Deadlines (30 days)</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr><th className="px-4 py-2">Name</th><th className="px-4 py-2">Due</th></tr></thead>
            <tbody>
              {data.upcoming_deadlines.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="px-4 py-2">{d.name}</td>
                  <td className="px-4 py-2">{d.due_date ? new Date(d.due_date).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
