"use client";
import type { FormEvent } from "react";

export default function AddNoteForm({ caseId }: { caseId: number }) {
  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const note = String(fd.get('note') || '').trim();
    if (!note) return;
    const res = await fetch(`/api/cases/${caseId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    });
    if (res.ok) {
      (e.currentTarget as HTMLFormElement).reset();
      window.location.reload();
    } else {
      alert('Failed to add note');
    }
  };
  return (
    <form onSubmit={onSubmit} className="grid gap-3 max-w-xl">
      <div>
        <label className="block text-sm text-gray-600 mb-1">Add Note</label>
        <textarea name="note" required className="w-full border rounded px-3 py-2" placeholder="Enter note..." />
      </div>
      <button type="submit" className="px-4 py-2 bg-black text-white rounded">Save Note</button>
    </form>
  );
}
