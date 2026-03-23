import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Next.js middleware: check for session cookie before serving protected routes.
 * The Flask backend handles actual auth - this just ensures the session cookie exists
 * so we can redirect to login early instead of showing a broken page.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Public routes that don't need auth
  const publicPaths = ['/login', '/api/', '/_next/', '/favicon', '/documentation', '/demo', '/platform', '/solutions', '/portfolio', '/pricing']
  if (pathname === '/' || publicPaths.some((p) => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // Check for any session cookie (session_* pattern from Flask)
  const cookies = request.cookies.getAll()
  const hasSession = cookies.some((c) => c.name.startsWith('session_'))

  if (!hasSession) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all paths except static files and Next.js internals
     */
    '/((?!_next/static|_next/image|favicon\\.ico|favicon\\.svg).*)',
  ],
}
