import ProductHero from '@/components/product/ProductHero'
import PathFork from '@/components/product/PathFork'
import ProofPoints from '@/components/product/ProofPoints'
import HowItWorks from '@/components/product/HowItWorks'
import ProductCTA from '@/components/product/ProductCTA'
import LiveStatus from '@/components/product/LiveStatus'
import SolutionCard from '@/components/product/SolutionCard'
import PortfolioCard from '@/components/product/PortfolioCard'
import { getProducts } from '@/lib/manifest'
import type { PortfolioProject } from '@/components/product/PortfolioCard'

const portfolioProjects: PortfolioProject[] = [
  {
    name: 'HealthData-in-Motion (HDIM)',
    vertical: 'Healthcare',
    description: 'Enterprise HIE platform with FHIR R4, HEDIS measures, and real-time care gap detection.',
    highlights: ['FHIR R4', 'HEDIS', 'Care Gaps', 'Clinical Analytics'],
  },
  {
    name: 'West Bethel Motel',
    vertical: 'Hospitality',
    description: 'Enterprise-grade motel booking system. 792+ tests, 95/100 quality score, production-ready.',
    highlights: ['792+ Tests', '95/100 Quality', 'Booking Engine'],
  },
  {
    name: 'BolducBuilders',
    vertical: 'Home Services',
    description: 'Custom home builders toolkit to help customers visualize their new home.',
    highlights: ['Visualization', 'Customer Portal', 'TypeScript'],
  },
  {
    name: 'CommandBridge',
    vertical: 'Operations',
    description: 'Purpose-built AI operations console for multi-business management.',
    highlights: ['Multi-Business', 'AI Ops', 'Console'],
  },
]

export default function Home() {
  const products = getProducts()
  const featuredProducts = products.slice(0, 6)

  return (
    <>
      <ProductHero />
      <PathFork />
      <ProofPoints />
      {featuredProducts.length > 0 && (
        <section className="py-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-3xl font-bold text-white mb-4">Solutions</h2>
            <p className="text-slate-400 mb-12">Named products within the Mahoosuc OS, each backed by real instruments and tools.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {featuredProducts.map((product) => (
                <SolutionCard key={product.slug} product={product} />
              ))}
            </div>
          </div>
        </section>
      )}
      <HowItWorks />
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-slate-800">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-4">Built With Mahoosuc OS</h2>
          <p className="text-slate-400 mb-12">Real solutions deployed across healthcare, hospitality, home services, and operations.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {portfolioProjects.map((project) => (
              <PortfolioCard key={project.name} project={project} />
            ))}
          </div>
        </div>
      </section>
      <ProductCTA />
      <div className="flex justify-center py-4">
        <LiveStatus />
      </div>
    </>
  )
}
