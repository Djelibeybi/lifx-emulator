<script lang="ts">
	import '../app.css';
	import { theme } from '#lib/stores/index.ts';

	let { children } = $props();

	// Apply theme changes in component context (safe for $effect)
	$effect(() => {
		theme.applyTheme();
	});
</script>

<svelte:head>
	<title>LIFX Emulator Monitor</title>
	<meta name="description" content="Real-time monitoring and device management for LIFX Emulator" />
</svelte:head>

{@render children()}
