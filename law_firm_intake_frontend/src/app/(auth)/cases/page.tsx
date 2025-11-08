import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function CasesPage({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const sp = await searchParams;
  const clientId = (sp?.client_id as string) || "";
  const status = (sp?.status as string) || "";
  const priority = (sp?.priority as string) || ""; // UI-only filter

  const [casesPage, clients] = await Promise.all([
    api.staff.cases({ per_page: 20, sort: "-created_at", client_id: clientId || undefined, status: status || undefined }),
    api.staff.clients(),
  ]);

  const items = priority && priority !== "all"
    ? casesPage.items.filter((c) => (c.priority || "").toLowerCase() === priority.toLowerCase())
    : casesPage.items;
  return (
    <div className="max-w-7xl mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Cases</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="mb-4 grid grid-cols-1 sm:grid-cols-4 gap-3" method="get">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Client</label>
              <select name="client_id" defaultValue={clientId || ""} className="w-full border border-input rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="">All Clients</option>
                {clients.map(cl => (
                  <option key={cl.id} value={cl.id}>{[cl.first_name, cl.last_name].filter(Boolean).join(' ') || `Client #${cl.id}`}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Status</label>
              <select name="status" defaultValue={status || ""} className="w-full border border-input rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="">All status</option>
                <option value="open">open</option>
                <option value="in_progress">in_progress</option>
                <option value="closed">closed</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Priority</label>
              <select name="priority" defaultValue={priority || ""} className="w-full border border-input rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="">All</option>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </div>
            <div className="flex items-end gap-2">
              <button type="submit" className="px-3 py-2 bg-primary text-primary-foreground hover:opacity-90 rounded-md text-sm">Filter</button>
              <a href="/cases" className="px-3 py-2 border border-input rounded-md text-sm">Reset</a>
            </div>
          </form>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <Link href={`/cases/${c.id}`} className="text-blue-600 hover:underline">{c.title}</Link>
                    </TableCell>
                    <TableCell>
                      {c.client?.id ? (
                        <Link href={`/clients/${c.client.id}`} className="text-blue-600 hover:underline">
                          {[c.client.first_name, c.client.last_name].filter(Boolean).join(' ') || `Client #${c.client.id}`}
                        </Link>
                      ) : (
                        [c.client.first_name, c.client.last_name].filter(Boolean).join(' ') || '—'
                      )}
                    </TableCell>
                    <TableCell>{c.status}</TableCell>
                    <TableCell>{c.priority}</TableCell>
                    <TableCell>{c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

