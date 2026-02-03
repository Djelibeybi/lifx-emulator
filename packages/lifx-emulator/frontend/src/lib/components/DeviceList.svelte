<script lang="ts">
	import { devices } from '$lib/stores';
	import { deleteAllDevices } from '$lib/utils/api';
	import DeviceCard from './DeviceCard.svelte';

	let removingAll = $state(false);

	async function handleRemoveAll() {
		if (devices.count === 0) {
			alert('No devices to remove');
			return;
		}

		const msg = `Remove all ${devices.count} device(s) from the server?\n\n` +
			'This will stop all devices from responding to LIFX protocol packets, ' +
			'but will not delete persistent storage.';
		if (!confirm(msg)) return;

		removingAll = true;
		try {
			const result = await deleteAllDevices();
			alert(result.message);
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to remove devices');
		} finally {
			removingAll = false;
		}
	}
</script>

<div class="card">
	<h2 style="display: flex; justify-content: space-between; align-items: center;">
		<span>Devices ({devices.count})</span>
		<button
			class="btn btn-delete"
			onclick={handleRemoveAll}
			disabled={removingAll || devices.count === 0}
			title="Remove all devices from server (runtime only)"
		>
			{removingAll ? 'Removing...' : 'Remove All'}
		</button>
	</h2>

	{#if devices.count === 0}
		<div class="no-devices">No devices emulated</div>
	{:else}
		<div class="devices-grid">
			{#each devices.list as device (device.serial)}
				<DeviceCard {device} />
			{/each}
		</div>
	{/if}
</div>
