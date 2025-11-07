import { api } from "@/lib/api";
import { redirect } from "next/navigation";

type Props = { params: { id: string } };

export const dynamic = "force-dynamic";

export default async function ClientDetailPage({ params }: Props) {
  const idNum = Number(params.id);
  if (!Number.isFinite(idNum) || idNum <= 0) {
    redirect("/clients");
  }
  let client;
  try {
    client = await api.staff.clientById(idNum);
  } catch (e) {
    redirect("/clients");
  }
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Client: {[client.first_name, client.last_name].filter(Boolean).join(" ")}</h1>
      <section className="rounded border bg-white p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div><div className="text-gray-500">Email</div><div>{client.email || '—'}</div></div>
          <div><div className="text-gray-500">Phone</div><div>{client.phone || '—'}</div></div>
          <div className="sm:col-span-2"><div className="text-gray-500">Address</div><div>{client.address || '—'}</div></div>
        </div>
      </section>
      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Cases</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr><th className="px-4 py-2">Title</th><th className="px-4 py-2">Status</th><th className="px-4 py-2">Created</th></tr></thead>
            <tbody>
              {client.cases.map((c) => (
                <tr key={c.id} className="border-t">
                  <td className="px-4 py-2">{c.title}</td>
                  <td className="px-4 py-2">{c.status}</td>
                  <td className="px-4 py-2">{c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
