<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  $: id = $page.params.id;
  onMount(() => { if (id) goto(`/app/pipeline-v2/${id}/jd`, { replaceState: true }); });
</script>

<div class="p-6 text-sm text-gray-600 dark:text-gray-300">Redirecting to JD…</div>
