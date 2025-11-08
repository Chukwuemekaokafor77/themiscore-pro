import { redirect } from "next/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PortalDocumentsPage() {
  let accesses;
  try {
    accesses = await api.portal.documents();
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/portal/login");
    throw e;
  }
  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Documents</h1>
      <div className="overflow-x-auto rounded-xl border bg-card shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Uploaded</th>
              <th className="px-4 py-2">Access Granted</th>
            </tr>
          </thead>
          <tbody>
            {accesses.map((a) => (
              <tr key={a.id} className="border-t">
                <td className="px-4 py-2">{a.document.name ?? "—"}</td>
                <td className="px-4 py-2">{a.document.file_type ?? "—"}</td>
                <td className="px-4 py-2">{a.document.created_at ? new Date(a.document.created_at).toLocaleString() : "—"}</td>
                <td className="px-4 py-2">{a.granted_at ? new Date(a.granted_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

