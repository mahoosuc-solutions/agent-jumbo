import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'How Agent Jumbo Works',
  description:
    'Everything you need to know about Agent Jumbo — what it is, what it does, how it connects to Mahoosuc OS, and how your data is protected. Written for humans, not engineers.',
}

const SECTIONS = [
  {
    id: 'what',
    label: 'What is it?',
    title: 'Agent Jumbo is a personal AI operating system that runs on your own computer.',
  },
  {
    id: 'what-it-does',
    label: 'What does it do?',
    title: 'It manages the parts of your life that eat your time but rarely need your judgment.',
  },
  {
    id: 'how',
    label: 'How does it work?',
    title: 'You talk to it. It acts. You approve what matters.',
  },
  {
    id: 'mos',
    label: 'Mahoosuc OS connection',
    title: 'Agent Jumbo is one part of a larger platform.',
  },
  {
    id: 'security',
    label: 'Security & your data',
    title: 'Your data never leaves your machine unless you explicitly configure it to.',
  },
  {
    id: 'when',
    label: 'When does it act?',
    title: 'Only when you initiate, schedule, or approve.',
  },
]

export default function HowItWorksPage() {
  return (
    <div className="py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="mb-14">
          <p className="text-copper-400 font-mono text-sm tracking-widest uppercase mb-3">Understanding Agent Jumbo</p>
          <h1 className="text-4xl font-bold text-white mb-5 leading-tight">
            Everything you need to know.<br />Plain language. No assumptions.
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            This page answers every question a careful, security-minded person should ask before installing software that manages their life. If something is unclear after reading, that is our failure — not yours.
          </p>
        </div>

        {/* Section nav */}
        <nav className="mb-14 p-5 rounded-xl bg-slate-800/50 border border-slate-700/50">
          <p className="text-xs text-slate-500 font-mono uppercase tracking-widest mb-3">On this page</p>
          <ol className="space-y-1.5">
            {SECTIONS.map((s, i) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="flex items-center gap-3 text-sm text-slate-300 hover:text-copper-400 transition group">
                  <span className="text-xs font-mono text-slate-600 group-hover:text-copper-500 w-4">{i + 1}.</span>
                  <span>{s.label}</span>
                </a>
              </li>
            ))}
          </ol>
        </nav>

        {/* ── SECTION 1: What is it ── */}
        <section id="what" className="mb-16 scroll-mt-8">
          <div className="mb-6">
            <p className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-2">01 — What is it?</p>
            <h2 className="text-2xl font-bold text-white leading-snug">
              Agent Jumbo is a personal AI operating system that runs on your own computer.
            </h2>
          </div>

          <div className="space-y-5 text-slate-300 leading-relaxed">
            <p>
              Think of it like a very capable personal assistant — one that can manage your calendar, track your properties, monitor your finances, remind you about the people you care about, and handle the repetitive work you do every week. The difference is that this assistant runs as software on your machine, not in someone else's cloud.
            </p>
            <p>
              Agent Jumbo is <strong className="text-white">not a chat app</strong>. It is not a productivity app. It is not a subscription service. It is an operating system layer — a piece of software that runs continuously in the background, monitoring your configured domains, triggering actions, and routing decisions to you when human judgment is required.
            </p>
            <p>
              It is built on the same architecture as{' '}
              <Link href="https://mahoosuc.ai" className="text-copper-400 hover:text-copper-300 underline underline-offset-2" target="_blank" rel="noopener noreferrer">
                Mahoosuc OS
              </Link>
              {' '}— an event-driven AI platform built and proven in production across healthcare, hospitality, home services, and business operations.
            </p>

            <div className="p-5 rounded-xl bg-slate-800/60 border border-slate-700/40">
              <p className="text-sm font-semibold text-white mb-3">In plain terms:</p>
              <ul className="space-y-2 text-sm">
                {[
                  'It runs on your computer, not in a data center you cannot inspect.',
                  'It does not phone home. It does not sell data. It does not have a free tier that monetizes you.',
                  'It connects to AI providers (like Anthropic or OpenAI) only to process requests you initiate.',
                  'You configure what it manages. It manages only that.',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <span className="text-copper-400 mt-0.5 flex-shrink-0">→</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── SECTION 2: What does it do ── */}
        <section id="what-it-does" className="mb-16 scroll-mt-8">
          <div className="mb-6">
            <p className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-2">02 — What does it do?</p>
            <h2 className="text-2xl font-bold text-white leading-snug">
              It manages the parts of your life that eat your time but rarely need your judgment.
            </h2>
          </div>

          <div className="space-y-5 text-slate-300 leading-relaxed">
            <p>
              Most of the work in managing a property, tracking finances, staying connected with family, or keeping a calendar optimized does not require your unique human judgment. It requires consistency, attention, and the willingness to act on information. Agent Jumbo provides the first two and routes the third to you — only when it actually matters.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-6">
              {[
                { domain: 'Real Estate & Property', detail: 'Portfolio tracking, maintenance ticket management, tenant communication drafts, occupancy monitoring. You review; it executes.' },
                { domain: 'Finance & Investments', detail: 'Budget monitoring, investment drift alerts, cash flow summaries, tax preparation reminders. You decide; it surfaces the information in time to act.' },
                { domain: 'Wellness & Health', detail: 'Metrics tracking, routine reminders, nutrition context, sleep and energy correlation. Your data, organized for your use.' },
                { domain: 'Relationships', detail: 'Touchpoint tracking, relationship reminders, network context. The people who matter get the attention they deserve.' },
                { domain: 'Calendar & Time', detail: 'Priority-aware scheduling, deep-work protection, meeting prep context. Your time, defended by something that understands your goals.' },
                { domain: 'Projects & Goals', detail: 'Goal tracking, habit formation, project orchestration. The things that matter most get the same rigor as business operations.' },
              ].map((d) => (
                <div key={d.domain} className="p-4 rounded-lg bg-slate-800/40 border border-slate-700/40">
                  <p className="text-sm font-semibold text-white mb-1.5">{d.domain}</p>
                  <p className="text-xs text-slate-400 leading-relaxed">{d.detail}</p>
                </div>
              ))}
            </div>

            <p>
              Every one of these domains is optional. You configure what you want Agent Jumbo to manage. If you only care about property management and finances, you configure those two and ignore the rest.
            </p>
          </div>
        </section>

        {/* ── SECTION 3: How does it work ── */}
        <section id="how" className="mb-16 scroll-mt-8">
          <div className="mb-6">
            <p className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-2">03 — How does it work?</p>
            <h2 className="text-2xl font-bold text-white leading-snug">
              You talk to it. It acts. You approve what matters.
            </h2>
          </div>

          <div className="space-y-5 text-slate-300 leading-relaxed">
            <p>
              The primary interface is a chat window — accessible from a browser on your local machine, or via Telegram on your phone. You talk to Agent Jumbo the way you would talk to a capable assistant. "The HVAC at the rental property is making a noise." "I haven't called my mother in three weeks." "Schedule a deep work block for Thursday morning." It understands context. It remembers what you told it last month.
            </p>

            <div className="space-y-4 my-6">
              {[
                {
                  step: '01',
                  title: 'You communicate',
                  body: 'Text, voice notes, or photos via the web interface or Telegram. Agent Jumbo understands natural language — you do not need to learn commands or a specific format.',
                },
                {
                  step: '02',
                  title: 'Specialized agents handle the work',
                  body: 'Behind the interface, specialized AI agents route tasks by domain — a property agent, a finance agent, a scheduling agent. Each one is purpose-built for its domain and operates with the minimum permissions needed to do its job.',
                },
                {
                  step: '03',
                  title: 'High-stakes decisions come to you',
                  body: 'Anything that involves money, binding commitments, communications on your behalf, or actions that cannot be undone — these route to you with full context, reasoning, and a recommended action. You approve with a single tap. The AI handles volume. You handle judgment.',
                },
                {
                  step: '04',
                  title: 'Everything is logged',
                  body: 'Every action Agent Jumbo takes, every decision it makes without you, every approval it requests — all of it is logged locally. You can audit the complete history of what happened and why at any time.',
                },
              ].map((s) => (
                <div key={s.step} className="flex gap-5 p-5 rounded-xl bg-slate-800/40 border border-slate-700/40">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-copper-500/15 border border-copper-500/30 flex items-center justify-center">
                    <span className="text-copper-400 font-mono text-xs font-bold">{s.step}</span>
                  </div>
                  <div>
                    <p className="text-white font-semibold mb-1.5">{s.title}</p>
                    <p className="text-sm text-slate-400 leading-relaxed">{s.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── SECTION 4: Mahoosuc OS ── */}
        <section id="mos" className="mb-16 scroll-mt-8">
          <div className="mb-6">
            <p className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-2">04 — The Mahoosuc OS connection</p>
            <h2 className="text-2xl font-bold text-white leading-snug">
              Agent Jumbo is one part of a larger platform.
            </h2>
          </div>

          <div className="space-y-5 text-slate-300 leading-relaxed">
            <p>
              <Link href="https://mahoosuc.ai" className="text-copper-400 hover:text-copper-300 underline underline-offset-2" target="_blank" rel="noopener noreferrer">Mahoosuc OS</Link>{' '}
              is the business AI operating system — 20 products, 121 specialized agents, built and proven in production. Agent Jumbo is its personal counterpart: the same governance model, the same approval architecture, the same underlying infrastructure — applied to your life instead of your business.
            </p>
            <p>
              The two systems can connect through what is called the <strong className="text-white">Agent Mesh Bridge</strong>. This is an optional connection that lets Agent Jumbo and Mahoosuc OS share context and route tasks across the boundary between your personal and business life.
            </p>

            <div className="p-5 rounded-xl bg-mahoosuc-blue-900/30 border border-mahoosuc-blue-700/30 space-y-3">
              <p className="text-sm font-semibold text-white">How the bridge works — in plain terms:</p>
              <ul className="space-y-2.5 text-sm text-slate-300">
                {[
                  { q: 'Is the bridge required?', a: 'No. Agent Jumbo works completely standalone. The bridge is optional and only activates if you configure it.' },
                  { q: 'What crosses the bridge?', a: 'Only events you configure. Examples: a maintenance issue at your rental property routes to the Mahoosuc OS property management system. A personal goal triggers a work calendar block. You define the boundaries.' },
                  { q: 'Is the bridge encrypted?', a: 'Yes. All communication between Agent Jumbo and Mahoosuc OS travels over an encrypted Redis Streams channel. Nothing is sent in plain text.' },
                  { q: 'Can Mahoosuc OS read my personal data?', a: 'Only what you explicitly route to it. The bridge is event-based — it passes structured events, not raw data dumps. You control what crosses.' },
                ].map((item) => (
                  <li key={item.q} className="border-t border-slate-700/50 pt-2.5 first:border-0 first:pt-0">
                    <p className="font-medium text-slate-200 mb-0.5">{item.q}</p>
                    <p className="text-slate-400">{item.a}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── SECTION 5: Security ── */}
        <section id="security" className="mb-16 scroll-mt-8">
          <div className="mb-6">
            <p className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-2">05 — Security &amp; your data</p>
            <h2 className="text-2xl font-bold text-white leading-snug">
              Your data never leaves your machine unless you explicitly configure it to.
            </h2>
          </div>

          <div className="space-y-5 text-slate-300 leading-relaxed">
            <p>
              Security is not a feature in Agent Jumbo — it is the architecture. Every design decision starts from the assumption that your data belongs to you and that you should be able to inspect, audit, and revoke access to anything the system touches.
            </p>

            <div className="space-y-3 my-6">
              {[
                {
                  title: 'Self-hosted by default',
                  body: 'Agent Jumbo runs on your machine. Your data lives in a local SQLite database on your hard drive. There is no Agent Jumbo cloud account. There is no central server that receives your information. The software runs entirely within your own infrastructure.',
                  icon: '🔒',
                },
                {
                  title: 'AI providers receive only what you send',
                  body: 'When Agent Jumbo uses an AI model (like Claude or GPT-4) to process a request, only the specific content of that request is sent. Your historical data, your full database, your other domains — none of that is included unless it is directly relevant to the task at hand and you have configured it to be.',
                  icon: '🧠',
                },
                {
                  title: 'Secrets stored locally, never in code',
                  body: 'Your API keys (for AI providers, calendar access, financial data) are stored in a local .env file on your machine. They are never stored in the Agent Jumbo codebase, never sent to a third party, and never logged. When connecting to Mahoosuc OS, secrets are managed through HashiCorp Vault — an industry-standard secrets manager that stores credentials separately from application code.',
                  icon: '🔑',
                },
                {
                  title: 'Approval gates on consequential actions',
                  body: 'Any action involving money, external communications, or irreversible changes requires your explicit approval before Agent Jumbo proceeds. The system is designed to be stopped by a human at every meaningful decision point. You are not handing over control — you are delegating volume work while retaining judgment.',
                  icon: '✅',
                },
                {
                  title: 'Complete audit log',
                  body: 'Every action Agent Jumbo takes is written to a tamper-evident local audit log. You can inspect the complete history of what the system did, when, and why. If something unexpected happened, you can trace it back to the exact request that caused it.',
                  icon: '📋',
                },
                {
                  title: 'Open source — inspect the code yourself',
                  body: 'Agent Jumbo is open source. Every line of code that runs on your machine is publicly available on GitHub. You do not have to trust our claims about security — you can read the code, or ask someone you trust to read it for you.',
                  icon: '👁',
                },
                {
                  title: 'No telemetry, no analytics, no tracking',
                  body: 'Agent Jumbo does not collect usage data, crash reports, feature analytics, or any other telemetry. There is no tracking pixel, no session recording, no behavioral analytics. The software runs for you, not for us.',
                  icon: '🚫',
                },
              ].map((item) => (
                <div key={item.title} className="flex gap-4 p-5 rounded-xl bg-slate-800/40 border border-slate-700/40">
                  <div className="flex-shrink-0 text-xl mt-0.5">{item.icon}</div>
                  <div>
                    <p className="text-white font-semibold mb-1.5">{item.title}</p>
                    <p className="text-sm text-slate-400 leading-relaxed">{item.body}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* What connects to the internet */}
            <div className="p-5 rounded-xl border border-amber-500/20 bg-amber-500/5">
              <p className="text-sm font-semibold text-amber-300 mb-3">What connects to the internet — complete list</p>
              <p className="text-sm text-slate-400 mb-4">
                Being transparent about every outbound connection Agent Jumbo can make. None of these happen without your configuration and explicit consent.
              </p>
              <div className="space-y-3">
                {[
                  { who: 'AI providers (Claude, OpenAI, etc.)', when: 'When you send a message or Agent Jumbo processes a task', what: 'The text of your request and any relevant context you have configured to include', required: 'Required for AI functionality — you choose which provider' },
                  { who: 'Your calendar service (Google, Outlook)', when: 'When you configure calendar integration', what: 'OAuth tokens stored locally; calendar read/write within the permissions you granted', required: 'Optional — only if you configure it' },
                  { who: 'Mahoosuc OS (Agent Mesh Bridge)', when: 'When you configure the bridge connection', what: 'Structured events you define — not raw data', required: 'Optional — off by default' },
                  { who: 'GitHub (for updates)', when: 'When you check for new versions', what: 'A version check request — no personal data', required: 'Optional — manual check only' },
                ].map((conn) => (
                  <div key={conn.who} className="border-t border-slate-700/50 pt-3 first:border-0 first:pt-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p className="text-sm font-medium text-white">{conn.who}</p>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-400 flex-shrink-0">{conn.required}</span>
                    </div>
                    <p className="text-xs text-slate-500"><span className="text-slate-400">When:</span> {conn.when}</p>
                    <p className="text-xs text-slate-500"><span className="text-slate-400">What is sent:</span> {conn.what}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── SECTION 6: When does it act ── */}
        <section id="when" className="mb-16 scroll-mt-8">
          <div className="mb-6">
            <p className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-2">06 — When does it act?</p>
            <h2 className="text-2xl font-bold text-white leading-snug">
              Only when you initiate, schedule, or approve.
            </h2>
          </div>

          <div className="space-y-5 text-slate-300 leading-relaxed">
            <p>
              Agent Jumbo does not take autonomous action. Every action it takes is the result of something you set in motion — either directly (you sent a message), on a schedule (you configured a daily briefing), or through an approval you granted (you tapped "approve" on a suggested action).
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-6">
              {[
                { trigger: 'You initiate', example: 'You send a message, ask a question, or give an instruction. Agent Jumbo responds and acts on that specific request.' },
                { trigger: 'Scheduled task', example: 'You configured a 6:30 AM morning brief. Every day at 6:30, it runs that brief — nothing more, nothing less.' },
                { trigger: 'You approve', example: 'Agent Jumbo identified something that needs your judgment. It asked. You approved. It acted on that approval only.' },
              ].map((t) => (
                <div key={t.trigger} className="p-4 rounded-lg bg-slate-800/40 border border-slate-700/40 text-center">
                  <p className="text-copper-400 font-semibold text-sm mb-2">{t.trigger}</p>
                  <p className="text-xs text-slate-400 leading-relaxed">{t.example}</p>
                </div>
              ))}
            </div>

            <p>
              If you stop Agent Jumbo — close the application, shut down the server — it stops completely. There is no background cloud process continuing to act on your behalf. There is no "always on" remote component. The system is exactly as active as you choose to make it.
            </p>

            <div className="p-5 rounded-xl bg-slate-800/60 border border-slate-700/40">
              <p className="text-sm font-semibold text-white mb-3">Things Agent Jumbo will never do without your explicit approval:</p>
              <ul className="space-y-2 text-sm text-slate-400">
                {[
                  'Transfer or move money',
                  'Send communications on your behalf (email, text, message)',
                  'Commit to appointments or obligations',
                  'Share your personal information with a third party',
                  'Take any action described as irreversible or high-stakes',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2.5">
                    <span className="text-slate-600">✗</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Footer CTA */}
        <div className="pt-10 border-t border-slate-800 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <p className="text-white font-semibold">Ready to get started?</p>
            <p className="text-slate-400 text-sm">Download takes 2 minutes. No account required.</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <Link href="/install" className="px-6 py-2.5 bg-copper-500 text-white rounded-lg font-semibold hover:bg-copper-400 transition text-sm">
              Download &amp; Install
            </Link>
            <Link href="https://mahoosuc.ai/agent-jumbo" className="px-6 py-2.5 border border-slate-700 text-slate-200 rounded-lg font-semibold hover:bg-slate-800 transition text-sm" target="_blank" rel="noopener noreferrer">
              See the Vision →
            </Link>
          </div>
        </div>

      </div>
    </div>
  )
}
