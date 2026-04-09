import AgentMahooHero from '@/components/product/AgentMahooHero'
import ProofPoints from '@/components/product/ProofPoints'
import HowItWorks from '@/components/product/HowItWorks'
import MosBridge from '@/components/product/MosBridge'
import AgentMahooCTA from '@/components/product/AgentMahooCTA'
import LiveStatus from '@/components/product/LiveStatus'

export default function Home() {
  return (
    <>
      <AgentMahooHero />
      <ProofPoints />
      <HowItWorks />
      <MosBridge />
      <AgentMahooCTA />
      <div className="flex justify-center py-4">
        <LiveStatus />
      </div>
    </>
  )
}
