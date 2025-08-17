import type { RequestEvent } from '@sveltejs/kit';
import { json } from '@sveltejs/kit';

export async function POST({ request }: RequestEvent) {
  const { text = '' } = await request.json().catch(() => ({} as { text?: string }));
  // Toy scoring: count presence of typical ATS-friendly elements
  const checks = [
    { test: /experience|work history/i, tip: 'Add a "Experience" section with clear responsibilities.' },
    { test: /education/i, tip: 'Include an "Education" section.' },
    { test: /skills|technologies/i, tip: 'List a "Skills" or "Technologies" section.' },
    { test: /\b\d{4}\b/, tip: 'Use years to indicate timelines (e.g., 2021-2024).' },
    { test: /achieved|led|built|improved|optimized/i, tip: 'Use action verbs to describe achievements.' }
  ];
  const passed = checks.filter((c) => c.test.test(text));
  const score = Math.round((passed.length / checks.length) * 100);
  const tips = checks.filter((c) => !c.test.test(text)).map((c) => c.tip);
  return json({ score, tips });
}
