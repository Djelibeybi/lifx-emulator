<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { connection, ui, devices, activity } from '$lib/stores';
	import type { ActiveTab } from '$lib/types';
	import {
		Header,
		StatsBar,
		DeviceToolbar,
		DeviceList,
		DeviceTable,
		ActivityLog,
		ScenarioPanel
	} from '$lib/components';

	const tabs: { id: ActiveTab; label: string }[] = [
		{ id: 'devices', label: 'Devices' },
		{ id: 'activity', label: 'Activity' },
		{ id: 'scenarios', label: 'Scenarios' }
	];

	onMount(() => {
		connection.connect();
	});

	onDestroy(() => {
		connection.disconnect();
	});
</script>

<div class="container">
	<Header />

	{#if ui.showStats}
		<StatsBar />
	{/if}

	<!-- Tab navigation -->
	<div class="tabs">
		{#each tabs as tab}
			<button
				class="tab"
				class:active={ui.activeTab === tab.id}
				onclick={() => ui.setActiveTab(tab.id)}
			>
				{tab.label}
				{#if tab.id === 'devices'}
					<span class="tab-count">{devices.count}</span>
				{:else if tab.id === 'activity'}
					<span class="tab-count">{activity.count}</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Tab content -->
	<div class="tab-content">
		{#if ui.activeTab === 'devices'}
			<DeviceToolbar />
			{#if ui.viewMode === 'table'}
				<DeviceTable />
			{:else}
				<DeviceList />
			{/if}
		{:else if ui.activeTab === 'activity'}
			<ActivityLog />
		{:else if ui.activeTab === 'scenarios'}
			<ScenarioPanel />
		{/if}
	</div>
</div>

<style>
	.tabs {
		display: flex;
		gap: 4px;
		margin-bottom: 16px;
		border-bottom: 2px solid var(--border-color);
		padding-bottom: 0;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 20px;
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		cursor: pointer;
		font-size: 0.95em;
		font-weight: 500;
		color: var(--text-muted);
		transition: all 0.15s ease;
	}

	.tab:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.tab.active {
		color: var(--accent-primary);
		border-bottom-color: var(--accent-primary);
	}

	.tab-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 20px;
		height: 20px;
		padding: 0 6px;
		background: var(--bg-secondary);
		border-radius: 10px;
		font-size: 0.8em;
		font-weight: 600;
		color: var(--text-muted);
	}

	.tab.active .tab-count {
		background: var(--accent-primary);
		color: white;
	}

	.tab-content {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
</style>
