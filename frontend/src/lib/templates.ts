export type Template = {
  id: string;
  name: string;
  description: string;
};

// Source of truth for available resume templates.
export const templates: Template[] = [
  {
    id: 'default',
    name: 'Default',
    description: 'Clean, balanced layout for most roles.'
  },
  {
    id: 'modern',
    name: 'Modern',
    description: 'Contemporary styling with accent headings.'
  },
  {
    id: 'classic',
    name: 'Classic',
    description: 'Traditional serif-inspired layout.'
  }
];

export function setActiveTemplate(id: string) {
  try { localStorage.setItem('tf_template', id); } catch {}
}

export function getActiveTemplate(): string | null {
  try { return localStorage.getItem('tf_template'); } catch { return null; }
}
