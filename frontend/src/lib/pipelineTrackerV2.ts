import { patchPipelineV2, type PipelineV2Patch } from './pipelinesV2';

export type V2StepKey = 'intake' | 'jd' | 'profile' | 'analysis' | 'ats' | 'actions' | 'export';
export const v2StepOrder: V2StepKey[] = ['intake', 'jd', 'profile', 'analysis', 'ats', 'actions', 'export'];

export const v2StepPaths: Record<V2StepKey, string> = {
  intake: '/app/v2/intake',
  jd: '/app/v2/jd',
  profile: '/app/v2/profile',
  analysis: '/app/v2/analysis',
  ats: '/app/v2/ats',
  actions: '/app/v2/actions',
  export: '/app/v2/export',
};

export function v2PathForStep(step: V2StepKey, pipelineId?: string): string {
  if (pipelineId) {
    const nested: Record<V2StepKey, string> = {
      intake: `/app/pipeline-v2/${pipelineId}/intake`,
      jd: `/app/pipeline-v2/${pipelineId}/jd`,
      profile: `/app/pipeline-v2/${pipelineId}/profile`,
      analysis: `/app/pipeline-v2/${pipelineId}/analysis`,
      ats: `/app/pipeline-v2/${pipelineId}/ats`,
      actions: `/app/pipeline-v2/${pipelineId}/actions`,
      export: `/app/pipeline-v2/${pipelineId}/export`,
    };
    return nested[step];
  }
  return v2StepPaths[step];
}

export async function v2MarkStepProgressFor(id: string, current: V2StepKey): Promise<void> {
  const idx = v2StepOrder.indexOf(current);
  const patch: PipelineV2Patch = { statuses: {} } as any;
  if (idx > 0) {
    (patch.statuses as any)[v2StepOrder[idx-1]] = 'complete';
  }
  (patch.statuses as any)[current] = 'active';
  try { await patchPipelineV2(id, patch); } catch {}
}
