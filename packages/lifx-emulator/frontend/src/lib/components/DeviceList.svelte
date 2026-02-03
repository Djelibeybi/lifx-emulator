<script lang="ts">
	import { devices, ui } from '$lib/stores';
	import { deleteAllDevices } from '$lib/utils/api';
	import DeviceCard from './DeviceCard.svelte';

	let removingAll = $state(false);
	let previousCount = $state(devices.count);

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

	// Pagination calculations
	let totalPages = $derived(Math.max(1, Math.ceil(devices.count / ui.pageSize)));

	let paginatedDevices = $derived(() => {
		const start = (ui.currentPage - 1) * ui.pageSize;
		const end = start + ui.pageSize;
		return devices.list.slice(start, end);
	});

	function goToPreviousPage() {
		if (ui.currentPage > 1) {
			ui.setCurrentPage(ui.currentPage - 1);
		}
	}

	function goToNextPage() {
		if (ui.currentPage < totalPages) {
			ui.setCurrentPage(ui.currentPage + 1);
		}
	}

	// Reset to page 1 when device count changes significantly
	$effect(() => {
		const countDiff = Math.abs(devices.count - previousCount);
		if (countDiff > 0) {
			// If current page would be beyond available pages, reset
			const maxPage = Math.max(1, Math.ceil(devices.count / ui.pageSize));
			if (ui.currentPage > maxPage) {
				ui.setCurrentPage(1);
			}
			previousCount = devices.count;
		}
	});
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
			{#each paginatedDevices() as device (device.serial)}
				<DeviceCard {device} />
			{/each}
		</div>

		<!-- Pagination controls -->
		{#if totalPages > 1}
			<div class="pagination">
				<button
					class="btn btn-sm"
					onclick={goToPreviousPage}
					disabled={ui.currentPage <= 1}
				>
					Previous
				</button>
				<span class="page-info">
					Page {ui.currentPage} of {totalPages}
				</span>
				<button
					class="btn btn-sm"
					onclick={goToNextPage}
					disabled={ui.currentPage >= totalPages}
				>
					Next
				</button>
			</div>
		{/if}
	{/if}
</div>

<style>
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 16px;
		margin-top: 16px;
		padding-top: 12px;
		border-top: 1px solid var(--border-color);
	}

	.page-info {
		font-size: 0.9em;
		color: var(--text-muted);
	}
</style>
