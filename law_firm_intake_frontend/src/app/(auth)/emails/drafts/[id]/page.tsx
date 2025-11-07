import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ActionsBar from "../ActionsBar";

export const dynamic = "force-dynamic";

export default async function EmailDraftDetail({ params }: { params: { id: string } }) {
  const draft = await api.staff.emailDraftById(Number(params.id));
  return (
    <div className="max-w-4xl mx-auto p-6">
      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>{draft.subject}</CardTitle>
          <ActionsBar id={draft.id} canSend={draft.status === 'draft'} />
        </CardHeader>
        <CardContent className="space-y-3">
          <div><span className="text-sm text-gray-500">To:</span> <span>{draft.to ?? '—'}</span></div>
          <div className="border rounded p-3 whitespace-pre-wrap bg-white">{draft.body}</div>
        </CardContent>
      </Card>
    </div>
  );
}
