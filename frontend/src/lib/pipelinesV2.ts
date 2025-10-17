import { PUBLIC_API_BASE } from '$env/static/public';

export type V2StepStatus = 'pending' | 'active' | 'complete' | 'failed';
// Full V2 step set to match backend API
export type V2StepKey = 'intake' | 'jd' | 'profile' | 'analysis' | 'ats' | 'actions' | 'export';
export type V2Statuses = Record<V2StepKey, V2StepStatus>;

export type PipelineV2 = {
  id: string;
  name: string;
  createdAt: number;
  company?: string | null;
  jdId?: string | null;
  resumeId?: string | null;
  statuses: V2Statuses;
  artifacts?: Record<string, unknown>;
};

export type PipelineV2Create = { name: string; company?: string | null; jdId?: string | null; resumeId?: string | null };
export type PipelineV2Patch = { name?: string; company?: string | null; jdId?: string | null; resumeId?: string | null; statuses?: Partial<V2Statuses>; artifacts?: Record<string, unknown> };
export type PipelineV2RunResult = { pipeline: PipelineV2; log: string[] };

const BASE = (typeof window !== 'undefined')
  ? ((PUBLIC_API_BASE && PUBLIC_API_BASE.length) ? (PUBLIC_API_BASE || '').replace(/\/$/, '') : '')
  : (PUBLIC_API_BASE || '').replace(/\/$/, '');

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { headers: { 'content-type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export async function listPipelinesV2(): Promise<PipelineV2[]> {
  return http(`${BASE}/api/pipelines-v2`);
}

export async function createPipelineV2(input: PipelineV2Create): Promise<PipelineV2> {
  return http(`${BASE}/api/pipelines-v2`, { method: 'POST', body: JSON.stringify(input) });
}

export async function getPipelineV2(id: string): Promise<PipelineV2> {
  return http(`${BASE}/api/pipelines-v2/${id}`);
}

export async function patchPipelineV2(id: string, patch: PipelineV2Patch): Promise<PipelineV2> {
  return http(`${BASE}/api/pipelines-v2/${id}`, { method: 'PATCH', body: JSON.stringify(patch) });
}

export async function deletePipelineV2(id: string): Promise<void> {
  await fetch(`${BASE}/api/pipelines-v2/${id}`, { method: 'DELETE' });
}

export async function runPipelineV2(id: string): Promise<PipelineV2RunResult> {
  return http(`${BASE}/api/pipelines-v2/${id}/run`, { method: 'POST' });
}

export async function getExtractionStats(): Promise<any> {
  return http(`${BASE}/api/pipelines-v2/stats/extraction`);
}

export async function retryJdAnalysis(id: string): Promise<PipelineV2> {
  return http(`${BASE}/api/pipelines-v2/${id}/jd/retry`, { method: 'POST' });
}
