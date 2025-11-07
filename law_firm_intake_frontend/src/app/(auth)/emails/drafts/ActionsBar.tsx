"use client";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function ActionsBar({ id, canSend }: { id: number; canSend: boolean }) {
  const onSend = async () => {
    const res = await fetch(`/api/email/drafts/${id}/send`, { method: 'POST' });
    if (res.ok) {
      toast.success('Draft sent');
      setTimeout(() => location.reload(), 300);
    } else {
      toast.error('Failed to send');
    }
  };
  const onDelete = async () => {
    const res = await fetch(`/api/email/drafts/${id}`, { method: 'DELETE' });
    if (res.ok) {
      toast.success('Draft deleted');
      setTimeout(() => history.back(), 300);
    } else {
      toast.error('Failed to delete');
    }
  };
  return (
    <div className="flex gap-2">
      {canSend && (<Button onClick={onSend}>Send</Button>)}
      <Button variant="destructive" onClick={onDelete}>Delete</Button>
    </div>
  );
}
