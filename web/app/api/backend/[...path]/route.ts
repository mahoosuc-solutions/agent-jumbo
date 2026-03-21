import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.FLASK_BACKEND_URL || 'http://localhost:50001'

async function proxyRequest(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')
  const url = new URL(`${BACKEND_URL}/${path}`)

  // Forward query params (needed for SSE context/log_version params)
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value)
  })

  const headers = new Headers()
  // Forward relevant headers
  for (const key of ['content-type', 'cookie', 'x-csrf-token', 'authorization']) {
    const val = req.headers.get(key)
    if (val) headers.set(key, val)
  }

  const init: RequestInit = {
    method: req.method,
    headers,
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = await req.text()
  }

  try {
    const upstream = await fetch(url.toString(), init)

    const responseHeaders = new Headers()
    // Forward response headers
    for (const key of ['content-type', 'set-cookie', 'x-csrf-token', 'cache-control']) {
      const val = upstream.headers.get(key)
      if (val) responseHeaders.set(key, val)
    }

    const contentType = upstream.headers.get('content-type') || ''

    // Stream SSE responses instead of buffering them
    if (contentType.includes('text/event-stream') && upstream.body) {
      responseHeaders.set('content-type', 'text/event-stream')
      responseHeaders.set('cache-control', 'no-cache')
      responseHeaders.set('connection', 'keep-alive')

      return new NextResponse(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: responseHeaders,
      })
    }

    // Buffer all other responses normally
    const body = await upstream.arrayBuffer()
    return new NextResponse(body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    })
  } catch {
    return NextResponse.json(
      { error: 'Backend unavailable' },
      { status: 502 },
    )
  }
}

export const GET = proxyRequest
export const POST = proxyRequest
export const PUT = proxyRequest
export const DELETE = proxyRequest
export const PATCH = proxyRequest
