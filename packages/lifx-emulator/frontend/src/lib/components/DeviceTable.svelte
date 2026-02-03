<script lang="ts">
	import { devices, ui } from '$lib/stores';
	import { deleteDevice, deleteAllDevices } from '$lib/utils/api';
	import { hsbkToRgb } from '$lib/utils/color';

	let removingAll = $state(false);
	let deletingSerial = $state<string | null>(null);
	let previousCount = $state(devices.count);

	async function handleRemoveAll() {
		if (devices.count === 0) {
			alert('No devices to remove');
			return;
		}

		const msg =
			`Remove all ${devices.count} device(s) from the server?\n\n` +
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

	function getProductName(productId: number): string {
		// Common LIFX product IDs
		const products: Record<number, string> = {
			1: 'Original 1000',
			10: 'White 800 (Low Voltage)',
			11: 'White 800 (High Voltage)',
			18: 'White 900 BR30',
			20: 'Color 1000 BR30',
			22: 'Color 1000',
			27: 'LIFX A19',
			28: 'LIFX BR30',
			29: 'LIFX+ A19',
			30: 'LIFX+ BR30',
			31: 'LIFX Z',
			32: 'LIFX Z 2',
			36: 'LIFX Downlight',
			37: 'LIFX Downlight',
			38: 'LIFX Beam',
			43: 'LIFX A19',
			44: 'LIFX BR30',
			45: 'LIFX+ A19',
			46: 'LIFX+ BR30',
			49: 'LIFX Mini Color',
			50: 'LIFX Mini Day and Dusk',
			51: 'LIFX Mini White',
			52: 'LIFX GU10',
			55: 'LIFX Tile',
			57: 'LIFX Candle',
			59: 'LIFX Mini Color',
			60: 'LIFX Mini Day and Dusk',
			61: 'LIFX Mini White',
			62: 'LIFX A19',
			63: 'LIFX BR30',
			64: 'LIFX A19 Night Vision',
			65: 'LIFX BR30 Night Vision',
			68: 'LIFX Candle CA',
			70: 'LIFX Switch',
			71: 'LIFX Switch',
			81: 'LIFX Candle Warm to White',
			82: 'LIFX Filament',
			85: 'LIFX A19 HEV',
			87: 'LIFX Candle Color',
			88: 'LIFX BR30 HEV',
			89: 'LIFX A19 Clean',
			90: 'LIFX Color',
			91: 'LIFX Color',
			94: 'LIFX BR30',
			96: 'LIFX Candle White to Warm',
			97: 'LIFX A19',
			98: 'LIFX BR30',
			99: 'LIFX Clean',
			100: 'LIFX Filament Clear',
			101: 'LIFX Filament Amber',
			109: 'LIFX A19 HEV',
			110: 'LIFX BR30 HEV',
			111: 'LIFX Neon',
			112: 'LIFX Lightstrip',
			120: 'LIFX GU10'
		};
		return products[productId] || `Product ${productId}`;
	}

	// Pagination calculations
	let totalPages = $derived(Math.max(1, Math.ceil(devices.count / ui.pageSize)));

	let paginatedDevices = $derived.by(() => {
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
							<td class="cell-product">{getProductName(device.product)}</td>
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
											<div class="zone-mini" style="background: {hsbkToRgb(color)};"></div>
										{/each}
										{#if device.zone_colors.length > 16}
											<span class="more-zones">+{device.zone_colors.length - 16}</span>
										{/if}
									</div>
								{:else if device.has_color && device.color}
									<span class="color-swatch" style="background: {hsbkToRgb(device.color)};"></span>
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

		<!-- Pagination controls -->
		{#if totalPages > 1}
			<div class="pagination">
				<button class="btn btn-sm" onclick={goToPreviousPage} disabled={ui.currentPage <= 1}>
					Previous
				</button>
				<span class="page-info">
					Page {ui.currentPage} of {totalPages}
				</span>
				<button class="btn btn-sm" onclick={goToNextPage} disabled={ui.currentPage >= totalPages}>
					Next
				</button>
			</div>
		{/if}
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
		border-bottom: 1px solid var(--border-color);
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
		border: 1px solid var(--border-color);
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
