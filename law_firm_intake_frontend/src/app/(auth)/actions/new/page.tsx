"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const dynamic = "force-dynamic";

export default function NewActionPage() {
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {
      title: String(fd.get('title') || ''),
      description: (fd.get('description') || '') as string,
      action_type: (fd.get('action_type') || undefined) as string | undefined,
      status: (fd.get('status') || 'pending') as string,
      priority: (fd.get('priority') || 'medium') as string,
      due_date: (fd.get('due_date') || undefined) as string | undefined,
      assigned_to_id: fd.get('assigned_to_id') ? Number(fd.get('assigned_to_id')) : undefined,
      case_id: fd.get('case_id') ? Number(fd.get('case_id')) : undefined,
    };
    const res = await fetch('/api/actions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (res.ok) {
      toast.success('Action created');
      const data = await res.json();
      location.href = `/actions/${data.id}`;
    } else {
      toast.error('Failed to create action');
    }
  };
  return (
    <div className="max-w-2xl mx-auto p-6">
      <Card>
        <CardHeader><CardTitle>New Action</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="grid gap-3">
            <div>
              <Label>Title</Label>
              <Input name="title" required />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea name="description" rows={4} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Status</Label>
                <Input name="status" placeholder="pending|in_progress|done" />
              </div>
              <div>
                <Label>Priority</Label>
                <Input name="priority" placeholder="low|medium|high" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Due Date</Label>
                <Input name="due_date" type="date" />
              </div>
              <div>
                <Label>Case ID</Label>
                <Input name="case_id" type="number" />
              </div>
            </div>
            <div>
              <Label>Assigned To (User ID)</Label>
              <Input name="assigned_to_id" type="number" />
            </div>
            <div className="pt-2">
              <Button type="submit">Create</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
