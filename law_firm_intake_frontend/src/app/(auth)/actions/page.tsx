import { api } from "@/lib/api";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ActionsPage({ searchParams }: { searchParams?: { [key: string]: string | string[] | undefined } }) {
  const clientId = (searchParams?.client_id as string) || "";
  const status = (searchParams?.status as string) || "";
  const priority = (searchParams?.priority as string) || "";
  const [actions, clients] = await Promise.all([
    api.staff.actions(clientId ? { client_id: Number(clientId) } : undefined),
    api.staff.clients(),
  ]);
  const items = actions.filter(a => (
    (!status || a.status === status) &&
    (!priority || (a.priority || '').toLowerCase() === priority.toLowerCase())
  ));
  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Actions</h1>
        <Link href="/actions/new" className="px-3 py-2 rounded bg-black text-white text-sm">New Action</Link>
      </div>
      <form className="mb-4 grid grid-cols-1 sm:grid-cols-4 gap-3" method="get">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Client</label>
          <select name="client_id" defaultValue={clientId || ""} className="w-full border rounded px-2 py-2 text-sm">
            <option value="">All Clients</option>
            {clients.map(cl => (
              <option key={cl.id} value={cl.id}>{[cl.first_name, cl.last_name].filter(Boolean).join(' ') || `Client #${cl.id}`}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select name="status" defaultValue={status || ""} className="w-full border rounded px-2 py-2 text-sm">
            <option value="">All</option>
            <option value="pending">pending</option>
            <option value="in_progress">in_progress</option>
            <option value="done">done</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Priority</label>
          <select name="priority" defaultValue={priority || ""} className="w-full border rounded px-2 py-2 text-sm">
            <option value="">All</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button type="submit" className="px-3 py-2 border rounded text-sm">Filter</button>
          <a href="/actions" className="px-3 py-2 border rounded text-sm">Reset</a>
        </div>
      </form>
      <div className="overflow-x-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-2">Title</th>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Priority</th>
              <th className="px-4 py-2">Due</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                  No actions found. <Link href="/actions/new" className="text-blue-600 hover:underline">Add your first action</Link>.
                </td>
              </tr>
            ) : (
              items.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="px-4 py-2">
                    <Link href={`/actions/${a.id}`} className="text-blue-600 hover:underline">{a.title}</Link>
                  </td>
                  <td className="px-4 py-2">{a.case_title ?? '—'}</td>
                  <td className="px-4 py-2">{a.status}</td>
                  <td className="px-4 py-2">{a.priority ?? '—'}</td>
                  <td className="px-4 py-2">{a.due_date ? new Date(a.due_date).toLocaleString() : '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
