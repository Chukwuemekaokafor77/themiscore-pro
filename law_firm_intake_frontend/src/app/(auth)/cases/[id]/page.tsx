import { api } from "@/lib/api";
import AddNoteForm from "@/app/(auth)/cases/[id]/AddNoteForm";
import { redirect } from "next/navigation";
import AddActionInline from "./AddActionInline";

type Props = { params: { id: string } };

export const dynamic = "force-dynamic";

export default async function CaseDetailPage({ params }: Props) {
  const id = Number(params.id);
  if (!Number.isFinite(id) || id <= 0) {
    redirect("/cases");
  }
  let c;
  try {
    c = await api.staff.caseById(id);
  } catch (e) {
    redirect("/cases");
  }
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Case: {c.title}</h1>

      <section className="rounded border bg-white p-4 text-sm grid gap-2">
        <div><span className="text-gray-500">Status:</span> {c.status}</div>
        <div><span className="text-gray-500">Priority:</span> {c.priority ?? '—'}</div>
        <div><span className="text-gray-500">Created:</span> {c.created_at ? new Date(c.created_at).toLocaleString() : '—'}</div>
        <div><span className="text-gray-500">Client:</span> {[c.client?.first_name, c.client?.last_name].filter(Boolean).join(' ') || '—'} ({c.client?.email || '—'})</div>
        {(c.category || c.department) && (
          <div className="flex items-center gap-3 flex-wrap">
            {c.category && (
              <span className="inline-flex items-center gap-2 px-2 py-1 rounded border text-xs">
                <span className="text-gray-500">Category</span>
                <span className="font-medium">{c.category}</span>
                {typeof c.confidence === 'number' && (
                  <span className="text-gray-500">({Math.round(c.confidence * 100)}%)</span>
                )}
              </span>
            )}
            {c.department && (
              <span className="inline-flex items-center gap-2 px-2 py-1 rounded border text-xs">
                <span className="text-gray-500">Department</span>
                <span className="font-medium">{c.department}</span>
              </span>
            )}
          </div>
        )}
        <div>
          <div className="text-gray-500">Description</div>
          <div className="whitespace-pre-wrap">{c.description || '—'}</div>
        </div>
      </section>

      {c.transcripts && c.transcripts.length > 0 && (
        <section className="rounded border bg-white p-4 text-sm grid gap-3">
          <h2 className="font-medium">Transcripts</h2>
          <div className="grid gap-3">
            {c.transcripts.map(t => (
              <div key={t.id} className="border rounded p-3 bg-gray-50">
                <div className="text-xs text-gray-500 mb-2">{t.created_at ? new Date(t.created_at).toLocaleString() : ''}</div>
                <div className="whitespace-pre-wrap">{t.text || ''}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {c.automations && (
        <section className="rounded border bg-white p-4 text-sm">
          <h2 className="font-medium mb-3">Automations</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded border p-3 text-center">
              <div className="text-2xl font-semibold">{c.automations.letters ?? 0}</div>
              <div className="text-xs text-gray-500">Letters</div>
            </div>
            <div className="rounded border p-3 text-center">
              <div className="text-2xl font-semibold">{c.automations.tasks ?? 0}</div>
              <div className="text-xs text-gray-500">Tasks</div>
            </div>
            <div className="rounded border p-3 text-center">
              <div className="text-2xl font-semibold">{c.automations.deadlines ?? 0}</div>
              <div className="text-xs text-gray-500">Deadlines</div>
            </div>
            <div className="rounded border p-3 text-center">
              <div className="text-2xl font-semibold">{c.automations.documents ?? 0}</div>
              <div className="text-xs text-gray-500">Documents</div>
            </div>
          </div>
        </section>
      )}

      <section className="rounded border bg-white p-4">
        <AddNoteForm caseId={id} />
      </section>

      <section className="rounded border bg-white p-4">
        <h2 className="font-medium mb-3">Add Action</h2>
        <AddActionInline caseId={id} />
      </section>
    </div>
  );
}

