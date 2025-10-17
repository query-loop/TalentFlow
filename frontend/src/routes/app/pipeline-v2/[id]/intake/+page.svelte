<script lang="ts">
  import { page } from '$app/stores';
  import { getPipelineV2, patchPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import StepFooterV2 from '$lib/components/StepFooterV2.svelte';
  import Icon from '$lib/Icon.svelte';
  
  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  let loading = true;
  let jdUrl = '';
  let jdFile: File | null = null;
  let resumeFile: File | null = null;
  // autoRun removed — pipeline run will be manual
  let uploadBusy = false;
  let intakeInProgress = false;
  let intakeStatusMessage = '';
  let showAttachModal = false;
  let jdSseEventSource: EventSource | null = null;
  
  async function loadPipeline() {
    if (!id) return;
    try {
      loading = true;
      error = null;
      pipe = await getPipelineV2(id);
    } catch (e: any) {
      error = e.message || 'Failed to load pipeline';
    } finally {
      loading = false;
    }
  }
  
  $: if (id) loadPipeline();
  
  // Get intake artifacts or default values
  $: intakeData = pipe?.artifacts?.intake as { template?: string; notes?: string } || {};
  $: template = intakeData.template || 'standard';
  $: notes = intakeData.notes || '';
  
  async function saveIntakeData() {
    if (!pipe) return;
    try {
      await patchPipelineV2(pipe.id, {
        artifacts: {
          ...pipe.artifacts,
          intake: { template, notes }
        }
      });
    } catch (e: any) {
      error = e.message || 'Failed to save changes';
    }
  }

  async function handleUploadAndMaybeRun() {
    if (!pipe) return;
    uploadBusy = true; error = null; intakeInProgress = true; intakeStatusMessage = 'Uploading files...'; showAttachModal = true;
    try {
      const form = new FormData();
      if (jdUrl && jdUrl.trim()) form.append('jd_url', jdUrl.trim());
      if (jdFile) form.append('jd_file', jdFile as File, jdFile.name);
      if (resumeFile) form.append('resume_file', resumeFile as File, resumeFile.name);

      const res = await fetch(`/api/pipelines-v2/${pipe.id}/upload`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      pipe = await res.json();
      // start monitoring status: JD SSE and polling upload-status
      subscribeJdSse();
      pollUploadStatus();
      // Optionally run pipeline after upload
      // Defer automatic run until intake completes. If autoRun is checked, we'll run after parse completes.
      if (!autoRun) {
        intakeStatusMessage = 'Upload complete. Waiting for parse to finish.';
      }
    } catch (e:any) {
      error = e?.message || String(e);
      intakeInProgress = false; showAttachModal = false;
    } finally { uploadBusy = false; }
  }

  function subscribeJdSse(){
    if (!pipe) return;
    try {
      if (jdSseEventSource) {
        jdSseEventSource.close();
      }
      jdSseEventSource = new EventSource(`/api/pipelines-v2/${pipe.id}/jd/stream`);
      jdSseEventSource.addEventListener('status', (e: MessageEvent) => {
        try { const d = JSON.parse((e as any).data); intakeStatusMessage = d.message || JSON.stringify(d); } catch(err){ }
      });
      jdSseEventSource.addEventListener('ready', (e: MessageEvent) => {
        intakeStatusMessage = 'JD analysis complete';
      });
      jdSseEventSource.addEventListener('failed', (e: MessageEvent) => {
        try { const d = JSON.parse((e as any).data); intakeStatusMessage = 'JD analysis failed: ' + (d.error || 'unknown'); } catch(err){}
      });
      jdSseEventSource.addEventListener('timeout', ()=>{
        intakeStatusMessage = 'JD analysis taking longer than expected...';
      });
    } catch(e){ console.warn('SSE subscribe failed', e); }
  }

  let _pollHandle: number | null = null;
  async function pollUploadStatus(){
    if (!pipe) return;
    try {
      // poll until resume parse job completes and JD artifacts exist
      const maxAttempts = 120; // ~2 minutes
      let attempts = 0;
      while (attempts < maxAttempts) {
        attempts += 1;
        const res = await fetch(`/api/pipelines-v2/${pipe.id}/upload-status`);
        if (!res.ok) throw new Error('status fetch failed');
        const data = await res.json();
        // update pipe artifacts locally
        pipe = await getPipelineV2(pipe.id);
        // determine resume parse status
        const resumeJob = (data.jobs || {}).resume_parse;
        const jdArtifact = (data.artifacts || {}).jd;
        if (resumeJob) {
          intakeStatusMessage = `Resume parse: ${resumeJob.state || 'unknown'}`;
          if (resumeJob.state === 'SUCCESS' || resumeJob.state === 'SUCCESS') {
            intakeStatusMessage = 'Resume parse complete';
            break;
          }
          if (resumeJob.state === 'FAILURE' || resumeJob.state === 'REVOKED') {
            intakeStatusMessage = 'Resume parse failed';
            break;
          }
        }
        // if JD artifact exists and resume has text or parse job absent, consider done
        if (jdArtifact && ((pipe.artifacts && (pipe.artifacts as any).resume && ((pipe.artifacts as any).resume.text || (pipe.artifacts as any).resume.parse_job_id == null)) )) {
          intakeStatusMessage = 'Intake complete';
          break;
        }
        await new Promise((r)=> setTimeout(r, 1000));
      }
    } catch(e:any){ console.warn('poll failed', e); intakeStatusMessage = 'Intake monitoring failed'; }
    finally {
      intakeInProgress = false;
      // close SSE
      if (jdSseEventSource) { jdSseEventSource.close(); jdSseEventSource = null; }
      // run pipeline automatically if requested
      if (autoRun && pipe) {
        try { await fetch(`/api/pipelines-v2/${pipe.id}/run`, { method: 'POST' }); pipe = await getPipelineV2(pipe.id); } catch(e){ console.warn('auto run failed', e); }
      }
    }
  }

  // We no longer support manual JD paste on this page. JD editing/paste was removed.
</script>

{#if loading}
  <div class="space-y-4">
    <div class="border rounded-lg p-6">
      <div class="animate-pulse space-y-4">
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
        <div class="h-32 bg-slate-200 dark:bg-slate-700 rounded"></div>
      </div>
    </div>
  </div>
{:else if error}
  <div class="border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded-lg p-4">
    <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
      <Icon name="alert-circle" size={16} />
      <span class="font-medium">Error loading pipeline</span>
    </div>
    <p class="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
  </div>
{:else if pipe}
  <div class="space-y-6">
    <!-- Pipeline Overview -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1">
          <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Pipeline Configuration
          </h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-slate-600 dark:text-slate-400">Name:</span>
              <span class="ml-2 font-medium text-slate-900 dark:text-slate-100">{pipe.name}</span>
            </div>
            {#if pipe.company}
            <div>
              <span class="text-slate-600 dark:text-slate-400">Company:</span>
              <span class="ml-2 font-medium text-slate-900 dark:text-slate-100">{pipe.company}</span>
            </div>
            {/if}
            <div>
              <span class="text-slate-600 dark:text-slate-400">Pipeline ID:</span>
              <span class="ml-2 font-mono text-xs text-slate-700 dark:text-slate-300">{pipe.id}</span>
            </div>
            <div>
              <span class="text-slate-600 dark:text-slate-400">Created:</span>
              <span class="ml-2 text-slate-700 dark:text-slate-300">
                {new Date(pipe.createdAt).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
          <Icon name="settings" size={12} />
          Intake Setup
        </div>
      </div>
    </div>


    <!-- Job Description Link -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h3 class="text-base font-medium text-slate-900 dark:text-slate-100 mb-4">Provide JD and Resume</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="text-xs text-slate-600">Job description URL</label>
          <input bind:value={jdUrl} placeholder="https://jobs.example.com/123" class="w-full mt-1 px-3 py-2 border rounded" />
        </div>
        <div>
          <label class="text-xs text-slate-600">Or upload JD file (pdf/docx/txt)</label>
          <input type="file" on:change={(e)=> jdFile = e.target.files?.[0] || null} class="w-full mt-1" />
        </div>
        <div>
          <label class="text-xs text-slate-600">Upload resume (pdf/docx/txt)</label>
          <input type="file" on:change={(e)=> resumeFile = e.target.files?.[0] || null} class="w-full mt-1" />
        </div>
        <!-- Automatic run removed; run the pipeline from the Run page when ready -->
      </div>
      <div class="mt-4">
        <button class="btn btn-primary" on:click={handleUploadAndMaybeRun} disabled={uploadBusy || intakeInProgress}>{uploadBusy ? 'Uploading…' : (intakeInProgress ? 'Intake in progress…' : 'Upload')}</button>
      </div>
    </div>

      <!-- Intake modal showing attached files and progress -->
      {#if showAttachModal}
        <div class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40" on:click={()=>{ /* don't close on backdrop now */ }}></div>
          <div class="bg-white dark:bg-slate-800 rounded-lg p-6 max-w-xl w-full z-10">
            <h4 class="text-sm font-medium mb-2">Intake progress</h4>
            <div class="text-xs text-slate-600 dark:text-slate-300 mb-3">{intakeStatusMessage}</div>
            <div class="space-y-3">
              <div>
                <div class="text-xs text-slate-500">Job Description</div>
                {#if pipe.artifacts && (pipe.artifacts as any).jd}
                  <div class="mt-1 p-3 bg-slate-50 dark:bg-slate-700 rounded">
                    <div class="text-sm font-medium">{(pipe.artifacts as any).jd.title || (pipe.jdId || 'Uploaded JD')}</div>
                    {#if (pipe.artifacts as any).jd.minio_uri}
                      <div class="text-xs text-slate-500">Stored: {(pipe.artifacts as any).jd.minio_uri}</div>
                    {/if}
                    {#if pipe.jdId}
                      <div class="text-xs text-slate-500">Source URL: <a href={pipe.jdId} target="_blank" class="text-blue-600 hover:underline">{pipe.jdId}</a></div>
                    {/if}
                  </div>
                {:else}
                  <div class="mt-1 text-xs text-slate-500">No JD data yet</div>
                {/if}
              </div>
              <div>
                <div class="text-xs text-slate-500">Resume</div>
                {#if pipe.artifacts && (pipe.artifacts as any).resume}
                  <div class="mt-1 p-3 bg-slate-50 dark:bg-slate-700 rounded">
                    <div class="text-sm font-medium">{(pipe.artifacts as any).resume.filename || 'Attached resume'}</div>
                    {#if (pipe.artifacts as any).resume.minio_uri}
                      <div class="text-xs text-slate-500">Stored: {(pipe.artifacts as any).resume.minio_uri}</div>
                    {/if}
                    {#if (pipe.artifacts as any).resume.parse_job_id}
                      <div class="text-xs text-slate-500">Parse job: {(pipe.artifacts as any).resume.parse_job_id} ({(pipe.artifacts as any).resume.parse_job_status || 'queued'})</div>
                    {/if}
                  </div>
                {:else}
                  <div class="mt-1 text-xs text-slate-500">No resume data yet</div>
                {/if}
              </div>
              <div class="pt-2">
                <div class="h-2 bg-slate-200 rounded overflow-hidden">
                  <div class="h-2 bg-blue-500" style="width: {intakeInProgress ? '60%' : '100%'}"></div>
                </div>
              </div>
              <div class="flex justify-end mt-3">
                <button class="btn" on:click={()=>{ showAttachModal = false; }}>Close</button>
              </div>
            </div>
          </div>
        </div>
      {/if}

    <!-- JD link/card removed — uploads and JD URL are shown in the intake modal -->

    <!-- Resume filename (no parsed content). Resume itself is not shown on JD page; we only show the filename here. -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h3 class="text-base font-medium text-slate-900 dark:text-slate-100 mb-4">Resume</h3>
      {#if pipe.artifacts && (pipe.artifacts as any).resume}
        <div class="flex items-center justify-between gap-4 p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
          <div class="flex items-center gap-2">
            <Icon name="user" size={16} />
            <div class="text-sm font-medium text-slate-900 dark:text-slate-100">{(pipe.artifacts as any).resume.filename || 'Attached resume'}</div>
          </div>
          <div class="text-xs text-slate-500 dark:text-slate-400">Attached</div>
        </div>
      {:else}
        <div class="text-xs text-slate-500 dark:text-slate-400">No resume attached to this pipeline.</div>
      {/if}
    </div>

    <!-- Notes Section -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h3 class="text-base font-medium text-slate-900 dark:text-slate-100 mb-4">
        Pipeline Notes
      </h3>
      <textarea
        bind:value={notes}
        on:blur={saveIntakeData}
        placeholder="Add any notes about this pipeline, special requirements, or context..."
        class="w-full h-32 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
      ></textarea>
      <div class="mt-2 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <Icon name="info" size={12} />
        Notes are automatically saved when you click outside the text area
      </div>
    </div>
  </div>

  <StepFooterV2 current="intake" pipelineId={id} />
{/if}
