import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Install Agent Jumbo',
  description: 'Download and self-host Agent Jumbo in minutes. One-line install script for macOS and Linux.',
}

const GITHUB_REPO = 'mahoosuc-solutions/agent-jumbo'
const GITHUB_URL = `https://github.com/${GITHUB_REPO}`
const RELEASES_URL = `${GITHUB_URL}/releases/latest`

const ONE_LINE_INSTALL = `curl -fsSL https://raw.githubusercontent.com/${GITHUB_REPO}/main/install.sh | sh`

const MANUAL_STEPS = [
  {
    step: '1',
    title: 'Download the latest release',
    code: `# Download from GitHub Releases
curl -LO ${RELEASES_URL.replace('/latest', '')}/download/latest/agent-jumbo-latest.tar.gz`,
  },
  {
    step: '2',
    title: 'Extract and enter the directory',
    code: `tar -xzf agent-jumbo-latest.tar.gz
cd agent-jumbo-*/`,
  },
  {
    step: '3',
    title: 'Install dependencies with uv',
    code: `# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Agent Jumbo dependencies
uv sync`,
  },
  {
    step: '4',
    title: 'Configure your environment',
    code: `cp .env.example .env
# Edit .env with your API keys and settings`,
  },
  {
    step: '5',
    title: 'Start Agent Jumbo',
    code: `uv run python run_ui.py
# Opens on http://localhost:6274`,
  },
]

const REQUIREMENTS = [
  { label: 'Python', value: '3.11+' },
  { label: 'uv', value: 'Latest' },
  { label: 'OS', value: 'macOS, Linux, Windows (WSL2)' },
  { label: 'RAM', value: '4GB minimum, 8GB recommended' },
]

export default function InstallPage() {
  return (
    <div className="py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-12">
          <p className="text-copper-400 font-mono text-sm tracking-widest uppercase mb-3">Installation</p>
          <h1 className="text-4xl font-bold text-white mb-4">Get Agent Jumbo Running</h1>
          <p className="text-slate-400 text-lg">
            Self-hosted. No cloud required. Runs on your machine or your server.
          </p>
        </div>

        {/* One-line install */}
        <div className="mb-12 p-6 rounded-xl bg-slate-900 border border-copper-500/30">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-white font-semibold">One-line install</h2>
            <span className="text-xs text-slate-500 font-mono">macOS &amp; Linux</span>
          </div>
          <div className="relative">
            <pre className="text-copper-300 font-mono text-sm overflow-x-auto bg-slate-950 rounded-lg p-4 pr-16">
              <code>{ONE_LINE_INSTALL}</code>
            </pre>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Installs to <code className="text-slate-400">~/.local/share/agent-jumbo</code> with a launcher at <code className="text-slate-400">~/.local/bin/agent-jumbo</code>.{' '}
            <Link href={`${GITHUB_URL}/blob/main/install.sh`} className="text-copper-400 hover:text-copper-300 underline underline-offset-2" target="_blank" rel="noopener noreferrer">
              Read the install script
            </Link>
          </p>
        </div>

        {/* System requirements */}
        <div className="mb-12">
          <h2 className="text-xl font-bold text-white mb-4">System Requirements</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {REQUIREMENTS.map((r) => (
              <div key={r.label} className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
                <div className="text-xs text-slate-500 font-mono uppercase tracking-widest mb-1">{r.label}</div>
                <div className="text-sm text-white font-medium">{r.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Manual install steps */}
        <div className="mb-12">
          <h2 className="text-xl font-bold text-white mb-6">Manual Installation</h2>
          <div className="space-y-6">
            {MANUAL_STEPS.map((s) => (
              <div key={s.step} className="flex gap-6">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-copper-500/20 border border-copper-500/40 flex items-center justify-center">
                  <span className="text-copper-400 font-mono text-sm font-bold">{s.step}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-white font-semibold mb-2">{s.title}</h3>
                  <pre className="text-slate-300 font-mono text-sm overflow-x-auto bg-slate-900 rounded-lg p-4 border border-slate-700/50">
                    <code>{s.code}</code>
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Connect to MOS */}
        <div className="mb-12 p-6 rounded-xl bg-mahoosuc-blue-900/30 border border-mahoosuc-blue-700/30">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full border border-mahoosuc-blue-500/40 bg-mahoosuc-blue-500/10 flex items-center justify-center">
              <span className="text-mahoosuc-blue-300 font-bold text-xs">MOS</span>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-1">Connect to Mahoosuc OS</h3>
              <p className="text-slate-400 text-sm mb-3">
                Once running, Agent Jumbo can connect to the Mahoosuc OS platform via the Agent Mesh Bridge. Set <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded text-xs">AGENTMESH_REDIS_URL</code> and <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded text-xs">AIOS_BASE_URL</code> in your <code className="text-slate-300 bg-slate-800 px-1 py-0.5 rounded text-xs">.env</code> to activate the bridge.
              </p>
              <Link
                href="https://mahoosuc.ai/agent-jumbo"
                className="text-sm text-mahoosuc-blue-300 hover:text-mahoosuc-blue-200 underline underline-offset-2"
                target="_blank"
                rel="noopener noreferrer"
              >
                Learn about the Agent Mesh Bridge →
              </Link>
            </div>
          </div>
        </div>

        {/* Footer links */}
        <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t border-slate-800">
          <Link
            href={RELEASES_URL}
            className="px-6 py-2.5 bg-copper-500 text-white rounded-lg font-semibold hover:bg-copper-400 transition text-center text-sm"
            target="_blank"
            rel="noopener noreferrer"
          >
            View Latest Release
          </Link>
          <Link
            href={`${GITHUB_URL}/blob/main/docs/SETUP-GUIDE.md`}
            className="px-6 py-2.5 border border-slate-700 text-slate-200 rounded-lg font-semibold hover:bg-slate-800 transition text-center text-sm"
            target="_blank"
            rel="noopener noreferrer"
          >
            Full Setup Guide
          </Link>
          <Link
            href="/documentation"
            className="px-6 py-2.5 border border-slate-700 text-slate-200 rounded-lg font-semibold hover:bg-slate-800 transition text-center text-sm"
          >
            Documentation
          </Link>
        </div>
      </div>
    </div>
  )
}
