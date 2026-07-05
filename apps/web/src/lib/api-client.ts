import axios, { type AxiosInstance } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export function createApiClient(token: string): AxiosInstance {
  return axios.create({
    baseURL: BASE_URL,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })
}

// ─── Domain Types ─────────────────────────────────────────────────────────────

export type AgentProfile = {
  id: string
  workspace_id: string
  name: string
  model: string
  system_prompt: string
  temperature: number
  max_tokens: number
  created_at: string
  updated_at: string
}

export type Workspace = {
  id: string
  name: string
  description: string | null
  tech_stack: string[]
  is_default: boolean
  evo_points: number
  created_at: string
  updated_at: string
  agent_profile: AgentProfile | null
}

export type Session = {
  id: string
  workspace_id: string
  title: string
  status: 'active' | 'archived'
  message_count: number
  created_at: string
  updated_at: string
}

export type Artifact = {
  type: 'code' | 'plan' | 'file'
  language?: string
  filename?: string
  content: string
}

export type Message = {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  artifacts: Artifact[]
  tokens_used: number | null
  latency_ms: number | null
  created_at: string
}

export type ChatResponse = {
  user_message: Message
  assistant_message: Message
  session_title: string
}

// ─── API helpers ──────────────────────────────────────────────────────────────

export async function updateWorkspace(
  token: string,
  workspaceId: string,
  data: { name?: string; description?: string | null; tech_stack?: string[] },
): Promise<Workspace> {
  const api = createApiClient(token)
  const res = await api.patch<Workspace>(`/api/v1/workspaces/${workspaceId}`, data)
  return res.data
}

export type WorkspaceStatus = {
  maintenance_mode: boolean
  message: string
  next_available: string | null
}

export async function fetchWorkspaceStatus(
  token: string,
  workspaceId: string,
): Promise<WorkspaceStatus> {
  const api = createApiClient(token)
  const res = await api.get<WorkspaceStatus>(`/api/v1/workspaces/${workspaceId}/status`)
  return res.data
}

export async function fetchWorkspaces(token: string): Promise<Workspace[]> {
  const api = createApiClient(token)
  const res = await api.get<Workspace[]>('/api/v1/workspaces/')
  return res.data
}

export async function fetchSessions(token: string, workspaceId: string): Promise<Session[]> {
  const api = createApiClient(token)
  const res = await api.get<Session[]>(`/api/v1/workspaces/${workspaceId}/sessions/`)
  return res.data
}

export async function fetchMessages(
  token: string,
  workspaceId: string,
  sessionId: string,
): Promise<Message[]> {
  const api = createApiClient(token)
  const res = await api.get<Message[]>(
    `/api/v1/workspaces/${workspaceId}/sessions/${sessionId}/messages`,
  )
  return res.data
}

export function streamChat(
  token: string,
  workspaceId: string,
  sessionId: string,
  message: string,
): Promise<Response> {
  return fetch(`${BASE_URL}/api/v1/workspaces/${workspaceId}/sessions/${sessionId}/chat/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  })
}

export async function trackEvent(
  token: string,
  workspaceId: string,
  sessionId: string | null,
  messageId: string | null,
  eventType: string,
  metadata: Record<string, unknown>,
): Promise<void> {
  const api = createApiClient(token)
  await api.post('/api/v1/events/', {
    workspace_id: workspaceId,
    session_id: sessionId,
    message_id: messageId,
    event_type: eventType,
    metadata,
  })
}

export async function scheduleIdeaReminder(
  token: string,
  workspaceId: string,
  text: string,
  sessionId: string,
  delaySeconds: number,
): Promise<void> {
  const api = createApiClient(token)
  await api.post(`/api/v1/workspaces/${workspaceId}/ideas/remind`, {
    text,
    session_id: sessionId,
    delay_seconds: delaySeconds,
  })
}

export async function submitFeedback(
  token: string,
  workspaceId: string,
  sessionId: string,
  messageId: string,
  score: 1 | 5,
): Promise<void> {
  const api = createApiClient(token)
  await api.post(
    `/api/v1/workspaces/${workspaceId}/sessions/${sessionId}/messages/${messageId}/feedback`,
    { score },
  )
}
