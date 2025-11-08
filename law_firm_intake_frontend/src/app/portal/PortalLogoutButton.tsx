"use client";

export default function PortalLogoutButton() {
  async function onClick() {
    try {
      await fetch("/api/portal/logout", { method: "POST" });
    } catch (_) {
      // ignore
    } finally {
      window.location.href = "/login";
    }
  }
  return (
    <button onClick={onClick} className="text-sm text-red-600 hover:underline">
      Sign out
    </button>
  );
}
