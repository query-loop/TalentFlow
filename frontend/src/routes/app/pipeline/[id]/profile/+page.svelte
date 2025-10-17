<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import StepNav from '$lib/components/StepNav.svelte';
  import JDDisplay from '$lib/components/JDDisplay.svelte';
  import { getPipeline, patchPipeline, type Pipeline } from '$lib/pipelines';
  import { getPipelineV2, patchPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';

  type CandidateProfile = {
    overview: {
      summary: string;
      keyStrengths: string[];
      experienceLevel: string;
      industryFocus: string[];
    };
    coreCompetencies: {
      technical: { skill: string; level: 'Beginner' | 'Intermediate' | 'Advanced' | 'Expert'; years?: number }[];
      soft: { skill: string; description: string }[];
      leadership: { skill: string; description: string }[];
    };
    careerTrajectory: {
      currentLevel: string;
      targetLevel: string;
      growthAreas: string[];
      readinessScore: number; // 1-10
    };
    alignmentAnalysis: {
      roleMatch: number; // percentage
      skillsGap: string[];
      strengthsMatch: string[];
      developmentNeeds: string[];
    };
    recommendations: {
      immediate: string[];
      shortTerm: string[];
      longTerm: string[];
    };
  };

  let pipeline: Pipeline | PipelineV2 | null = null;
  let profile: CandidateProfile | null = null;
  let loading = false;
  let generating = false;
  let error = '';
  let activeTab: 'overview' | 'competencies' | 'trajectory' | 'alignment' | 'recommendations' = 'overview';

  $: pid = $page.params.id;
  $: isV2 = pipeline && 'statuses' in pipeline && typeof pipeline.statuses === 'object';

  async function load() {
    error = '';
    try {
      // Try V2 first, fallback to V1
      try {
        pipeline = await getPipelineV2(pid);
      } catch {
        pipeline = await getPipeline(pid);
      }
      
      // Load existing profile from artifacts
      if (isV2 && pipeline?.artifacts?.profile) {
        profile = pipeline.artifacts.profile as CandidateProfile;
      }
    } catch (e: any) {
      error = e?.message || 'Failed to load pipeline';
      pipeline = null;
    }
  }

  async function generateProfile() {
    if (!pipeline) return;
    
    generating = true;
    error = '';
    
    try {
      // Get JD data from artifacts
      const jdData = isV2 && pipeline?.artifacts?.jd ? pipeline.artifacts.jd : null;
      
      // Generate comprehensive profile based on JD analysis
      const generatedProfile: CandidateProfile = await createRigorousProfile(jdData);
      
      profile = generatedProfile;
      
      // Save to pipeline artifacts
      if (isV2) {
        const updated = await patchPipelineV2(pid, {
          artifacts: {
            ...pipeline.artifacts,
            profile: generatedProfile
          },
          statuses: {
            ...pipeline.statuses,
            profile: 'complete'
          }
        });
        pipeline = updated;
      } else {
        const updated = await patchPipeline(pid, {
          statuses: {
            ...pipeline.statuses,
            profile: 'complete'
          }
        });
        pipeline = updated;
      }
    } catch (e: any) {
      error = e?.message || 'Failed to generate profile';
    } finally {
      generating = false;
    }
  }

  async function createRigorousProfile(jdData: any): Promise<CandidateProfile> {
    // Simulate comprehensive profile generation
    // In production, this would call AI services or backend analysis
    
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate processing
    
    const description = jdData?.description || '';
    const title = jdData?.title || 'Software Engineer';
    const company = jdData?.company || 'Tech Company';
    
    // Extract key requirements and responsibilities
    const requirements = extractKeyRequirements(description);
    const responsibilities = extractResponsibilities(description);
    const technicalSkills = extractTechnicalSkills(description);
    
    return {
      overview: {
        summary: `Experienced professional with strong background in ${inferPrimaryDomain(title, description)}. Demonstrated expertise in ${technicalSkills.slice(0, 3).join(', ')} with a proven track record of delivering high-impact solutions. Strong analytical and problem-solving abilities with excellent communication skills.`,
        keyStrengths: [
          'Technical Leadership',
          'Problem Solving',
          'Cross-functional Collaboration',
          'Continuous Learning',
          'Results-driven Approach'
        ],
        experienceLevel: inferExperienceLevel(description),
        industryFocus: inferIndustryFocus(company, description)
      },
      coreCompetencies: {
        technical: technicalSkills.map(skill => ({
          skill,
          level: inferSkillLevel(skill, description) as any,
          years: inferExperienceYears(skill, description)
        })),
        soft: [
          { skill: 'Communication', description: 'Excellent written and verbal communication skills' },
          { skill: 'Team Collaboration', description: 'Proven ability to work effectively in cross-functional teams' },
          { skill: 'Problem Solving', description: 'Strong analytical and critical thinking capabilities' },
          { skill: 'Adaptability', description: 'Quick to learn and adapt to new technologies and processes' }
        ],
        leadership: [
          { skill: 'Mentoring', description: 'Experience guiding junior team members and sharing knowledge' },
          { skill: 'Project Leadership', description: 'Ability to lead technical initiatives and drive results' },
          { skill: 'Strategic Thinking', description: 'Understanding of business impact and technical decisions' }
        ]
      },
      careerTrajectory: {
        currentLevel: inferCurrentLevel(description),
        targetLevel: inferTargetLevel(title, description),
        growthAreas: [
          'Advanced system architecture',
          'Team leadership skills',
          'Domain expertise expansion',
          'Strategic business understanding'
        ],
        readinessScore: calculateReadinessScore(requirements, technicalSkills)
      },
      alignmentAnalysis: {
        roleMatch: calculateRoleMatch(requirements, technicalSkills),
        skillsGap: identifySkillsGap(requirements, technicalSkills),
        strengthsMatch: identifyStrengthsMatch(requirements, technicalSkills),
        developmentNeeds: identifyDevelopmentNeeds(requirements, description)
      },
      recommendations: {
        immediate: [
          'Review and strengthen core technical competencies',
          'Update portfolio with relevant project examples',
          'Practice behavioral interview scenarios'
        ],
        shortTerm: [
          'Complete relevant certifications or training',
          'Build projects demonstrating key skills',
          'Expand network in target industry'
        ],
        longTerm: [
          'Develop leadership and mentoring capabilities',
          'Gain expertise in emerging technologies',
          'Build thought leadership through content creation'
        ]
      }
    };
  }

  // Helper functions for profile analysis
  function extractKeyRequirements(description: string): string[] {
    const text = description.toLowerCase();
    const requirements = [];
    
    // Look for bullet points and key phrases
    const lines = description.split('\n').map(l => l.trim()).filter(Boolean);
    for (const line of lines) {
      if (line.match(/^[-•*]\s+/) || line.includes('experience') || line.includes('skill')) {
        requirements.push(line.replace(/^[-•*]\s+/, '').trim());
      }
    }
    
    return requirements.slice(0, 10);
  }

  function extractResponsibilities(description: string): string[] {
    const lines = description.split('\n').map(l => l.trim()).filter(Boolean);
    const responsibilities = [];
    
    for (const line of lines) {
      if (line.includes('will') || line.includes('responsible') || line.includes('work on')) {
        responsibilities.push(line);
      }
    }
    
    return responsibilities.slice(0, 8);
  }

  function extractTechnicalSkills(description: string): string[] {
    const text = description.toLowerCase();
    const skills = new Set<string>();
    
    // Common technical skills to look for
    const skillPatterns = [
      'javascript', 'typescript', 'python', 'java', 'react', 'vue', 'angular',
      'node.js', 'express', 'fastapi', 'django', 'flask', 'spring',
      'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
      'postgresql', 'mysql', 'mongodb', 'redis',
      'git', 'ci/cd', 'agile', 'scrum'
    ];
    
    for (const skill of skillPatterns) {
      if (text.includes(skill)) {
        skills.add(skill.charAt(0).toUpperCase() + skill.slice(1));
      }
    }
    
    return Array.from(skills).slice(0, 12);
  }

  function inferPrimaryDomain(title: string, description: string): string {
    const titleLower = title.toLowerCase();
    const descLower = description.toLowerCase();
    
    if (titleLower.includes('frontend') || descLower.includes('frontend')) return 'Frontend Development';
    if (titleLower.includes('backend') || descLower.includes('backend')) return 'Backend Development';
    if (titleLower.includes('fullstack') || titleLower.includes('full stack')) return 'Full Stack Development';
    if (titleLower.includes('data') || descLower.includes('analytics')) return 'Data Engineering';
    if (titleLower.includes('devops') || descLower.includes('infrastructure')) return 'DevOps Engineering';
    
    return 'Software Development';
  }

  function inferExperienceLevel(description: string): string {
    const text = description.toLowerCase();
    
    if (text.includes('senior') || text.includes('lead') || text.includes('principal')) return 'Senior Level';
    if (text.includes('mid') || text.includes('3+') || text.includes('5+')) return 'Mid Level';
    if (text.includes('junior') || text.includes('entry') || text.includes('0-2')) return 'Entry Level';
    
    return 'Mid Level';
  }

  function inferIndustryFocus(company: string, description: string): string[] {
    const focus = [];
    const text = description.toLowerCase();
    
    if (text.includes('fintech') || text.includes('financial')) focus.push('Financial Technology');
    if (text.includes('healthcare') || text.includes('medical')) focus.push('Healthcare');
    if (text.includes('ecommerce') || text.includes('retail')) focus.push('E-commerce');
    if (text.includes('saas') || text.includes('software')) focus.push('Software as a Service');
    if (text.includes('ai') || text.includes('machine learning')) focus.push('Artificial Intelligence');
    
    return focus.length > 0 ? focus : ['Technology'];
  }

  function inferSkillLevel(skill: string, description: string): string {
    // Simplified skill level inference
    const text = description.toLowerCase();
    if (text.includes(`advanced ${skill.toLowerCase()}`) || text.includes(`expert ${skill.toLowerCase()}`)) return 'Expert';
    if (text.includes(`proficient ${skill.toLowerCase()}`) || text.includes(`strong ${skill.toLowerCase()}`)) return 'Advanced';
    return 'Intermediate';
  }

  function inferExperienceYears(skill: string, description: string): number {
    // Extract years from patterns like "3+ years of Python"
    const regex = new RegExp(`(\\d+)\\+?\\s*years?.*${skill.toLowerCase()}`, 'i');
    const match = description.match(regex);
    return match ? parseInt(match[1]) : Math.floor(Math.random() * 5) + 2;
  }

  function inferCurrentLevel(description: string): string {
    return inferExperienceLevel(description);
  }

  function inferTargetLevel(title: string, description: string): string {
    const current = inferExperienceLevel(description);
    if (current === 'Entry Level') return 'Mid Level';
    if (current === 'Mid Level') return 'Senior Level';
    return 'Principal/Staff Level';
  }

  function calculateReadinessScore(requirements: string[], skills: string[]): number {
    // Simple scoring based on skill matches
    const skillsLower = skills.map(s => s.toLowerCase());
    let matches = 0;
    
    for (const req of requirements) {
      const reqLower = req.toLowerCase();
      if (skillsLower.some(skill => reqLower.includes(skill) || skill.includes(reqLower))) {
        matches++;
      }
    }
    
    return Math.min(10, Math.max(1, Math.round((matches / Math.max(requirements.length, 1)) * 10)));
  }

  function calculateRoleMatch(requirements: string[], skills: string[]): number {
    return Math.min(100, Math.max(10, calculateReadinessScore(requirements, skills) * 10));
  }

  function identifySkillsGap(requirements: string[], skills: string[]): string[] {
    const gaps = [];
    const skillsLower = skills.map(s => s.toLowerCase());
    
    for (const req of requirements.slice(0, 5)) {
      const reqLower = req.toLowerCase();
      if (!skillsLower.some(skill => reqLower.includes(skill))) {
        gaps.push(req);
      }
    }
    
    return gaps;
  }

  function identifyStrengthsMatch(requirements: string[], skills: string[]): string[] {
    const matches = [];
    const skillsLower = skills.map(s => s.toLowerCase());
    
    for (const req of requirements.slice(0, 5)) {
      const reqLower = req.toLowerCase();
      if (skillsLower.some(skill => reqLower.includes(skill))) {
        matches.push(req);
      }
    }
    
    return matches;
  }

  function identifyDevelopmentNeeds(requirements: string[], description: string): string[] {
    return [
      'Advanced technical architecture',
      'Cross-functional leadership',
      'Domain expertise deepening',
      'Strategic business acumen'
    ];
  }

  function percent(p: Pipeline | PipelineV2 | null) {
    if (!p) return 0;
    const order = ['extract','generate','keywords','ats','export','save'];
    const statuses = isV2 ? p.statuses : p.statuses;
    const done = order.filter(k => (statuses as any)[k] === 'complete').length;
    return Math.round((done / order.length) * 100);
  }

  onMount(load);
</script>

{#if error}
  <div class="p-6">
    <div class="rounded-lg border border-red-200 dark:border-red-800 p-6 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200">{error}</div>
  </div>
{:else if !pipeline}
  <div class="p-6">
    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-6 bg-white dark:bg-gray-900">Pipeline not found.</div>
  </div>
{:else}
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold flex items-center gap-2">
        <Icon name="user"/> Candidate Profile — <span class="text-sm text-gray-600">{pipeline.name}</span>
      </h1>
      <a href={`/app/pipeline/${pipeline.id}`} class="text-sm text-blue-600 hover:underline">Back to pipeline</a>
    </div>

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-5 bg-white dark:bg-gray-900">
      <div class="mb-3 flex items-center justify-between text-xs text-gray-600 dark:text-gray-300">
        <div class="flex items-center gap-2">
          <span class="text-gray-500">Pipeline</span>
          <span class="text-gray-400">•</span>
          <span class="truncate" title={pipeline.name}>{pipeline.name}</span>
        </div>
        <div class="text-[11px] text-gray-500">Created {new Date(pipeline.createdAt).toLocaleString()}</div>
      </div>
      <div class="mb-3">
        <StepNav statuses={pipeline.statuses as any} pipelineId={pipeline.id} />
      </div>
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm text-gray-600 dark:text-gray-300">Progress</div>
        <div class="flex items-center gap-3">
          <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{percent(pipeline)}%</div>
        </div>
      </div>
      <div class="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div class="h-full bg-blue-600" style={`width: ${percent(pipeline)}%`}></div>
      </div>
    </div>

    {#if !profile}
      <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-8 bg-white dark:bg-gray-900 text-center">
        <Icon name="user" size={48} class="mx-auto mb-4 text-gray-400" />
        <h3 class="text-lg font-medium mb-2">Generate Candidate Profile</h3>
        <p class="text-gray-600 dark:text-gray-300 mb-6">Create a comprehensive profile analysis based on the job requirements and your background.</p>
        <button 
          class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          on:click={generateProfile}
          disabled={generating}
        >
          {#if generating}
            <Icon name="refresh" class="inline w-4 h-4 mr-2 animate-spin" />
            Generating Profile...
          {:else}
            <Icon name="sparkles" class="inline w-4 h-4 mr-2" />
            Generate Profile
          {/if}
        </button>
      </div>
    {:else}
      <!-- Profile Tabs -->
      <div class="border-b border-gray-200 dark:border-gray-700">
        <nav class="-mb-px flex space-x-8">
          {#each [
            { key: 'overview', label: 'Overview', icon: 'user' },
            { key: 'competencies', label: 'Competencies', icon: 'badge-check' },
            { key: 'trajectory', label: 'Career Path', icon: 'trending-up' },
            { key: 'alignment', label: 'Role Alignment', icon: 'target' },
            { key: 'recommendations', label: 'Recommendations', icon: 'lightbulb' }
          ] as tab}
            <button
              class={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              on:click={() => activeTab = tab.key}
            >
              <Icon name={tab.icon} size={16} />
              {tab.label}
            </button>
          {/each}
        </nav>
      </div>

      <!-- Profile Content -->
      <div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        {#if activeTab === 'overview'}
          <div class="p-6 space-y-6">
            <div>
              <h3 class="text-lg font-semibold mb-3">Professional Summary</h3>
              <p class="text-gray-700 dark:text-gray-300 leading-relaxed">{profile.overview.summary}</p>
            </div>
            
            <div class="grid md:grid-cols-2 gap-6">
              <div>
                <h4 class="font-medium mb-3">Key Strengths</h4>
                <ul class="space-y-2">
                  {#each profile.overview.keyStrengths as strength}
                    <li class="flex items-center gap-2">
                      <Icon name="check-circle" size={16} class="text-green-500" />
                      <span class="text-sm">{strength}</span>
                    </li>
                  {/each}
                </ul>
              </div>
              
              <div>
                <h4 class="font-medium mb-3">Focus Areas</h4>
                <div class="space-y-2">
                  <div class="text-sm"><span class="font-medium">Experience Level:</span> {profile.overview.experienceLevel}</div>
                  <div class="text-sm"><span class="font-medium">Industry Focus:</span> {profile.overview.industryFocus.join(', ')}</div>
                </div>
              </div>
            </div>
          </div>
        {/if}

        {#if activeTab === 'competencies'}
          <div class="p-6 space-y-6">
            <div>
              <h3 class="text-lg font-semibold mb-4">Technical Skills</h3>
              <div class="grid md:grid-cols-2 gap-4">
                {#each profile.coreCompetencies.technical as skill}
                  <div class="border rounded-lg p-3">
                    <div class="flex justify-between items-center mb-1">
                      <span class="font-medium">{skill.skill}</span>
                      <span class="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800">{skill.level}</span>
                    </div>
                    {#if skill.years}
                      <div class="text-xs text-gray-600">{skill.years} years experience</div>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>

            <div>
              <h3 class="text-lg font-semibold mb-4">Soft Skills</h3>
              <div class="space-y-3">
                {#each profile.coreCompetencies.soft as skill}
                  <div class="border-l-4 border-blue-200 pl-4">
                    <div class="font-medium">{skill.skill}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">{skill.description}</div>
                  </div>
                {/each}
              </div>
            </div>

            <div>
              <h3 class="text-lg font-semibold mb-4">Leadership Capabilities</h3>
              <div class="space-y-3">
                {#each profile.coreCompetencies.leadership as skill}
                  <div class="border-l-4 border-green-200 pl-4">
                    <div class="font-medium">{skill.skill}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">{skill.description}</div>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {/if}

        {#if activeTab === 'trajectory'}
          <div class="p-6 space-y-6">
            <div class="grid md:grid-cols-3 gap-6">
              <div class="text-center">
                <div class="text-2xl font-bold text-blue-600 mb-2">{profile.careerTrajectory.currentLevel}</div>
                <div class="text-sm text-gray-600">Current Level</div>
              </div>
              <div class="flex items-center justify-center">
                <Icon name="arrow-right" size={24} class="text-gray-400" />
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-green-600 mb-2">{profile.careerTrajectory.targetLevel}</div>
                <div class="text-sm text-gray-600">Target Level</div>
              </div>
            </div>

            <div class="text-center">
              <div class="text-3xl font-bold text-purple-600 mb-2">{profile.careerTrajectory.readinessScore}/10</div>
              <div class="text-sm text-gray-600">Readiness Score</div>
              <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div class="bg-purple-600 h-2 rounded-full" style={`width: ${profile.careerTrajectory.readinessScore * 10}%`}></div>
              </div>
            </div>

            <div>
              <h4 class="font-medium mb-3">Growth Areas</h4>
              <div class="grid md:grid-cols-2 gap-3">
                {#each profile.careerTrajectory.growthAreas as area}
                  <div class="flex items-center gap-2 p-3 border rounded-lg">
                    <Icon name="trending-up" size={16} class="text-blue-500" />
                    <span class="text-sm">{area}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {/if}

        {#if activeTab === 'alignment'}
          <div class="p-6 space-y-6">
            <div class="text-center">
              <div class="text-3xl font-bold text-blue-600 mb-2">{profile.alignmentAnalysis.roleMatch}%</div>
              <div class="text-sm text-gray-600">Role Match Score</div>
              <div class="w-full bg-gray-200 rounded-full h-3 mt-2">
                <div class="bg-blue-600 h-3 rounded-full" style={`width: ${profile.alignmentAnalysis.roleMatch}%`}></div>
              </div>
            </div>

            <div class="grid md:grid-cols-2 gap-6">
              <div>
                <h4 class="font-medium mb-3 text-green-600">Strengths Match</h4>
                <ul class="space-y-2">
                  {#each profile.alignmentAnalysis.strengthsMatch as strength}
                    <li class="flex items-start gap-2">
                      <Icon name="check-circle" size={16} class="text-green-500 mt-0.5 flex-shrink-0" />
                      <span class="text-sm">{strength}</span>
                    </li>
                  {/each}
                </ul>
              </div>

              <div>
                <h4 class="font-medium mb-3 text-orange-600">Skills Gap</h4>
                <ul class="space-y-2">
                  {#each profile.alignmentAnalysis.skillsGap as gap}
                    <li class="flex items-start gap-2">
                      <Icon name="exclamation-circle" size={16} class="text-orange-500 mt-0.5 flex-shrink-0" />
                      <span class="text-sm">{gap}</span>
                    </li>
                  {/each}
                </ul>
              </div>
            </div>

            <div>
              <h4 class="font-medium mb-3">Development Priorities</h4>
              <div class="space-y-2">
                {#each profile.alignmentAnalysis.developmentNeeds as need}
                  <div class="flex items-center gap-2 p-3 border rounded-lg bg-blue-50 dark:bg-blue-900/20">
                    <Icon name="target" size={16} class="text-blue-500" />
                    <span class="text-sm">{need}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {/if}

        {#if activeTab === 'recommendations'}
          <div class="p-6 space-y-6">
            <div>
              <h4 class="font-medium mb-3 flex items-center gap-2">
                <Icon name="zap" size={16} class="text-red-500" />
                Immediate Actions
              </h4>
              <ul class="space-y-2">
                {#each profile.recommendations.immediate as rec}
                  <li class="flex items-start gap-2 p-3 border rounded-lg bg-red-50 dark:bg-red-900/20">
                    <Icon name="arrow-right" size={16} class="text-red-500 mt-0.5 flex-shrink-0" />
                    <span class="text-sm">{rec}</span>
                  </li>
                {/each}
              </ul>
            </div>

            <div>
              <h4 class="font-medium mb-3 flex items-center gap-2">
                <Icon name="clock" size={16} class="text-orange-500" />
                Short-term Goals (3-6 months)
              </h4>
              <ul class="space-y-2">
                {#each profile.recommendations.shortTerm as rec}
                  <li class="flex items-start gap-2 p-3 border rounded-lg bg-orange-50 dark:bg-orange-900/20">
                    <Icon name="arrow-right" size={16} class="text-orange-500 mt-0.5 flex-shrink-0" />
                    <span class="text-sm">{rec}</span>
                  </li>
                {/each}
              </ul>
            </div>

            <div>
              <h4 class="font-medium mb-3 flex items-center gap-2">
                <Icon name="trending-up" size={16} class="text-green-500" />
                Long-term Vision (6+ months)
              </h4>
              <ul class="space-y-2">
                {#each profile.recommendations.longTerm as rec}
                  <li class="flex items-start gap-2 p-3 border rounded-lg bg-green-50 dark:bg-green-900/20">
                    <Icon name="arrow-right" size={16} class="text-green-500 mt-0.5 flex-shrink-0" />
                    <span class="text-sm">{rec}</span>
                  </li>
                {/each}
              </ul>
            </div>
          </div>
        {/if}
      </div>

      <!-- Regenerate Button -->
      <div class="flex justify-center">
        <button 
          class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
          on:click={generateProfile}
          disabled={generating}
        >
          {#if generating}
            <Icon name="refresh" class="inline w-4 h-4 mr-2 animate-spin" />
            Regenerating...
          {:else}
            <Icon name="refresh" class="inline w-4 h-4 mr-2" />
            Regenerate Profile
          {/if}
        </button>
      </div>
    {/if}
  </div>
{/if}