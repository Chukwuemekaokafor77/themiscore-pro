"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";

export default function NewCasePage() {
  const router = useRouter();
  const qp = useSearchParams();
  const [title, setTitle] = useState("Client Intake");
  const [text, setText] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = qp.get("title");
    const x = qp.get("text");
    if (t) setTitle(t);
    if (x) setText(x);
  }, [qp]);

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Create New Case</h1>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setSubmitting(true);
          setError(null);
          try {
            const res = await fetch("/api/intake/auto", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                text,
                title: title || "Client Intake",
                client: { first_name: firstName, last_name: lastName, email, phone, address },
              }),
            });
            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              throw new Error(err.error || "Failed to create case");
            }
            const data = await res.json();
            if (data && data.case_id) {
              router.push(`/cases/${data.case_id}`);
              return;
            }
            throw new Error("Unexpected response");
          } catch (e: any) {
            setError(e?.message || "Failed to create case");
          } finally {
            setSubmitting(false);
          }
        }}
        className="grid gap-4"
      >
        <div className="grid gap-2">
          <label className="text-sm text-gray-600">Case title</label>
          <input className="border rounded px-3 py-2" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <label className="text-sm text-gray-600">Description / Transcript</label>
          <textarea className="border rounded px-3 py-2 min-h-40" value={text} onChange={(e) => setText(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="grid gap-2">
            <label className="text-sm text-gray-600">First name</label>
            <input className="border rounded px-3 py-2" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm text-gray-600">Last name</label>
            <input className="border rounded px-3 py-2" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="grid gap-2">
            <label className="text-sm text-gray-600">Email</label>
            <input className="border rounded px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm text-gray-600">Phone</label>
            <input className="border rounded px-3 py-2" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
        </div>
        <div className="grid gap-2">
          <label className="text-sm text-gray-600">Address</label>
          <input className="border rounded px-3 py-2" value={address} onChange={(e) => setAddress(e.target.value)} />
        </div>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <div className="flex justify-end gap-2">
          <button type="button" className="px-3 py-2 border rounded" onClick={() => router.back()}>
            Cancel
          </button>
          <button type="submit" className="px-3 py-2 bg-primary text-primary-foreground rounded" disabled={submitting}>
            {submitting ? "Creating…" : "Create Case"}
          </button>
        </div>
      </form>
    </div>
  );
}
