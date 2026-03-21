import { type ZodSchema } from 'zod'

const BASE = '/api/backend'

let csrfToken: string | null = null

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken
  const res = await fetch(`${BASE}/csrf_token`, { method: 'GET' })
  if (res.ok) {
    const data = await res.json()
    csrfToken = data.token || ''
  }
  return csrfToken || ''
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown,
  ) {
    super(`API ${status}: ${statusText}`)
    this.name = 'ApiError'
  }
}

export async function api<T = unknown>(
  path: string,
  options: {
    method?: string
    body?: unknown
    params?: Record<string, string>
  } = {},
): Promise<T> {
  const { method = 'POST', body, params } = options

  const url = new URL(`${BASE}/${path}`, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v)
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (method !== 'GET') {
    headers['X-CSRF-Token'] = await ensureCsrf()
  }

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'same-origin',
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    let parsed: unknown = text
    try { parsed = JSON.parse(text) } catch {}
    throw new ApiError(res.status, res.statusText, parsed)
  }

  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return res.json() as Promise<T>
  }

  return res.text() as unknown as T
}

/**
 * Fetch + validate an API response against a Zod schema.
 *
 * The return type is inferred from the schema by default.
 * Dev mode throws on validation failure; production logs a warning only.
 */
export function validatedApi<T>(
  path: string,
  schema: ZodSchema<T>,
  options: { method?: string; body?: unknown; params?: Record<string, string> } = {},
): Promise<T> {
  return api<unknown>(path, options).then((data) => {
    if (process.env.NODE_ENV === 'production') {
      const result = schema.safeParse(data)
      if (!result.success) {
        console.warn(`[API] Response validation failed for ${path}:`, result.error.issues)
      }
      return data as T
    }
    return schema.parse(data) as T
  })
}

export function resetCsrf() {
  csrfToken = null
}
