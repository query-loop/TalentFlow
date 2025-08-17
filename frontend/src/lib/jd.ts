export type ExtractedJD = {
  title?: string;
  company?: string;
  location?: string;
  experienceYears?: number | null;
  seniority?: string | null;
  skills: string[];
  responsibilities: string[];
  requirements: string[];
  raw: string;
  when: number;
};

export type RefConfig = {
  includeMeta: boolean;
  includeSkills: boolean;
  includeRequirements: boolean;
  includeResponsibilities: boolean;
  topSkills: number;
  topRequirements: number;
  topResponsibilities: number;
  maxChars: number;
};

export function normalizeText(t: string) {
  return (t || '').replace(/\r/g, '').trim();
}

export function guessSeniority(t: string): string | null {
  const map = [
    /\b(intern|internship)\b/i,
    /\b(junior|jr\.?|entry[- ]?level)\b/i,
    /\b(mid|intermediate)\b/i,
    /\b(senior|sr\.?)\b/i,
    /\b(staff)\b/i,
    /\b(principal)\b/i,
    /\b(lead)\b/i,
    /\b(manager|management)\b/i,
    /\b(director|head)\b/i
  ];
  const labels = ['Intern', 'Junior', 'Mid', 'Senior', 'Staff', 'Principal', 'Lead', 'Manager', 'Director'];
  for (let i = labels.length - 1; i >= 0; i--) {
    if (map[i].test(t)) return labels[i];
  }
  return null;
}

export function findSkills(t: string): string[] {
  const dictionary = [
    'javascript','typescript','svelte','react','vue','angular','node','express','kotlin','java','spring','ktor','python','django','flask','fastapi','c#','dotnet','go','rust','sql','postgres','mysql','mongodb','redis','graphql','rest','aws','gcp','azure','docker','kubernetes','terraform','ansible','git','ci/cd','jenkins','github actions','tailwind','css','html','sass','less','webpack','vite','jest','vitest','playwright','cypress','android','ios','swift','objective-c'
  ];
  const lc = t.toLowerCase();
  const found = new Set<string>();
  for (const k of dictionary) {
    const re = new RegExp(`(^|[^a-z])${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?=$|[^a-z])`, 'i');
    if (re.test(lc)) found.add(k.toLowerCase());
  }
  return Array.from(found).map(s => s.toUpperCase() === s ? s : s.replace(/(^|\s)\w/g, (m) => m.toUpperCase()));
}

export function extractSections(t: string) {
  const lines = t.split(/\n+/).map(l => l.trim()).filter(Boolean);
  const norm = (s: string) => s.replace(/^[-*•\u2022\u25CF\u25E6\s]+/, '').replace(/\s{2,}/g, ' ').trim();
  const collect = (pred: (l: string) => boolean) => {
    const set = new Set<string>();
    for (const l of lines) {
      if (!pred(l)) continue;
      const v = norm(l);
      if (!v) continue;
      const key = v.toLowerCase();
      if (!set.has(key)) set.add(key);
    }
    return Array.from(set).map(s => s.replace(/(^|\s)\w/g, (m) => m.toUpperCase()));
  };
  const bulletRe = /^(?:[-*•\u2022\u25CF\u25E6]|\d+\.)\s/i;
  const responsibilities = collect((l) => bulletRe.test(l) || /^responsibilities?:/i.test(l) || /^what you(?:'|\s)ll do:?/i.test(l)).slice(0, 12);
  const requirements = collect((l) => /^requirements?:/i.test(l) || /^qualifications?:/i.test(l) || bulletRe.test(l)).slice(0, 12);
  return { responsibilities, requirements };
}

export function formatJD(t: string): string {
  let s = normalizeText(t)
    .replace(/[\t\u00A0]+/g, ' ')
    .replace(/\r\n/g, '\n')
    .replace(/\s+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n');
  // Standardize bullets to "- " and ensure a space after
  s = s.replace(/^[•\u2022\u25CF\u25E6]\s*/gm, '- ')
       .replace(/^\*\s*/gm, '- ')
       .replace(/^(\d+)\.\s*/gm, '$1. ');
  // Normalize common section headings casing
  s = s.replace(/^responsibilities:?$/gim, 'Responsibilities:')
       .replace(/^requirements:?$/gim, 'Requirements:')
       .replace(/^qualifications:?$/gim, 'Qualifications:')
       .replace(/^what you(?:'|\s)ll do:?$/gim, "What you'll do:");
  return s.trim();
}

export function extractMeta(t: string) {
  const firstLine = t.split(/\n/)[0] || '';
  let title: string | undefined;
  let company: string | undefined;
  let location: string | undefined;
  const titleMatch = t.match(/(?:^|\n)\s*(?:role|title)\s*[:\-]\s*(.+)/i);
  if (titleMatch) title = titleMatch[1].trim();
  const companyMatch = t.match(/(?:^|\n)\s*(?:company)\s*[:\-]\s*(.+)/i);
  if (companyMatch) company = companyMatch[1].trim();
  const locMatch = t.match(/(?:^|\n)\s*(?:location)\s*[:\-]\s*(.+)/i);
  if (locMatch) location = locMatch[1].trim();
  if (!title) {
    const f = firstLine.match(/^(.*?)\s+at\s+(.*)$/i);
    if (f) { title = f[1].trim(); if (!company) company = f[2].trim(); }
    else title = firstLine.trim();
  }
  return { title, company, location };
}

export function extractExperienceYears(t: string): number | null {
  const m = t.match(/(\d+)\+?\s*(?:years|yrs)/i);
  return m ? Number(m[1]) : null;
}

export function buildReferenceText(ex: ExtractedJD | null, cfg: RefConfig): string {
  if (!ex) return '';
  const parts: string[] = [];
  if (cfg.includeMeta) {
    const meta: string[] = [];
    if (ex.title) meta.push(ex.title);
    if (ex.company) meta.push(`at ${ex.company}`);
    if (ex.location) meta.push(`(${ex.location})`);
    const head = meta.join(' ').trim();
    const line2: string[] = [];
    if (ex.seniority) line2.push(`Seniority: ${ex.seniority}`);
    if (ex.experienceYears != null) line2.push(`${ex.experienceYears}+ years`);
    if (head) parts.push(`Role: ${head}`);
    if (line2.length) parts.push(line2.join(' · '));
  }
  if (cfg.includeSkills && ex.skills?.length) {
    parts.push(`Top skills: ${ex.skills.slice(0, cfg.topSkills).join(', ')}`);
  }
  if (cfg.includeRequirements && ex.requirements?.length) {
    parts.push('Key requirements:');
    for (const it of ex.requirements.slice(0, cfg.topRequirements)) parts.push(`- ${it}`);
  }
  if (cfg.includeResponsibilities && ex.responsibilities?.length) {
    parts.push('Responsibilities:');
    for (const it of ex.responsibilities.slice(0, cfg.topResponsibilities)) parts.push(`- ${it}`);
  }
  let text = parts.join('\n');
  if (text.length > cfg.maxChars) text = text.slice(0, cfg.maxChars - 3).trimEnd() + '...';
  return text;
}
