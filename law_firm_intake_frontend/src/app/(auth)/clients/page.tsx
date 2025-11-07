import { api } from "@/lib/api";
import { redirect } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ClientsPage() {
  let clients;
  try {
    clients = await api.staff.clients();
  } catch (e: any) {
    if (e?.message === "unauthorized") redirect("/login");
    throw e;
  }
  return (
    <div className="max-w-7xl mx-auto p-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Clients</CardTitle>
            <Link href="/clients/new" className="px-3 py-2 rounded bg-black text-white text-sm">Add Client</Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Cases</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clients.map((cl) => (
                  <TableRow key={cl.id}>
                    <TableCell>
                      <Link href={`/clients/${cl.id}`} className="text-blue-600 hover:underline">
                        {[cl.first_name, cl.last_name].filter(Boolean).join(" ") || "—"}
                      </Link>
                    </TableCell>
                    <TableCell>{cl.email ?? "—"}</TableCell>
                    <TableCell>{cl.phone ?? "—"}</TableCell>
                    <TableCell>
                      <Link href={`/cases?client_id=${cl.id}`} className="text-blue-600 hover:underline">View</Link>
                    </TableCell>
                    <TableCell>
                      <Link href={`/actions?client_id=${cl.id}`} className="text-blue-600 hover:underline">View</Link>
                    </TableCell>
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
