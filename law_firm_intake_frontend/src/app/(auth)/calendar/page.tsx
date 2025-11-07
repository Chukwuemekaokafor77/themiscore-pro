import { api } from "@/lib/api";
import AddEventForm from "./AddEventForm";

export const dynamic = "force-dynamic";

// AddEventForm is a Client Component in ./AddEventForm

export default async function CalendarPage() {
  const events = await api.staff.calendar();
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Calendar</h1>

      <section className="rounded border bg-white p-4">
        <h2 className="font-medium mb-3">Add Event</h2>
        <AddEventForm />
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Upcoming Events</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left"><tr>
              <th className="px-4 py-2">Title</th>
              <th className="px-4 py-2">Start</th>
              <th className="px-4 py-2">End</th>
              <th className="px-4 py-2">All Day</th>
              <th className="px-4 py-2">Case</th>
              <th className="px-4 py-2">Client</th>
            </tr></thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} className="border-t">
                  <td className="px-4 py-2">{ev.title}</td>
                  <td className="px-4 py-2">{ev.start_at ? new Date(ev.start_at).toLocaleString() : '—'}</td>
                  <td className="px-4 py-2">{ev.end_at ? new Date(ev.end_at).toLocaleString() : '—'}</td>
                  <td className="px-4 py-2">{ev.all_day ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-2">{ev.case?.title ?? '—'}</td>
                  <td className="px-4 py-2">{ev.client?.name ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div>
        <a href="/calendar/ics" className="text-sm underline">Download ICS</a>
      </div>
    </div>
  );
}
