"use client";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function AddActionInline({ caseId }: { caseId: number }) {
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {
      title: String(fd.get("title") || ""),
      description: (fd.get("description") || "") as string,
      status: (fd.get("status") || "pending") as string,
      priority: (fd.get("priority") || "medium") as string,
      due_date: (fd.get("due_date") || undefined) as string | undefined,
      case_id: caseId,
    };
    const res = await fetch("/api/actions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      toast.success("Action created");
      (e.currentTarget as HTMLFormElement).reset();
      window.location.reload();
    } else {
      toast.error("Failed to create action");
    }
  };
  return (
    <form onSubmit={onSubmit} className="grid gap-2 text-sm">
      <div>
        <Label>Title</Label>
        <Input name="title" required />
      </div>
      <div>
        <Label>Description</Label>
        <Textarea name="description" rows={3} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label>Status</Label>
          <Input name="status" placeholder="pending|in_progress|done" />
        </div>
        <div>
          <Label>Priority</Label>
          <Input name="priority" placeholder="low|medium|high" />
        </div>
      </div>
      <div>
        <Label>Due Date</Label>
        <Input name="due_date" type="date" />
      </div>
      <div className="pt-1">
        <Button type="submit" size="sm">Add Action</Button>
      </div>
    </form>
  );
}
