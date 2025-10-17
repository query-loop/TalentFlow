import { patchPipeline, type PipelinePatch } from './pipelines';

export type StepKey = 'extract' | 'profile' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';
export const stepOrder: StepKey[] = ['extract','profile','generate','keywords','ats','export','save'];
export const stepPaths: Record<StepKey, string> = {
  extract: '/app/extract',
  profile: '/app/generate', // fallback to generate for global nav
  generate: '/app/generate',
  keywords: '/app/keywords',
  ats: '/app/ats',
  export: '/app/export',
  save: '/app/library'
};

export function pathForStep(step: StepKey, pipelineId?: string): string {
  if (pipelineId) {
    const nested: Record<StepKey, string> = {
      extract: `/app/pipeline/${pipelineId}/extract`,
      profile: `/app/pipeline/${pipelineId}/profile`,
      generate: `/app/pipeline/${pipelineId}/generate`,
      keywords: `/app/pipeline/${pipelineId}/keywords`,
      ats: `/app/pipeline/${pipelineId}/ats`,
      export: `/app/pipeline/${pipelineId}/export`,
      save: `/app/pipeline/${pipelineId}/save`,
    };
    return nested[step];
  }
  return stepPaths[step];
}

export function getActivePipelineId(): string | null {
  try { return localStorage.getItem('tf_active_pipeline'); } catch { return null; }
}

export function setActivePipelineId(id: string) {
  try { localStorage.setItem('tf_active_pipeline', id); } catch {}
}

export async function markStepProgress(current: StepKey): Promise<void> {
  const id = getActivePipelineId();
  if (!id) return;
  const idx = stepOrder.indexOf(current);
  const patch: PipelinePatch = { statuses: {} } as any;
  if (idx > 0) {
    (patch.statuses as any)[stepOrder[idx-1]] = 'complete';
  }
  (patch.statuses as any)[current] = 'active';
  try { await patchPipeline(id, patch); } catch {}
}

export async function markStepProgressFor(id: string, current: StepKey): Promise<void> {
  const idx = stepOrder.indexOf(current);
  const patch: PipelinePatch = { statuses: {} } as any;
  if (idx > 0) {
    (patch.statuses as any)[stepOrder[idx-1]] = 'complete';
  }
  (patch.statuses as any)[current] = 'active';
  try { await patchPipeline(id, patch); } catch {}
}

export function percentFromStatuses(statuses: Record<StepKey, string> | undefined): number {
  if (!statuses) return 0;
  const total = stepOrder.length;
  const done = stepOrder.filter(k => statuses[k] === 'complete').length;
  return Math.round((done / Math.max(1,total)) * 100);
}
