<script lang="ts">
  export let name: string;
  export let id: string;
</script>

<!-- Simple thumbnail-style preview placeholder -->
<div class="border rounded-md bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 overflow-hidden">
  <div class="h-28 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-700 flex items-center justify-center text-sm text-gray-500">
    {name}
  </div>
</div>
