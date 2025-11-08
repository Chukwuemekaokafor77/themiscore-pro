"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type Intent = { id:number; key:string; name:string; department:string|null };

export default function ApplyIntent({ caseId }: { caseId: number }) {
  const [intents, setIntents] = useState<Intent[]>([]);
  const [selected, setSelected] = useState<number | "">("");
  const [pending, startTransition] = useTransition();
  const [msg, setMsg] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/staff/intents', { cache: 'no-store' });
        if (!res.ok) return;
        const data = await res.json();
        setIntents(data);
      } catch {}
    })();
  }, []);

  function onApply() {
    if (!selected) return;
    setMsg(null);
    startTransition(async () => {
      try {
        const res = await fetch(`/api/staff/cases/${caseId}/apply_intent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intent_id: selected }),
        });
        if (!res.ok) {
          const t = await res.text();
          setMsg(`Failed (${res.status}) ${t}`);
          return;
        }
        setMsg('Templates applied.');
        router.refresh();
      } catch {
        setMsg('Request failed');
      }
    });
  }

  return (
    <div className="rounded border bg-white p-4">
      <div className="text-sm font-medium mb-3">Apply Case Template</div>
      <div className="flex items-center gap-2">
        <select className="border rounded px-2 py-1" value={selected} onChange={(e) => setSelected(e.target.value ? Number(e.target.value) : "")}>
          <option value="">Select template...</option>
          {intents.map(i => (
            <option key={i.id} value={i.id}>{i.name}</option>
          ))}
        </select>
        <button className="border rounded px-3 py-1 bg-black text-white text-sm" disabled={!selected || pending} onClick={onApply}>
          {pending ? 'Applying...' : 'Apply Template'}
        </button>
        {msg && <span className="text-xs text-gray-600">{msg}</span>}
      </div>
    </div>
  );
}
