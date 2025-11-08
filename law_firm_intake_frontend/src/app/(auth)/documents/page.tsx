import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DocumentsPage() {
  const docs = await api.staff.documents();
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Documents</h1>

      <section className="rounded-xl border bg-card shadow-sm p-4">
        <h2 className="font-medium mb-3">Upload Document</h2>
        <form id="upload" action="/api/documents/upload" method="post" encType="multipart/form-data" className="grid gap-3 max-w-xl">
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Name (optional)</label>
            <input type="text" name="name" className="w-full border border-input rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Case ID (optional)</label>
            <input type="number" name="case_id" className="w-full border border-input rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">File</label>
            <input type="file" name="file" required className="w-full" />
          </div>
          <button type="submit" className="px-4 py-2 bg-primary text-primary-foreground hover:opacity-90 rounded-md">Upload</button>
          <p className="text-xs text-muted-foreground">After upload, refresh the page to see the new document.</p>
        </form>
      </section>

      <section className="rounded-xl border bg-card shadow-sm">
        <div className="px-4 py-3 border-b font-medium">All Documents</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-muted-foreground"><tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Size</th>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Created</th>
            </tr></thead>
            <tbody>
              {docs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
                    No documents found. <a href="#upload" className="text-blue-600 hover:underline">Add your first document</a>.
                  </td>
                </tr>
              ) : (
                docs.map((d) => (
                  <tr key={d.id} className="border-t">
                    <td className="px-4 py-2">{d.name}</td>
                    <td className="px-4 py-2">{d.file_type ?? '—'}</td>
                    <td className="px-4 py-2">{d.file_size ? `${(d.file_size/1024).toFixed(1)} KB` : '—'}</td>
                    <td className="px-4 py-2">{d.case?.title ?? '—'}</td>
                    <td className="px-4 py-2">{d.created_at ? new Date(d.created_at).toLocaleString() : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

