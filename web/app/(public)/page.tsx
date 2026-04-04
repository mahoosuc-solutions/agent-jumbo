import AgentJumboHero from '@/components/product/AgentJumboHero'
import ProofPoints from '@/components/product/ProofPoints'
import HowItWorks from '@/components/product/HowItWorks'
import MosBridge from '@/components/product/MosBridge'
import AgentJumboCTA from '@/components/product/AgentJumboCTA'
import LiveStatus from '@/components/product/LiveStatus'

export default function Home() {
  return (
    <>
      <AgentJumboHero />
      <ProofPoints />
      <HowItWorks />
      <MosBridge />
      <AgentJumboCTA />
      <div className="flex justify-center py-4">
        <LiveStatus />
      </div>
    </>
  )
}
