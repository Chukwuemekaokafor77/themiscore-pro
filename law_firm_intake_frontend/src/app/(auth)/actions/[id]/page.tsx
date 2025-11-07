import { api } from "@/lib/api";

type Props = { params: { id: string } };

export const dynamic = "force-dynamic";

export default async function ActionDetailPage({ params }: Props) {
  const action = await api.staff.actionById(Number(params.id));
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Action: {action.title}</h1>
      <section className="rounded border bg-white p-4 text-sm space-y-2">
        <div><span className="text-gray-500">Status:</span> {action.status}</div>
        <div><span className="text-gray-500">Priority:</span> {action.priority ?? '—'}</div>
        <div><span className="text-gray-500">Due:</span> {action.due_date ? new Date(action.due_date).toLocaleString() : '—'}</div>
        <div><span className="text-gray-500">Case:</span> {action.case?.title ?? '—'}</div>
      </section>
      <section className="rounded border bg-white p-4">
        <div className="text-gray-500 text-sm mb-2">Description</div>
        <div className="prose max-w-none whitespace-pre-wrap text-sm">{action.description ?? '—'}</div>
      </section>
    </div>
  );
}
