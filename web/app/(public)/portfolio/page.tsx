import type { Metadata } from 'next'
import PortfolioCard from '@/components/product/PortfolioCard'
import type { PortfolioProject } from '@/components/product/PortfolioCard'

export const metadata: Metadata = {
  title: 'Portfolio',
  description: 'Real solutions built on the Mahoosuc OS across healthcare, hospitality, home services, and operations.',
}

const projects: PortfolioProject[] = [
  { name: 'HealthData-in-Motion (HDIM)', vertical: 'Healthcare', description: 'Enterprise HIE platform with FHIR R4, HEDIS measures, and real-time care gap detection. Includes validation demo and provider accelerator toolkit.', highlights: ['FHIR R4', 'HEDIS', 'Care Gaps', 'Clinical Analytics', 'Provider Portal'] },
  { name: 'West Bethel Motel Booking System', vertical: 'Hospitality', description: 'Enterprise-grade motel booking system with FAANG-level production deployment. 792+ tests, 95/100 quality score.', highlights: ['792+ Tests', '95/100 Quality', 'Production-Ready', 'Booking Engine'] },
  { name: 'RemoteMotel / StayHive.ai', vertical: 'Hospitality', description: 'AI-powered hotel operator agent with voice calls, booking management, and knowledge base.', highlights: ['Voice AI', 'Booking Mgmt', 'Knowledge Base'] },
  { name: 'BolducBuilders', vertical: 'Home Services', description: 'Custom home builders toolkit to help customers visualize their new home.', highlights: ['Visualization', 'Customer Portal', 'TypeScript'] },
  { name: 'fence.guru', vertical: 'Home Services', description: 'Platform for invisible fencing, traditional fencing, and privacy consultants to modernize their customer experience.', highlights: ['Fencing', 'Customer Experience', 'Modernization'] },
  { name: 'CommandBridge', vertical: 'Operations', description: 'Purpose-built AI operations console for multi-business management.', highlights: ['Multi-Business', 'AI Ops', 'Console', 'TypeScript'] },
  { name: 'FoodHive', vertical: 'Food Service', description: 'Cloud-based food service management platform.', highlights: ['Cloud', 'Food Service', 'Management'] },
]

export default function PortfolioPage() {
  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold text-white mb-4">Built With Mahoosuc OS</h1>
      <p className="text-xl text-slate-400 mb-12">Real solutions deployed across multiple verticals -- all built on the same AI operating system.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {projects.map((project) => (<PortfolioCard key={project.name} project={project} />))}
      </div>
    </div>
  )
}
