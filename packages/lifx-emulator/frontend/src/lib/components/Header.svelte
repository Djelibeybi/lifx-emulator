<script lang="ts">
	import { connection, theme, ui } from '$lib/stores';

	const themeIcons: Record<string, string> = {
		light: '☀',
		dark: '☾',
		system: '◐'
	};
</script>

<header class="header">
	<div class="header-title">
		<h1>LIFX Emulator</h1>
		<span
			class="status-indicator"
			class:connecting={connection.status === 'connecting'}
			class:disconnected={connection.status === 'disconnected'}
			class:error={connection.status === 'error'}
			title={connection.status}
		></span>
		{#if connection.status !== 'connected'}
			<span class="status-text">{connection.status}</span>
		{/if}
	</div>
	<div class="header-controls">
		<button
			class="control-btn"
			class:active={ui.showStats}
			onclick={() => ui.toggleShowStats()}
			title={ui.showStats ? 'Hide statistics' : 'Show statistics'}
		>
			<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
				<rect x="1" y="9" width="3" height="6" rx="0.5" />
				<rect x="6" y="5" width="3" height="10" rx="0.5" />
				<rect x="11" y="1" width="3" height="14" rx="0.5" />
			</svg>
		</button>
		<button class="control-btn" onclick={() => theme.toggle()} title={`Toggle theme (${theme.mode})`}>
			{themeIcons[theme.mode]}
		</button>
	</div>
</header>

<style>
	.header-title h1 {
		font-size: 1.3em;
		margin: 0;
	}

	.status-text {
		font-size: 0.75em;
		color: var(--text-dimmed);
		text-transform: capitalize;
	}

	.header-controls {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.control-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-primary);
		border-radius: 6px;
		cursor: pointer;
		font-size: 1em;
		color: var(--text-muted);
		transition: all 0.15s ease;
	}

	.control-btn:hover {
		border-color: var(--accent-primary);
		color: var(--text-primary);
	}

	.control-btn.active {
		background: var(--accent-primary);
		border-color: var(--accent-primary);
		color: white;
	}
</style>
