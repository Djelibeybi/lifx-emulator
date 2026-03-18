<script lang="ts">
	import { devices, ui, products } from '$lib/stores';
	import { deleteDevice } from '$lib/utils/api';
	import { hsbkToCss } from '$lib/utils/color';
	import Pagination from './Pagination.svelte';

	let deletingSerial = $state<string | null>(null);
	let previousCount = $state(devices.count);

	async function handleDelete(serial: string) {
		if (!confirm(`Delete device ${serial}?`)) return;

		deletingSerial = serial;
		try {
			await deleteDevice(serial);
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to delete device');
		} finally {
			deletingSerial = null;
		}
	}

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
		<div class="table-container">
			<table class="device-table">
				<thead>
					<tr>
						<th>Serial</th>
						<th>Label</th>
						<th>Product</th>
						<th>Power</th>
						<th>Color</th>
						<th>Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each paginatedDevices as device (device.serial)}
						<tr>
							<td class="cell-serial">{device.serial}</td>
							<td class="cell-label">{device.label}</td>
							<td class="cell-product">{products.getName(device.product)}</td>
							<td>
								<span
									class="power-badge"
									class:power-on={device.power_level > 0}
									class:power-off={device.power_level === 0}
								>
									{device.power_level > 0 ? 'ON' : 'OFF'}
								</span>
							</td>
							<td>
								{#if device.has_multizone && device.zone_colors && device.zone_colors.length > 0}
									<div class="zone-mini-strip">
										{#each device.zone_colors.slice(0, 16) as color}
											<div class="zone-mini" style="background: {hsbkToCss(color)};"></div>
										{/each}
										{#if device.zone_colors.length > 16}
											<span class="more-zones">+{device.zone_colors.length - 16}</span>
										{/if}
									</div>
								{:else if device.has_color && device.color}
									<span class="color-swatch" style="background: {hsbkToCss(device.color)};"></span>
								{:else}
									<span class="no-color">-</span>
								{/if}
							</td>
							<td>
								<button
									class="btn btn-delete btn-sm"
									onclick={() => handleDelete(device.serial)}
									disabled={deletingSerial === device.serial}
								>
									{deletingSerial === device.serial ? '...' : 'Del'}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<Pagination {totalPages} />
	{/if}
</div>

<style>
	.table-container {
		overflow-x: auto;
	}

	.device-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.85em;
	}

	.device-table th,
	.device-table td {
		padding: 8px 12px;
		text-align: left;
		border-bottom: 1px solid var(--border-primary);
	}

	.device-table th {
		font-weight: 600;
		color: var(--text-muted);
		font-size: 0.9em;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.device-table tbody tr:hover {
		background: var(--bg-hover);
	}

	.cell-serial {
		font-family: monospace;
		color: var(--text-primary);
	}

	.cell-label {
		font-weight: 500;
	}

	.cell-product {
		color: var(--text-muted);
		font-size: 0.9em;
	}

	.power-badge {
		display: inline-block;
		padding: 2px 8px;
		border-radius: 3px;
		font-size: 0.8em;
		font-weight: 500;
	}

	.power-on {
		background: rgba(76, 175, 80, 0.2);
		color: #4caf50;
	}

	.power-off {
		background: rgba(158, 158, 158, 0.2);
		color: var(--text-dimmed);
	}

	.color-swatch {
		display: inline-block;
		width: 24px;
		height: 24px;
		border-radius: 4px;
		border: 1px solid var(--border-primary);
		vertical-align: middle;
	}

	.zone-mini-strip {
		display: flex;
		align-items: center;
		gap: 1px;
	}

	.zone-mini {
		width: 6px;
		height: 16px;
		border-radius: 1px;
	}

	.more-zones {
		font-size: 0.75em;
		color: var(--text-dimmed);
		margin-left: 4px;
	}

	.no-color {
		color: var(--text-dimmed);
	}

	.no-devices {
		padding: 20px;
		text-align: center;
		color: var(--text-dimmed);
	}
</style>
