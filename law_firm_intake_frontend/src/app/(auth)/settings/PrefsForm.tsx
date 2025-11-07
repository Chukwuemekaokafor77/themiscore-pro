"use client";
import { toast } from "sonner";

export default function PrefsForm({ minutes, email }: { minutes: number; email: boolean }) {
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const payload = {
      minutes_before: Number(fd.get('minutes_before') || 60),
      email_enabled: fd.get('email_enabled') === 'on',
    };
    const res = await fetch('/api/settings/notifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      toast.success('Preferences saved');
    } else {
      toast.error('Failed to save');
    }
  };
  return (
    <form onSubmit={onSubmit} className="grid gap-3 max-w-md">
      <div>
        <label className="block text-sm text-gray-600 mb-1">Minutes before reminders</label>
        <input name="minutes_before" type="number" min={0} defaultValue={minutes} className="w-full border rounded px-3 py-2" />
      </div>
      <label className="inline-flex items-center gap-2 text-sm">
        <input name="email_enabled" type="checkbox" defaultChecked={email} /> Email reminders enabled
      </label>
      <button type="submit" className="px-4 py-2 bg-primary text-primary-foreground rounded">Save</button>
    </form>
  );
}
