<script lang="ts">
	import { activity, stats } from '#lib/stores/index.ts';

	import type { ActivityEvent } from '#lib/types.ts';

	/** Number of payload bytes shown inline before the hex is truncated. */
	const HEX_PREVIEW_BYTES = 16;

	let filterDirection = $state<'all' | 'rx' | 'tx'>('all');
	let filterDevice = $state<string>('');
	let filterPacket = $state<string>('');
	let filterUndecodable = $state<boolean>(false);
	let expanded = $state<Record<string, boolean>>({});

	function formatTime(timestamp: number): string {
		return new Date(timestamp * 1000).toLocaleTimeString();
	}

	function isUndecodable(act: ActivityEvent): boolean {
		return act.payload_hex !== undefined && act.decode_error !== undefined;
	}

	function truncateHex(hex: string): string {
		const limit = HEX_PREVIEW_BYTES * 2;
		return hex.length > limit ? `${hex.slice(0, limit)}…` : hex;
	}

	function eventKey(act: ActivityEvent): string {
		return `${act.timestamp}:${act.direction}:${act.packet_type}:${act.addr}`;
	}

	function toggleExpanded(act: ActivityEvent) {
		const key = eventKey(act);
		expanded = { ...expanded, [key]: !expanded[key] };
	}

	function clearFilters() {
		filterDirection = 'all';
		filterDevice = '';
		filterPacket = '';
		filterUndecodable = false;
	}

	let filteredActivity = $derived.by(() => {
		let items = activity.reversed;

		if (filterDirection !== 'all') {
			items = items.filter((act) => act.direction === filterDirection);
		}

		if (filterDevice) {
			const deviceLower = filterDevice.toLowerCase();
			items = items.filter(
				(act) =>
					act.device?.toLowerCase().includes(deviceLower) ||
					act.target?.toLowerCase().includes(deviceLower)
			);
		}

		if (filterPacket) {
			const packetLower = filterPacket.toLowerCase();
			items = items.filter((act) => act.packet_name.toLowerCase().includes(packetLower));
		}

		if (filterUndecodable) {
			items = items.filter(isUndecodable);
		}

		return items;
	});
</script>

<div class="card">
	<h2>Recent Activity</h2>

	{#if !stats.value.activity_enabled}
		<div class="activity-disabled">
			<p>Activity logging is disabled.</p>
			<p class="hint">Start the emulator with <code>--api-activity</code> to enable packet logging.</p>
		</div>
	{:else}
		<!-- Filters -->
		<div class="activity-filters">
			<div class="filter-group">
				<label for="filter-direction">Direction:</label>
				<select id="filter-direction" bind:value={filterDirection}>
					<option value="all">All</option>
					<option value="rx">RX</option>
					<option value="tx">TX</option>
				</select>
			</div>

			<div class="filter-group">
				<label for="filter-device">Device/Target:</label>
				<input
					id="filter-device"
					type="text"
					placeholder="Filter by device..."
					bind:value={filterDevice}
				/>
			</div>

			<div class="filter-group">
				<label for="filter-packet">Packet:</label>
				<input
					id="filter-packet"
					type="text"
					placeholder="Filter by packet..."
					bind:value={filterPacket}
				/>
			</div>

			<div class="filter-group">
				<label class="checkbox-label" for="filter-undecodable">
					<input id="filter-undecodable" type="checkbox" bind:checked={filterUndecodable} />
					Undecodable only
				</label>
			</div>

			{#if filterDirection !== 'all' || filterDevice || filterPacket || filterUndecodable}
				<button class="btn btn-sm" onclick={clearFilters}>Clear</button>
			{/if}
		</div>

		<div class="activity-log">
			{#if activity.count === 0}
				<div style="color: var(--text-dimmed);">No activity yet</div>
			{:else if filteredActivity.length === 0}
				<div style="color: var(--text-dimmed);">No matching activity</div>
			{:else}
				{#each filteredActivity as act}
					<div class="activity-item" class:activity-undecodable={isUndecodable(act)}>
						<span class="activity-time">{formatTime(act.timestamp)}</span>
						<span class={act.direction === 'rx' ? 'activity-rx' : 'activity-tx'}>
							{act.direction.toUpperCase()}
						</span>
						<span class="activity-packet">{act.packet_name}</span>
						<span class="device-serial">{act.device || act.target || 'N/A'}</span>
						<span style="color: var(--text-dimmed);">{act.addr}</span>
						{#if act.payload_hex !== undefined && act.decode_error !== undefined}
							<button
								type="button"
								class="activity-hex"
								title={`${act.decode_error}\n${act.payload_hex || '(empty payload)'}`}
								aria-expanded={expanded[eventKey(act)] ?? false}
								onclick={() => toggleExpanded(act)}
							>
								<span class="activity-reason">{act.decode_error}</span>
								<code>{act.payload_hex ? truncateHex(act.payload_hex) : '(empty)'}</code>
							</button>
						{/if}
					</div>
					{#if isUndecodable(act) && expanded[eventKey(act)]}
						<div class="activity-hex-full">
							<span class="activity-reason">{act.decode_error}</span>
							<code>{act.payload_hex || '(empty payload)'}</code>
						</div>
					{/if}
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
		color: var(--text-muted);
		font-size: 0.85em;
		padding: 6px 0;
	}

	/* The shared .filter-group input rule sets a 150px min-width for text
	   inputs; the checkbox must stay at its natural size. */
	.checkbox-label input[type='checkbox'] {
		min-width: 0;
		width: 16px;
		height: 16px;
		margin: 0;
	}

	.activity-item.activity-undecodable {
		flex-wrap: wrap;
	}

	.activity-hex {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: none;
		border: 1px dashed var(--border-primary);
		border-radius: 4px;
		padding: 0 6px;
		color: var(--text-secondary);
		font: inherit;
		cursor: pointer;
	}

	.activity-hex:hover {
		border-color: var(--accent-primary);
	}

	.activity-hex code,
	.activity-hex-full code {
		font-family: var(--font-mono);
	}

	.activity-reason {
		color: var(--accent-danger-hover);
		font-size: 0.9em;
	}

	.activity-hex-full {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 4px 0 8px 90px;
		border-bottom: 1px solid var(--bg-secondary);
	}

	.activity-hex-full code {
		word-break: break-all;
		white-space: pre-wrap;
		color: var(--text-secondary);
	}

	.activity-disabled {
		padding: 20px;
		text-align: center;
		color: var(--text-muted);
	}

	.activity-disabled p {
		margin: 8px 0;
	}

	.activity-disabled .hint {
		font-size: 0.85em;
		color: var(--text-dimmed);
	}

	.activity-disabled code {
		background: var(--bg-secondary);
		padding: 2px 6px;
		border-radius: 3px;
		font-family: monospace;
	}
</style>
