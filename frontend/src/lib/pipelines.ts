import { PUBLIC_API_BASE } from '$env/static/public';

export type StepStatus = 'pending' | 'active' | 'complete' | 'failed';
export type StepKey = 'extract' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';
export type Statuses = Record<StepKey, StepStatus>;

export type Pipeline = {
  id: string;
  name: string;
  createdAt: number;
  company?: string | null;
  jdId?: string | null;
  resumeId?: string | null;
  statuses: Statuses;
};

export type PipelineCreate = { name: string; company?: string | null; jdId?: string | null; resumeId?: string | null };
export type PipelinePatch = { name?: string; company?: string | null; jdId?: string | null; resumeId?: string | null; statuses?: Partial<Statuses> };
export type PipelineRunResult = { pipeline: Pipeline; log: string[] };

// If PUBLIC_API_BASE is set, use it; otherwise, use relative URLs (Vite proxy in dev / same origin in prod)
const BASE = (typeof window !== 'undefined')
  ? ((PUBLIC_API_BASE && PUBLIC_API_BASE.length) ? (PUBLIC_API_BASE || '').replace(/\/$/, '') : '')
  : (PUBLIC_API_BASE || '').replace(/\/$/, '');

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { headers: { 'content-type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export async function listPipelines(): Promise<Pipeline[]> {
  return http(`${BASE}/api/pipelines`);
}

export async function createPipeline(input: PipelineCreate): Promise<Pipeline> {
  return http(`${BASE}/api/pipelines`, { method: 'POST', body: JSON.stringify(input) });
}

export async function getPipeline(id: string): Promise<Pipeline> {
  return http(`${BASE}/api/pipelines/${id}`);
}

export async function patchPipeline(id: string, patch: PipelinePatch): Promise<Pipeline> {
  return http(`${BASE}/api/pipelines/${id}`, { method: 'PATCH', body: JSON.stringify(patch) });
}

export async function deletePipeline(id: string): Promise<void> {
  await fetch(`${BASE}/api/pipelines/${id}`, { method: 'DELETE' });
}

export async function runPipeline(id: string): Promise<PipelineRunResult> {
  return http(`${BASE}/api/pipelines/${id}/run`, { method: 'POST' });
}
