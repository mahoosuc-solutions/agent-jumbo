const steps = [
  {
    number: '01',
    name: 'ArchitectFlow',
    title: 'Design',
    description: 'Generate requirements, system architecture, and specs from natural language. AI agents decompose your vision into buildable components.',
  },
  {
    number: '02',
    name: 'DevFlow',
    title: 'Build',
    description: 'AI agents recursively execute your specs using 414+ commands, skills, and SOPs. Code is generated, tested, and validated through structured workflows.',
  },
  {
    number: '03',
    name: 'AG Mesh',
    title: 'Orchestrate',
    description: 'Event-driven coordination connects everything. Tasks flow through risk-based approval gates. Agents collaborate across your entire infrastructure.',
  },
]

export default function HowItWorks() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-white text-center mb-4">How It Works</h2>
        <p className="text-slate-400 text-center mb-16 max-w-2xl mx-auto">From idea to orchestrated reality in three stages.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div key={step.number} className="relative">
              {i < steps.length - 1 && (
                <div className="hidden md:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-copper-500/40 to-transparent -translate-x-4" />
              )}
              <div className="text-copper-500 font-mono text-sm mb-2">{step.number}</div>
              <div className="text-copper-400 font-mono text-xs uppercase tracking-widest mb-1">{step.name}</div>
              <h3 className="text-xl font-bold text-white mb-3">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
