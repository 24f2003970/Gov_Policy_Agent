export type User = {
  id: string; email: string; username: string; role: 'user' | 'admin'
  preferred_language: string; active: boolean; created_at: string; updated_at: string
}
type Tokens = { access_token: string; user: User }
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
let accessToken: string | null = null
let refreshFlight: Promise<User | null> | null = null
let currentUser: User | null = null
const listeners = new Set<(user: User | null) => void>()
const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('gov-auth') : null

function update(tokens: Tokens | null) {
  accessToken = tokens?.access_token || null
  currentUser = tokens?.user || null
  listeners.forEach((listener) => listener(currentUser))
}
channel?.addEventListener('message', (event: MessageEvent<unknown>) => {
  if (event.data === 'logout') update(null)
})

export function subscribe(listener: (user: User | null) => void) {
  listeners.add(listener)
  listener(currentUser)
  return () => { listeners.delete(listener) }
}

async function request(path: string, options: RequestInit = {}, protectedRequest = false): Promise<Response> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  headers.set('X-CSRF-Protection', '1')
  if (protectedRequest && accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  return fetch(`${base}${path}`, { ...options, headers, credentials: 'include', cache: 'no-store',
    signal: AbortSignal.timeout(10000) })
}

async function checked<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { message?: string } } | null
    throw new ApiError(response.status, body?.error?.message || `Request failed (${response.status})`)
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

async function locked<T>(operation: () => Promise<T>): Promise<T> {
  // Web Locks serialize cookie rotation across same-origin tabs. Tokens stay in memory.
  return navigator.locks ? await navigator.locks.request('gov-auth-cookie', operation) : operation()
}

export function restoreSession(): Promise<User | null> {
  if (refreshFlight) return refreshFlight
  refreshFlight = locked(async () => {
    const response = await request('/auth/refresh', { method: 'POST' })
    if (response.status === 401) { update(null); return null }
    const tokens = await checked<Tokens>(response)
    update(tokens)
    return tokens.user
  }).finally(() => { refreshFlight = null })
  return refreshFlight
}

export async function login(email: string, password: string): Promise<User> {
  return locked(async () => {
    const tokens = await checked<Tokens>(await request('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }))
    update(tokens)
    return tokens.user
  })
}

export async function register(email: string, username: string, password: string) {
  return checked<User>(await request('/auth/register', {
    method: 'POST', body: JSON.stringify({ email, username, password }),
  }))
}

export async function logout() {
  await locked(async () => {
    await checked(await request('/auth/logout', { method: 'POST' }, true))
    update(null)
    channel?.postMessage('logout')
  })
}

export async function authorized<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response = await request(path, options, true)
  if (response.status === 401) {
    const restored = await restoreSession()
    if (!restored) throw new ApiError(401, 'Session expired. Please sign in again.')
    response = await request(path, options, true) // Exactly one refresh/retry; no recursion.
    if (response.status === 401) update(null)
  }
  return checked<T>(response)
}
