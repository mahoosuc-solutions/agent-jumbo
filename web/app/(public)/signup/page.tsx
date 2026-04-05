import type { Metadata } from 'next'
import SignupWidget from './SignupWidget'

export const metadata: Metadata = {
  title: 'Sign Up',
  description: 'Get started with Mahoosuc OS — Free Cloud, Pro, or self-hosted Community edition.',
}

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ plan?: string }>
}) {
  const { plan = 'free_cloud' } = await searchParams
  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-lg mx-auto">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-white mb-2">Get Started</h1>
        <p className="text-slate-400">
          No credit card required for Free Cloud. Upgrade any time.
        </p>
      </div>
      <SignupWidget initialPlan={plan} />
    </div>
  )
}
