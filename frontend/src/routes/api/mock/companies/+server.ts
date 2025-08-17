import type { RequestHandler } from '@sveltejs/kit';

type Company = {
  name: string;
  domain?: string; // used to build a logo URL when provided
  logo?: string; // direct logo URL
  matchScore: number; // 0-100
  roles: string[];
  reason: string;
  openRoles?: number;
  metrics?: {
    relevance?: number; // 0-100
    skills?: number; // 0-100
    roleFit?: number; // 0-100
    location?: number; // 0-100
    culture?: number; // 0-100
    salary?: number; // 0-100
  };
};

const sample: Company[] = [
  { name: 'Microsoft', domain: 'microsoft.com', matchScore: 94, roles: ['Software Engineer', 'Product Engineer'], reason: 'Strong TypeScript, cloud, and platform experience.', openRoles: 12, metrics: { relevance: 95, skills: 92, roleFit: 93, location: 85, culture: 88 } },
  { name: 'Google', domain: 'google.com', matchScore: 91, roles: ['Frontend Engineer'], reason: 'Excellent web performance and UX focus.', openRoles: 7, metrics: { relevance: 92, skills: 90, roleFit: 89, location: 80 } },
  { name: 'Amazon', domain: 'amazon.com', matchScore: 89, roles: ['Fullstack Developer'], reason: 'Kotlin and scalable backend experience align.', openRoles: 9, metrics: { relevance: 90, skills: 88, roleFit: 87 } },
  { name: 'Meta', domain: 'meta.com', matchScore: 86, roles: ['Product Engineer'], reason: 'Modern tooling, Svelte/React ecosystem strength.', openRoles: 5, metrics: { relevance: 87, skills: 85, roleFit: 86 } },
  { name: 'Netflix', domain: 'netflix.com', matchScore: 85, roles: ['Platform Engineer'], reason: 'DevOps and containerization experience fit.', openRoles: 3, metrics: { relevance: 86, skills: 84, roleFit: 83 } },
  { name: 'Salesforce', domain: 'salesforce.com', matchScore: 83, roles: ['UI Engineer'], reason: 'Accessibility and component library experience.', openRoles: 6, metrics: { relevance: 84, skills: 82, roleFit: 80 } },
  { name: 'Acme Corp', matchScore: 92, roles: ['Frontend Engineer', 'UI Engineer'], reason: 'Strong match on Svelte/TypeScript and accessibility.', metrics: { relevance: 93, skills: 91, roleFit: 90 } },
  { name: 'Globex', matchScore: 88, roles: ['Fullstack Developer'], reason: 'Kotlin + Ktor backend skills align well.', metrics: { relevance: 89, skills: 87, roleFit: 86 } },
  { name: 'Initech', matchScore: 84, roles: ['Product Engineer'], reason: 'Experience with Tailwind and modern tooling.', metrics: { relevance: 85, skills: 83, roleFit: 82 } },
  { name: 'Umbrella Labs', matchScore: 80, roles: ['Platform Engineer'], reason: 'DevOps and containerized workflows fit.', metrics: { relevance: 81, skills: 79, roleFit: 78 } },
  { name: 'Hooli', matchScore: 78, roles: ['Frontend Developer'], reason: 'Solid React/Svelte ecosystem knowledge.', metrics: { relevance: 79, skills: 77, roleFit: 76 } }
];

export const GET: RequestHandler = async () => {
  // Compose logo from domain when available
  const withLogos = sample.map((c) => ({
    ...c,
    logo: c.logo || (c.domain ? `https://logo.clearbit.com/${c.domain}` : undefined)
  }));
  return new Response(JSON.stringify(withLogos), {
    headers: { 'content-type': 'application/json' }
  });
};
