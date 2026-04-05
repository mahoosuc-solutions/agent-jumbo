import Link from 'next/link'
import { getAllDocs } from '@/lib/docs'

const launchAndComplianceDocs = [
  {
    slug: 'PRODUCTION_GA_DEFINITION_OF_DONE',
    title: 'Production GA Definition of Done',
    description: 'Launch gates, go-live criteria, and the current source of truth for self-serve readiness.',
  },
  {
    slug: 'SELF_SERVE_GA_ONBOARDING',
    title: 'Self-Serve GA Onboarding',
    description: 'The customer-facing setup path for production launch.',
  },
  {
    slug: 'GA_LAUNCH_RUNBOOK',
    title: 'GA Launch Runbook',
    description: 'Launch-day execution, rollback triggers, and observation guidance.',
  },
  {
    slug: 'PRIVACY_POLICY',
    title: 'Privacy Policy',
    description: 'How Agent Jumbo handles customer data, integrations, and telemetry.',
  },
  {
    slug: 'TERMS_OF_USE',
    title: 'Terms Of Use',
    description: 'Core service terms and acceptable-use boundaries.',
  },
  {
    slug: 'DATA_RETENTION_POLICY',
    title: 'Data Retention Policy',
    description: 'Default retention guidance for chats, projects, backups, and logs.',
  },
  {
    slug: 'DATA_DELETION_POLICY',
    title: 'Data Deletion Policy',
    description: 'Expected deletion behavior for customer content and environments.',
  },
  {
    slug: 'CUSTOMER_SUPPORT',
    title: 'Customer Support',
    description: 'Canonical support, incident, billing, and remediation paths for self-serve customers.',
  },
]

export default function DocsIndex() {
  const docs = getAllDocs()
    .filter(doc => doc.metadata.title)
    .filter(doc => !launchAndComplianceDocs.some(featured => featured.slug === doc.slug))
    .sort((a, b) => {
      const aDate = new Date(a.metadata.date || 0).getTime()
      const bDate = new Date(b.metadata.date || 0).getTime()
      return bDate - aDate
    })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-12">
        <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
          Documentation
        </h1>
        <p className="text-xl text-slate-600 dark:text-slate-300">
          Learn how to use Agent Jumbo for intelligent multi-platform deployment orchestration.
        </p>
      </div>

      <div className="mb-12">
        <div className="flex items-end justify-between gap-4 mb-6 flex-wrap">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
              Launch & Compliance
            </h2>
            <p className="text-slate-600 dark:text-slate-300 mt-1">
              Customer-facing launch, onboarding, privacy, and policy documents for the current self-serve platform.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {launchAndComplianceDocs.map(doc => (
            <Link
              key={doc.slug}
              href={`/documentation/${doc.slug}`}
              className="p-6 border border-blue-200 bg-blue-50/40 dark:bg-blue-950/10 dark:border-blue-900/50 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition"
            >
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                {doc.title}
              </h3>
              <p className="text-slate-700 dark:text-slate-300 line-clamp-3">
                {doc.description}
              </p>
            </Link>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
          General Documentation
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          Product, setup, architecture, and feature guides across the rest of the platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {docs.map(doc => (
          <Link
            key={doc.slug}
            href={`/documentation/${doc.slug}`}
            className="p-6 border border-slate-200 dark:border-slate-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition"
          >
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
              {doc.metadata.title || doc.slug}
            </h3>
            <p className="text-slate-600 dark:text-slate-400 line-clamp-3">
              {doc.metadata.description || 'Documentation page'}
            </p>
          </Link>
        ))}
      </div>
    </div>
  )
}
