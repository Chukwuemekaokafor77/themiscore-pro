"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type Props = {
  caseId: number;
  initialStatus: "open" | "in_progress" | "closed";
};

type AuditRow = { id:number; case_id:number; from_status:string|null; to_status:string; changed_by_id:number|null; created_at:string|null };

export default function StatusManager({ caseId, initialStatus }: Props) {
  const [status, setStatus] = useState<Props["initialStatus"]>(initialStatus);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [loading, startTransition] = useTransition();
  const router = useRouter();

  async function loadAudit() {
    try {
      const res = await fetch(`/api/staff/cases/${caseId}/status_audit`, { cache: "no-store" });
      if (!res.ok) return;
      const rows = await res.json();
      setAudit(rows);
    } catch {}
  }

  useEffect(() => {
    loadAudit();
  }, [caseId]);

  async function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newStatus = e.target.value as Props["initialStatus"];
    if (newStatus === status) return;
    startTransition(async () => {
      try {
        const res = await fetch(`/api/staff/cases/${caseId}/status`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        });
        if (res.ok) {
          setStatus(newStatus);
          await loadAudit();
          router.refresh();
        }
      } catch {}
    });
  }

  return (
    <div className="rounded border bg-white p-4">
      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-600">Status</label>
        <select className="border rounded px-2 py-1" value={status} onChange={onChange} disabled={loading}>
          <option value="open">open</option>
          <option value="in_progress">in_progress</option>
          <option value="closed">closed</option>
        </select>
      </div>
      <div className="mt-4">
        <div className="text-sm font-medium mb-2">Status History</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr><th className="px-2 py-1">Changed</th><th className="px-2 py-1">From</th><th className="px-2 py-1">To</th></tr></thead>
            <tbody>
              {audit.map(r => (
                <tr key={r.id} className="border-t">
                  <td className="px-2 py-1">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                  <td className="px-2 py-1">{r.from_status ?? "—"}</td>
                  <td className="px-2 py-1">{r.to_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
