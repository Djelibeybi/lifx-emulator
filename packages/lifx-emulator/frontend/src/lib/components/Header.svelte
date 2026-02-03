<script lang="ts">
	import { connection, theme } from '$lib/stores';

	const themeIcons: Record<string, string> = {
		light: '☀',
		dark: '☾',
		system: '◐'
	};
</script>

<header class="header">
	<div class="header-title">
		<h1>LIFX Emulator Monitor</h1>
		<span
			class="status-indicator"
			class:connecting={connection.status === 'connecting'}
			class:disconnected={connection.status === 'disconnected'}
			class:error={connection.status === 'error'}
			title={connection.status}
		></span>
	</div>
	<div class="header-controls">
		<button class="theme-toggle" onclick={() => theme.toggle()} title="Toggle theme ({theme.mode})">
			{themeIcons[theme.mode]}
		</button>
	</div>
</header>
<p class="subtitle">Real-time monitoring and device management</p>
