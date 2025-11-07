import { api } from "@/lib/api";
import PrefsForm from "./PrefsForm";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const data = await api.staff.settings();
  const p = data.preferences;
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="rounded border bg-white p-4">
        <h2 className="font-medium mb-3">Notification Preferences</h2>
        <PrefsForm minutes={p.minutes_before} email={p.email_enabled} />
      </section>

      <section className="rounded border bg-white p-4">
        <h2 className="font-medium mb-3">Connected Providers</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Google</div>
            <div>{data.providers.google.connected ? 'Connected' : 'Not connected'}</div>
          </div>
          <div>
            <div className="text-gray-500">Microsoft</div>
            <div>{data.providers.microsoft.connected ? 'Connected' : 'Not connected'}</div>
          </div>
        </div>
      </section>
    </div>
  );
}
