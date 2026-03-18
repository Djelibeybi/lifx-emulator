<script lang="ts">
	import { devices, ui } from '$lib/stores';
	import DeviceCard from './DeviceCard.svelte';
	import Pagination from './Pagination.svelte';

	let previousCount = $state(devices.count);

	let totalPages = $derived(Math.max(1, Math.ceil(devices.count / ui.pageSize)));

	let paginatedDevices = $derived.by(() => {
		const start = (ui.currentPage - 1) * ui.pageSize;
		return devices.list.slice(start, start + ui.pageSize);
	});

	// Reset to page 1 when device count changes and current page is out of range
	$effect(() => {
		if (devices.count !== previousCount) {
			const maxPage = Math.max(1, Math.ceil(devices.count / ui.pageSize));
			if (ui.currentPage > maxPage) ui.setCurrentPage(1);
			previousCount = devices.count;
		}
	});
</script>

<div class="card">
	<h2>Devices ({devices.count})</h2>

	{#if devices.count === 0}
		<div class="no-devices">No devices emulated</div>
	{:else}
		<div class="devices-grid">
			{#each paginatedDevices as device (device.serial)}
				<DeviceCard {device} />
			{/each}
		</div>

		<Pagination {totalPages} />
	{/if}
</div>
