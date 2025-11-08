"use client";

import { useState, useTransition } from "react";

export default function GenerateInvoicesButton() {
  const [pending, startTransition] = useTransition();
  const [msg, setMsg] = useState<string | null>(null);

  function onClick() {
    setMsg(null);
    startTransition(async () => {
      try {
        const res = await fetch(`/api/staff/billing/invoices/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (res.status === 501) {
          setMsg("Generate invoices is not implemented yet.");
          return;
        }
        if (!res.ok) {
          setMsg(`Failed (${res.status})`);
          return;
        }
        setMsg("Invoices generated.");
      } catch (e) {
        setMsg("Request failed.");
      }
    });
  }

  return (
    <div className="flex items-center gap-2">
      <button className="border rounded px-3 py-1 bg-black text-white text-sm" disabled={pending} onClick={onClick}>
        {pending ? "Generating..." : "Generate Invoices"}
      </button>
      {msg && <span className="text-xs text-gray-600">{msg}</span>}
    </div>
  );
}
