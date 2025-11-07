"use client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function EditForm({ id, defaults }: { id: number; defaults: any }) {
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    ["first_name", "last_name", "email", "phone", "address"].forEach((k) => {
      const v = fd.get(k);
      if (v && String(v).trim().length) (body as any)[k] = v;
    });
    const res = await fetch(`/api/clients/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      toast.success("Client updated");
      location.href = `/clients/${id}`;
    } else {
      toast.error("Failed to update");
    }
  };
  return (
    <form onSubmit={onSubmit} className="grid gap-3">
      <div>
        <Label>First Name</Label>
        <Input name="first_name" defaultValue={defaults.first_name ?? ""} />
      </div>
      <div>
        <Label>Last Name</Label>
        <Input name="last_name" defaultValue={defaults.last_name ?? ""} />
      </div>
      <div>
        <Label>Email</Label>
        <Input name="email" type="email" defaultValue={defaults.email ?? ""} />
      </div>
      <div>
        <Label>Phone</Label>
        <Input name="phone" defaultValue={defaults.phone ?? ""} />
      </div>
      <div>
        <Label>Address</Label>
        <Input name="address" defaultValue={defaults.address ?? ""} />
      </div>
      <div className="pt-2">
        <Button type="submit">Save</Button>
      </div>
    </form>
  );
}
