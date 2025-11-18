export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
      <main className="w-full max-w-3xl bg-white rounded-lg shadow-sm p-8 space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold">Law Firm Intake Console</h1>
          <p className="text-sm text-zinc-600">
            Quick links to common intake workflows.
          </p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 text-sm">
          <a
            href="/intake"
            className="rounded border px-4 py-3 hover:bg-zinc-50 transition-colors flex flex-col justify-between"
          >
            <div>
              <div className="font-medium">AI Intake (Text)</div>
              <div className="text-xs text-zinc-600">
                Paste or type client narrative and run full automation.
              </div>
            </div>
          </a>

          <a
            href="/transcribe"
            className="rounded border px-4 py-3 hover:bg-zinc-50 transition-colors flex flex-col justify-between"
          >
            <div>
              <div className="font-medium">Voice Intake (Staff)</div>
              <div className="text-xs text-zinc-600">
                Record or upload audio, transcribe, analyze, and automate.
              </div>
            </div>
          </a>
        </section>
      </main>
    </div>
  );
}
