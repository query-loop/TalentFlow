import type { PageLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: PageLoad = async ({ params }) => {
  // Default to intake step (first step in v2 flow)
  throw redirect(307, `/app/pipeline-v2/${params.id}/intake`);
};
