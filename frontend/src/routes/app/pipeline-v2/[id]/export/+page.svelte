<script lang="ts">
  import StepFooterV2 from '$lib/components/StepFooterV2.svelte';
  import { page } from '$app/stores';
  $: id = $page.params.id;
</script>

<div class="space-y-4">
  <div class="border rounded p-4">
    <div class="text-sm text-gray-700 dark:text-gray-300">Download or copy final artifacts (placeholder).</div>
  </div>
  <StepFooterV2 current="export" pipelineId={id} />
</div>
