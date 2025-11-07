import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import EditForm from "./EditForm";

export const dynamic = "force-dynamic";

export default async function EditClientPage({ params }: { params: { id: string } }) {
  const cl = await api.staff.clientById(Number(params.id));
  return (
    <div className="max-w-2xl mx-auto p-6">
      <Card>
        <CardHeader><CardTitle>Edit Client</CardTitle></CardHeader>
        <CardContent>
          <EditForm id={Number(params.id)} defaults={cl} />
        </CardContent>
      </Card>
    </div>
  );
}
