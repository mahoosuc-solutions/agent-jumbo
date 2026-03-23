interface PortfolioProject {
  name: string
  vertical: string
  description: string
  highlights: string[]
}

export default function PortfolioCard({ project }: { project: PortfolioProject }) {
  return (
    <div className="p-6 rounded-xl border border-slate-800 hover:border-mahoosuc-blue-400/30 transition">
      <span className="text-xs font-mono px-2 py-0.5 rounded bg-mahoosuc-blue-500/10 text-mahoosuc-blue-300 uppercase tracking-wider">
        {project.vertical}
      </span>
      <h3 className="text-lg font-bold text-white mb-2 mt-3">{project.name}</h3>
      <p className="text-sm text-slate-400 mb-4">{project.description}</p>
      <div className="flex flex-wrap gap-2">
        {project.highlights.map((h) => (
          <span key={h} className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">{h}</span>
        ))}
      </div>
    </div>
  )
}

export type { PortfolioProject }
