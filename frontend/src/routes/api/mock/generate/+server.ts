import { json } from '@sveltejs/kit';

function tokenize(text: string) {
  return (text.toLowerCase().match(/[a-zA-Z][a-zA-Z+\-]{1,}/g) || []).filter((w) => w.length > 2);
}

export async function POST({ request }) {
  const { job = '', theme = 'default' } = await request.json().catch(() => ({}));
  const words = tokenize(job);
  const skills = Array.from(new Set(words.filter((w) => ['javascript','typescript','kotlin','java','aws','docker','react','svelte','node','python','sql','graphql','kubernetes','git','ci','cd'].includes(w))));
  const top = Array.from(new Set(words)).slice(0, 6);
  const experience = top.map((w, i) => `Led ${w} initiative improving outcomes by ${15 + i * 3}%`);
  const summary = `Results-driven developer with strong focus on ${top.slice(0,3).join(', ')}. Adaptable to ${theme} theme formatting.`;
  return json({ summary, skills, experience, theme });
}
