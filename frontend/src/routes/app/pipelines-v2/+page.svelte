<script lang="ts">
  import { listPipelinesV2, createPipelineV2, patchPipelineV2, deletePipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import { onMount } from 'svelte';
  import Icon from '$lib/Icon.svelte';
  let items: PipelineV2[] = [];
  let loading = false; let error: string | null = null;
  // no periodic polling; we fetch on demand

  // Modal state
  let showCreate = false;
  const form = { name: '', company: '', jdUrl: '', jdDoc: '' };
  
  // Resume upload state
  let resumeFile: File | null = null;
  let resumeUploading = false;
  let resumeText: string = '';
  let resumeId: string | null = null;
  // Removed sample data support
  
  function resetForm() {
    form.name = '';
    form.company = '';
    form.jdUrl = '';
    form.jdDoc = '';
    resumeFile = null;
    resumeText = '';
    resumeId = null;
    error = null;
  }
  
  function openCreateModal() {
    resetForm();
    showCreate = true;
  }

  // Edit modal state
  let showEdit = false; let editTarget: PipelineV2 | null = null;
  const editForm = { name: '', company: '', jdUrl: '', notes: '' };

  async function load(){
    try { items = await listPipelinesV2(); error = null; }
    catch(e:any){ error = e?.message || 'Failed to fetch pipelines'; }
  }
  onMount(() => { load(); });

  async function handleResumeUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    resumeFile = file;
    resumeUploading = true;
    error = null;
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/resume/parse-file', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('Failed to parse resume');
      
      const data = await response.json();
      resumeId = data.id;
      resumeText = data.text || '';
    } catch(e: any) {
      error = e?.message || 'Failed to upload resume';
      resumeFile = null;
    } finally {
      resumeUploading = false;
    }
  }
  
  async function createWithConfig(){
    if (loading) return; loading = true; error=null;
    try {
      const baseName = (form.name || '').trim() || 'Untitled v2';
      
      // Determine JD source: URL or document text
      let jdSource = form.jdUrl?.trim() || undefined;
      if (!jdSource && form.jdDoc?.trim()) {
        jdSource = 'manual:' + form.jdDoc.trim();
      }
      
      const p = await createPipelineV2({ 
        name: baseName, 
        company: form.company?.trim() || undefined, 
        jdId: jdSource,
        resumeId: resumeId || undefined
      });
      
      // Store intake data and resume as artifacts
      const artifacts: any = { 
        intake: { 
          jdSource: form.jdUrl ? 'url' : 'document'
        } 
      };
      
      if (resumeId && resumeText) {
        artifacts.resume = {
          id: resumeId,
          text: resumeText,
          filename: resumeFile?.name || 'resume',
          uploadedAt: Date.now()
        };
      }
      
      await patchPipelineV2(p.id, { artifacts });
      window.location.href = `/app/pipeline-v2/${p.id}`;
    } catch(e:any){ error = e?.message || 'Failed to create pipeline'; }
    finally { loading = false; showCreate = false; }
  }

  function openEdit(p: PipelineV2) {
    editTarget = p;
    editForm.name = p.name || '';
    editForm.company = p.company || '';
    editForm.jdUrl = p.jdId || '';
    const n = (p.artifacts && (p.artifacts as any).intake && (p.artifacts as any).intake.notes) || '';
    editForm.notes = n;
    showEdit = true; error = null;
  }

  async function removePipeline(p: PipelineV2){
    if (loading) return;
    const ok = window.confirm(`Delete pipeline "${p.name}"? This cannot be undone.`);
    if (!ok) return;
    loading = true; error=null;
    try {
      await deletePipelineV2(p.id);
      // Refresh list
      await load();
    } catch(e:any){ error = e?.message || 'Failed to delete pipeline'; }
    finally { loading = false; }
  }

  async function saveEdit(){
    if (!editTarget) return;
    if (loading) return; loading = true; error=null;
    try {
      const patch: any = {
        name: (editForm.name||'').trim() || editTarget.name,
        company: (editForm.company||'').trim() || null,
        jdId: (editForm.jdUrl||'').trim() || null,
        artifacts: { intake: { notes: editForm.notes || '' } }
      };
      const updated = await patchPipelineV2(editTarget.id, patch);
      // Update local list
      items = items.map(it => it.id === updated.id ? updated : it);
      showEdit = false; editTarget = null;
    } catch(e:any){ error = e?.message || 'Failed to save changes'; }
    finally { loading = false; }
  }

  // V2 pipeline steps definition
  const v2Steps = [
    { key: 'intake', label: 'Intake' },
    { key: 'jd', label: 'JD' },
    { key: 'profile', label: 'Profile' },
    { key: 'analysis', label: 'Analysis' },
    { key: 'ats', label: 'ATS' },
    { key: 'actions', label: 'Actions' },
    { key: 'export', label: 'Export' }
  ];
</script>

