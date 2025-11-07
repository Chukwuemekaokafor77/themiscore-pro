"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const dynamic = "force-dynamic";

export default function NewClientPage() {
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body = {
      first_name: String(fd.get('first_name') || ''),
      last_name: String(fd.get('last_name') || ''),
      email: (fd.get('email') || undefined) as string | undefined,
      phone: (fd.get('phone') || undefined) as string | undefined,
      address: (fd.get('address') || undefined) as string | undefined,
    };
    const res = await fetch('/api/clients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      toast.success('Client created');
      const data = await res.json();
      location.href = `/clients/${data.id}`;
    } else {
      toast.error('Failed to create client');
    }
  };
  return (
    <div className="max-w-2xl mx-auto p-6">
      <Card>
        <CardHeader><CardTitle>New Client</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="grid gap-3">
            <div>
              <Label>First Name</Label>
              <Input name="first_name" required />
            </div>
            <div>
              <Label>Last Name</Label>
              <Input name="last_name" required />
            </div>
            <div>
              <Label>Email</Label>
              <Input name="email" type="email" />
            </div>
            <div>
              <Label>Phone</Label>
              <Input name="phone" />
            </div>
            <div>
              <Label>Address</Label>
              <Input name="address" />
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
