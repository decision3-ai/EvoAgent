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
