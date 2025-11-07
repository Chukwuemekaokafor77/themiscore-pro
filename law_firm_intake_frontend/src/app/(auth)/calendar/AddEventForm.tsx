"use client";
import { toast } from "sonner";
import type { FormEvent } from "react";

export default function AddEventForm() {
  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const payload = {
      title: fd.get('title'),
      description: fd.get('description') || undefined,
      location: fd.get('location') || undefined,
      all_day: fd.get('all_day') === 'on',
      reminder_minutes_before: Number(fd.get('reminder') || 0),
      case_id: fd.get('case_id') ? Number(fd.get('case_id')) : undefined,
      client_id: fd.get('client_id') ? Number(fd.get('client_id')) : undefined,
      start_at: fd.get('start_at') || undefined,
      end_at: fd.get('end_at') || undefined,
    };
    const res = await fetch('/api/calendar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      toast.success('Event created');
      (e.currentTarget as HTMLFormElement).reset();
      setTimeout(() => window.location.reload(), 400);
    } else {
      const msg = await res.text().catch(() => 'Failed to create event');
      toast.error(msg || 'Failed to create event');
    }
  };
  return (
    <form onSubmit={onSubmit} className="grid gap-3 max-w-xl">
      <div>
        <label className="block text-sm text-gray-600 mb-1">Title</label>
        <input name="title" required className="w-full border rounded px-3 py-2" />
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">Description</label>
        <textarea name="description" className="w-full border rounded px-3 py-2" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Start (ISO)</label>
          <input name="start_at" placeholder="2025-11-06T10:00:00" className="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">End (ISO)</label>
          <input name="end_at" placeholder="2025-11-06T11:00:00" className="w-full border rounded px-3 py-2" />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Case ID</label>
          <input name="case_id" type="number" className="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Client ID</label>
          <input name="client_id" type="number" className="w-full border rounded px-3 py-2" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" name="all_day" /> All day</label>
        <div className="flex items-center gap-2 text-sm"><span>Reminder</span><input name="reminder" type="number" min={0} className="w-24 border rounded px-2 py-1" /><span>min</span></div>
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">Location</label>
        <input name="location" className="w-full border rounded px-3 py-2" />
      </div>
      <button type="submit" className="px-4 py-2 bg-black text-white rounded">Add Event</button>
    </form>
  );
}