<section class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold flex items-center gap-2">Pipelines v2</h1>
    <div class="flex items-center gap-2">
      <a
        href="/app/pipeline-v2/stats"
        class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-blue-600 text-white border border-blue-700 shadow-sm hover:bg-blue-700 transition"
        title="View extraction statistics"
      >
        <Icon name="bar-chart" size={14} />
        Stats
      </a>
      <button
        on:click={() => load()}
        class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/30 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/50 dark:hover:bg-white/20 transition disabled:opacity-60"
        disabled={loading}
        title="Refresh list"
      >
        Refresh
      </button>
      <button
        on:click={openCreateModal}
        class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition disabled:opacity-60"
        disabled={loading}
      >
        New pipeline
      </button>
    </div>
  </div>

  {#if error}
    <div class="text-sm text-red-600">{error}</div>
  {/if}

  {#if loading}
    <div>Loading…</div>
  {:else if !items.length}
    <div class="text-gray-600 dark:text-gray-400">No pipelines yet.</div>
  {:else}
    <ul class="grid gap-3">
      {#each items as p}
        <li class="relative border rounded-lg p-3 bg-white/80 backdrop-blur-sm dark:bg-slate-800/70 border-slate-200 dark:border-slate-700">
          <div class="flex items-center justify-between mb-2">
            <div class="font-medium truncate">{p.name}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{new Date(p.createdAt).toLocaleString()}</div>
          </div>
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 flex-1 flex-nowrap overflow-x-auto whitespace-nowrap pr-1">
              {#each v2Steps as s, i}
                {@const st = (p.statuses && (p.statuses as any)[s.key]) || 'pending'}
                <div class={`whitespace-nowrap inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border text-xs ${st === 'complete' ? 'border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300 bg-emerald-50/40 dark:bg-emerald-900/20' : st === 'active' ? 'border-indigo-300 text-indigo-700 dark:border-indigo-700 dark:text-indigo-300 bg-indigo-50/40 dark:bg-indigo-900/20' : 'border-slate-200 text-gray-700 dark:border-slate-700 dark:text-gray-200'}`}>
                  <span class={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] ${st === 'complete' ? 'bg-emerald-600 text-white' : st === 'active' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300'}`}>{i+1}</span>
                  <span class="font-medium">{s.label}</span>
                </div>
                {#if i < v2Steps.length - 1}
                  <span class="text-gray-400 dark:text-gray-500"><Icon name="arrow-right" size={14}/></span>
                {/if}
              {/each}
            </div>
            <div class="flex items-center gap-3">
              {#if p.jdId && /^https?:\/\//.test(p.jdId)}
                <a
                  href={p.jdId}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center text-xs text-blue-600 hover:underline gap-1"
                  title="Open JD link"
                >
                  <Icon name="external-link" size={14} /> JD
                </a>
              {/if}
              <a
                href={`/app/pipeline-v2/${p.id}`}
                class="inline-flex items-center text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition"
              >View</a>
              <button
                class="inline-flex items-center justify-center w-8 h-8 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-white/60 dark:hover:bg-white/20"
                on:click={() => openEdit(p)}
                title="Edit"
              >
                <Icon name="edit" size={16} />
              </button>
              <button
                class="inline-flex items-center justify-center w-8 h-8 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 hover:bg-white/60 dark:hover:bg-white/20 disabled:opacity-50"
                on:click={() => removePipeline(p)}
                title="Delete"
                disabled={loading}
              >
                <Icon name="trash" size={16} />
              </button>
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
  {#if showCreate}
    <!-- Modal overlay -->
    <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40" on:click={() => { showCreate=false; resetForm(); }}></div>
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="w-full max-w-4xl my-8 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-2xl" on:click|stopPropagation>
        <!-- Header -->
        <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-800 rounded-t-xl">
          <div>
            <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Create New Pipeline</h2>
            <p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">Set up your resume and job description analysis</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition" on:click={() => { showCreate=false; resetForm(); }}>
            <Icon name="x" size={20} />
          </button>
        </div>
        
        <!-- Content - Two Column Layout -->
        <div class="p-6 max-h-[calc(100vh-16rem)] overflow-y-auto">
          {#if error}
            <div class="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
              <Icon name="alert-circle" size={16} />
              {error}
            </div>
          {/if}
          
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Left Column: Basic Info -->
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <Icon name="info" size={16} />
                  Pipeline Information
                </h3>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Pipeline Name *</span>
                    <input 
                      class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" 
                      bind:value={form.name} 
                      placeholder="e.g., Senior Backend Engineer at TechCorp" 
                    />
                  </label>
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Company Name</span>
                    <input 
                      class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" 
                      bind:value={form.company} 
                      placeholder="e.g., TechCorp Inc." 
                    />
                  </label>
                </div>
              </div>
              
              <!-- Resume Upload -->
              <div>
                <h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <Icon name="file-text" size={16} />
                  Resume Upload
                </h3>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Upload Resume (PDF or DOCX)</span>
                    <div class="relative">
                      <input 
                        type="file" 
                        accept=".pdf,.docx,.doc" 
                        class="w-full text-sm border border-slate-300 dark:border-slate-600 rounded-lg cursor-pointer
                               file:mr-4 file:py-2 file:px-4 file:rounded-l-lg file:border-0 
                               file:text-sm file:font-medium file:cursor-pointer
                               file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 
                               dark:file:bg-blue-900/30 dark:file:text-blue-300 dark:hover:file:bg-blue-900/50
                               bg-white dark:bg-slate-800 transition" 
                        on:change={handleResumeUpload}
                        disabled={resumeUploading}
                      />
                    </div>
                  </label>
                  
                  {#if resumeUploading}
                    <div class="text-xs text-blue-600 dark:text-blue-400 flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <svg class="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
                      <span>Uploading and parsing resume...</span>
                    </div>
                  {/if}
                  
                  {#if resumeFile && resumeId}
                    <div class="text-xs text-green-600 dark:text-green-400 flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                      <Icon name="check-circle" size={14} />
                      <span class="font-medium">{resumeFile.name}</span>
                      <span class="text-green-500 dark:text-green-500">• Uploaded successfully</span>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
            
            <!-- Right Column: JD Source -->
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <Icon name="briefcase" size={16} />
                  Job Description Source
                </h3>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">JD URL (Optional)</span>
                    <input 
                      class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" 
                      bind:value={form.jdUrl} 
                      placeholder="https://jobs.lever.co/company/job-id" 
                    />
                  </label>
                  {#if form.jdUrl?.trim()}
                  <div class="text-xs mt-1">
                    <a class="inline-flex items-center gap-1 text-blue-600 hover:underline" href={form.jdUrl} target="_blank" rel="noopener noreferrer">
                      <Icon name="external-link" size={12} /> Open JD link
                    </a>
                  </div>
                  {/if}
                  
                  <div class="relative">
                    <div class="absolute inset-0 flex items-center">
                      <div class="w-full border-t border-slate-300 dark:border-slate-600"></div>
                    </div>
                    <div class="relative flex justify-center text-xs">
                      <span class="px-2 bg-white dark:bg-slate-900 text-slate-500">OR</span>
                    </div>
                  </div>
                  
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Paste JD Text</span>
                    <textarea 
                      class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition font-mono"
                      bind:value={form.jdDoc} 
                      placeholder="Paste the job description here..."
                      rows="12"
                      disabled={!!form.jdUrl?.trim()}
                    ></textarea>
                  </label>
                  
                  {#if form.jdUrl?.trim()}
                    <div class="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                      <Icon name="info" size={12} />
                      <span>URL takes precedence over pasted text</span>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
          
          
        </div>
        
        <!-- Footer -->
        <div class="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50 rounded-b-xl">
          <div class="text-xs text-slate-500 dark:text-slate-400">
            {#if resumeFile && (form.jdUrl?.trim() || form.jdDoc?.trim())}
              <span class="text-green-600 dark:text-green-400 flex items-center gap-1">
                <Icon name="check-circle" size={14} />
                Ready to create
              </span>
            {:else}
              <span>Upload resume and provide JD to continue</span>
            {/if}
          </div>
          <div class="flex items-center gap-3">
            <button 
              class="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition" 
              on:click={() => { showCreate=false; resetForm(); }}
            >
              Cancel
            </button>
            <button 
              class="px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg shadow-blue-500/30 flex items-center gap-2" 
              disabled={loading || !resumeFile || (!form.jdUrl?.trim() && !form.jdDoc?.trim())} 
              on:click={createWithConfig}
            >
              {#if loading}
                <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
                Creating...
              {:else}
                <Icon name="play" size={16} />
                Create Pipeline
              {/if}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if showEdit && editTarget}
    <!-- Edit modal overlay -->
    <div class="fixed inset-0 bg-black/40 z-40" on:click={() => { showEdit=false; editTarget=null; }}></div>
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="w-full max-w-lg rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg" on:click|stopPropagation>
        <div class="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="font-medium">Edit pipeline</div>
          <button class="text-sm text-gray-500" on:click={() => { showEdit=false; editTarget=null; }}>✕</button>
        </div>
        <div class="p-4 space-y-3">
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Name</span>
            <input class="w-full border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.name} />
          </label>
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Company</span>
            <input class="w-full border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.company} />
          </label>
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">JD URL or ID</span>
            <input class="w-full border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.jdUrl} />
          </label>
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Notes</span>
            <textarea class="w-full border rounded px-2 py-1.5 min-h-24 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.notes} placeholder="Optional notes for this pipeline..."></textarea>
          </label>
        </div>
        <div class="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center gap-2 justify-end">
          <button class="px-3 py-1.5 rounded border" on:click={() => { showEdit=false; editTarget=null; }}>Cancel</button>
          <button class="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50" disabled={loading} on:click={saveEdit}>{loading? 'Saving…' : 'Save changes'}</button>
        </div>
      </div>
    </div>
  {/if}
</section>
