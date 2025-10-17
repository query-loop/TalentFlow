<script lang="ts">
  export let name:
    | 'home'
    | 'sparkles'
    | 'shield-check'
    | 'tag'
    | 'palette'
    | 'folder'
    | 'layers'
    | 'clock'
    | 'gear'
    | 'info'
    | 'plug'
    | 'upload'
    | 'download'
    | 'building'
    | 'check'
    | 'arrow-right'
    | 'arrow-left'
    | 'plus'
    | 'eye'
    | 'search'
    | 'trash'
    | 'pencil'
    | 'map-pin'
    | 'link'
    | 'file-text'
    | 'external-link'
  | 'spinner'
  | 'chevrons-right-left'
  | 'x'
  | 'alert-circle'
  | 'edit'
  | 'file-plus'
  | 'settings'
  | 'arrow-up-right'
  | 'map' = 'home';
  export let size = 18;
  const paths: Record<string, string> = {
    home: 'M3 9.75 10 3l7 6.75V18a1 1 0 0 1-1 1h-4.5v-5h-3v5H4a1 1 0 0 1-1-1V9.75Z',
    sparkles: 'M6 2.5 7.5 6 11 7.5 7.5 9 6 12.5 4.5 9 1 7.5 4.5 6 6 2.5Zm10 1 1 2.5 2.5 1-2.5 1L16 10.5l-1-2.5-2.5-1 2.5-1L16 3.5Zm-2 7 1.5 3.5 3.5 1.5-3.5 1.5L14 20.5l-1.5-3.5L9 17.5l3.5-1.5L14 10.5Z',
    'shield-check': 'M12 2 4 5v6c0 5 4 8 8 9 4-1 8-4 8-9V5l-8-3Zm3.3 6.7-4.6 4.6-2-2L7 12l3.7 3.7L17 9.4l-1.7-1.7Z',
    tag: 'M2 10V4h6l10 10-6 6L2 10Zm5-4.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z',
    palette: 'M12 3c-5 0-9 3.6-9 8s3 7 6 7h1.5a1.5 1.5 0 0 0 0-3H10a2 2 0 1 1 0-4h2a2 2 0 0 0 2-2c0-3.3 2.7-3 3-3 1.7 0 3 1.3 3 3 0 4.4-4 9-8 9-6 0-10-4.5-10-10S6 1 12 1V3Z',
    folder: 'M3 5h6l2 2h10v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z',
    layers: 'M12 2 2 7l10 5 10-5-10-5Zm0 9L2 6v3l10 5 10-5V6l-10 5Zm0 4L2 10v3l10 5 10-5v-3l-10 5Z',
    clock: 'M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2Zm1 5h-2v6l5 3 1-1.732-4-2.268V7Z',
    gear: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm9 4-2.1-.7.3-2.2-2-1.1-1.3 1.8-2.1-.7-.7-2.1H9.9L9.2 9.1l-2.1.7-1.3-1.8-2 1.1.3 2.2L2 12l.7 2.1-2 .7 1.1 2 2.2-.3.7 2.1 2 1.1 1.3-1.8 2.1.7.7 2.1h2.2l.7-2.1 2.1-.7 1.3 1.8 2-1.1-.3-2.2 2.1-.7V12Z',
    info: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 5h-2v2h2V7Zm0 4h-2v6h2v-6Z',
    plug: 'M7 2v6l-2 2v2h6v6h2l2-2v-4h4l2-2-6-6-2 2V2H7Z',
    upload: 'M12 2 7 7h3v6h4V7h3l-5-5Zm-8 18v-2h16v2H4Z',
    building: 'M4 3h16v18H4V3Zm4 2v2h2V5H8Zm0 4v2h2V9H8Zm0 4v2h2v-2H8Zm0 4v2h8v-2H8Zm4-12v2h2V5h-2Zm0 4v2h2V9h-2Zm0 4v2h2v-2h-2Z',
    check: 'M20.285 6.708 9 18l-5.285-5.292 1.414-1.414L9 15.172l9.871-9.878 1.414 1.414Z',
    'arrow-right': 'M4 12h12l-4-4 1.414-1.414L20.828 12l-7.414 7.414L12 18l4-4H4v-2Z',
    'arrow-left': 'M20 11v2H8l4 4-1.414 1.414L3.172 12l7.414-7.414L12 6l-4 4h12z',
    plus: 'M11 4h2v6h6v2h-6v6h-2v-6H5v-2h6V4Z',
    eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10 4a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
    search: 'M10 2a8 8 0 1 0 4.9 14.32l4.39 4.39 1.42-1.42-4.39-4.39A8 8 0 0 0 10 2Zm0 2a6 6 0 1 1 0 12A6 6 0 0 1 10 4Z',
    download: 'M12 3v10.586l3.293-3.293 1.414 1.414L12 17.414l-4.707-4.707 1.414-1.414L12 13.586V3h0ZM5 19h14v2H5v-2Z',
    trash: 'M7 9v10a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9H7Zm11-4h-3.5l-1-1h-3l-1 1H6v2h12V5Z',
    pencil: 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm18.71-11.04a1.003 1.003 0 0 0 0-1.42l-2.5-2.5a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.99-1.66Z',
    'map-pin': 'M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7Zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z',
    link: 'M7 12a5 5 0 0 1 5-5h3v2h-3a3 3 0 1 0 0 6h3v2h-3a5 5 0 0 1-5-5Zm6-3h3a5 5 0 1 1 0 10h-3v-2h3a3 3 0 1 0 0-6h-3V9Z',
    'file-text': 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6ZM8 12h8v2H8v-2Zm0 4h8v2H8v-2Zm6-10v4h4',
    'external-link': 'M14 3h7v7h-2V6.414l-8.293 8.293-1.414-1.414L17.586 5H14V3ZM5 5h6v2H7v10h10v-4h2v6H5V5Z',
    spinner: 'M12 2a10 10 0 1 0 10 10h-2A8 8 0 1 1 12 4V2Z',
    'chevrons-right-left': 'M7 8l-3 4 3 4v-3h10v3l3-4-3-4v3H7V8Z',
    x: 'M5 5l14 14M19 5L5 19',
    'alert-circle': 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-1 5h2v7h-2V7Zm0 9h2v2h-2v-2Z',
    edit: 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm18.71-11.04a1.003 1.003 0 0 0 0-1.42l-2.5-2.5a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.99-1.66Z',
    'file-plus': 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6ZM8 12h4v-2h2v2h2v2h-2v2h-2v-2H8v-2Zm6-7v4h4',
    settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm9 4-2.1-.7.3-2.2-2-1.1-1.3 1.8-2.1-.7-.7-2.1H9.9L9.2 9.1l-2.1.7-1.3-1.8-2 1.1.3 2.2L2 12l.7 2.1-2 .7 1.1 2 2.2-.3.7 2.1 2 1.1 1.3-1.8 2.1.7.7 2.1h2.2l.7-2.1 2.1-.7 1.3 1.8 2-1.1-.3-2.2 2.1-.7V12Z',
    'arrow-up-right': 'M7 17 15 9v5h2V7h-7v2h5l-8 8Z',
    // alias simple map to existing map-pin for compatibility
    map: 'M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7Zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z'
  };
  const path = paths[name] || paths['info'];
</script>

<svg {...$$restProps} width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
  <path d={paths[name] || path}></path>
  <slot />
</svg>
