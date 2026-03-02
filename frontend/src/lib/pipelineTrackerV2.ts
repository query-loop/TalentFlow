import { patchPipelineV2, type PipelineV2Patch } from './pipelinesV2';

export type V2StepKey = 'intake' | 'jd' | 'profile' | 'ats';
export const v2StepOrder: V2StepKey[] = ['intake', 'jd', 'profile', 'ats'];

export function v2PathForStep(step: V2StepKey, pipelineId?: string): string {
  if (!pipelineId) return '/app/pipelines-v2';

  const nested: Record<V2StepKey, string> = {
    intake: `/app/pipeline-v2/${pipelineId}/intake`,
    jd: `/app/pipeline-v2/${pipelineId}/jd`,
    profile: `/app/pipeline-v2/${pipelineId}/profile`,
    ats: `/app/pipeline-v2/${pipelineId}/ats`,
  };

  return nested[step];
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
