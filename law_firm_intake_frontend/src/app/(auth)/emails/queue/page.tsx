import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function EmailQueuePage({ searchParams }: { searchParams?: { [key: string]: string | string[] | undefined } }) {
  const status = (searchParams?.status as string) || "";
  const items = await api.staff.emailQueue(status ? { status: status as any } : undefined);

  async function retry(formData: FormData) {
    "use server";
    const id = Number(formData.get("id"));
    if (!Number.isFinite(id) || id <= 0) return;
    await api.staff.retryEmailQueue(id);
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Email Queue</h1>
      </div>
      <form className="mb-4 grid grid-cols-1 sm:grid-cols-4 gap-3" method="get">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select name="status" defaultValue={status || ""} className="w-full border rounded px-2 py-2 text-sm">
            <option value="">All</option>
            <option value="pending">pending</option>
            <option value="sent">sent</option>
            <option value="failed">failed</option>
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button type="submit" className="px-3 py-2 border rounded text-sm">Filter</button>
          <a href="/emails/queue" className="px-3 py-2 border rounded text-sm">Reset</a>
        </div>
      </form>

      <div className="overflow-x-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-2">Subject</th>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Send After</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Attempts</th>
              <th className="px-4 py-2">Last Error</th>
              <th className="px-4 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-500">No queued emails</td>
              </tr>
            ) : (
              items.map((e: any) => (
                <tr key={e.id} className="border-top">
                  <td className="px-4 py-2">{e.subject}</td>
                  <td className="px-4 py-2">{e.case_title || (e.case_id ? `Case #${e.case_id}` : '—')}</td>
                  <td className="px-4 py-2">{e.send_after ? new Date(e.send_after).toLocaleString() : '—'}</td>
                  <td className="px-4 py-2">{e.status}</td>
                  <td className="px-4 py-2">{e.attempts}</td>
                  <td className="px-4 py-2 max-w-xs truncate" title={e.last_error || ''}>{e.last_error || '—'}</td>
                  <td className="px-4 py-2">
                    {(e.status === 'failed' || e.status === 'pending') && (
                      <form action={retry}>
                        <input type="hidden" name="id" value={e.id} />
                        <button type="submit" className="px-2 py-1 border rounded text-xs">Retry</button>
                      </form>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
