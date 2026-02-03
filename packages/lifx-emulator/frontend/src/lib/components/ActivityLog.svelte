<script lang="ts">
	import { activity, stats } from '$lib/stores';

	let filterDirection = $state<'all' | 'rx' | 'tx'>('all');
	let filterDevice = $state<string>('');
	let filterPacket = $state<string>('');

	function formatTime(timestamp: number): string {
		return new Date(timestamp * 1000).toLocaleTimeString();
	}

	let filteredActivity = $derived(() => {
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

		return items;
	});
</script>

{#if stats.value.activity_enabled}
	<div class="card">
		<h2>Recent Activity</h2>

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

			{#if filterDirection !== 'all' || filterDevice || filterPacket}
				<button
					class="btn btn-sm"
					onclick={() => {
						filterDirection = 'all';
						filterDevice = '';
						filterPacket = '';
					}}
				>
					Clear
				</button>
			{/if}
		</div>

		<div class="activity-log">
			{#if activity.count === 0}
				<div style="color: var(--text-dimmed);">No activity yet</div>
			{:else if filteredActivity().length === 0}
				<div style="color: var(--text-dimmed);">No matching activity</div>
			{:else}
				{#each filteredActivity() as act}
					<div class="activity-item">
						<span class="activity-time">{formatTime(act.timestamp)}</span>
						<span class={act.direction === 'rx' ? 'activity-rx' : 'activity-tx'}>
							{act.direction.toUpperCase()}
						</span>
						<span class="activity-packet">{act.packet_name}</span>
						<span class="device-serial">{act.device || act.target || 'N/A'}</span>
						<span style="color: var(--text-dimmed);">{act.addr}</span>
					</div>
				{/each}
			{/if}
		</div>
	</div>
{/if}
