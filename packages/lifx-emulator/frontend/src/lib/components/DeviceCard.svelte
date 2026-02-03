<script lang="ts">
	import type { Device } from '$lib/types';
	import { ui } from '$lib/stores';
	import { hsbkToRgb } from '$lib/utils/color';
	import { deleteDevice } from '$lib/utils/api';

	let { device }: { device: Device } = $props();

	let deleting = $state(false);

	async function handleDelete() {
		if (!confirm(`Delete device ${device.serial}?`)) return;

		deleting = true;
		try {
			await deleteDevice(device.serial);
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to delete device');
		} finally {
			deleting = false;
		}
	}

	function formatUptime(ns: number): string {
		const seconds = Math.floor(ns / 1e9);
		return `${seconds}s`;
	}

	function getCapabilities(): string {
		const caps: string[] = [];
		if (device.has_color) caps.push('Color');
		if (device.has_infrared) caps.push('Infrared');
		if (device.has_multizone) caps.push(`Multizone (${device.zone_count} zones)`);
		if (device.has_extended_multizone) caps.push('Extended Multizone');
		if (device.has_matrix) caps.push(`Matrix (${device.tile_count} tiles)`);
		if (device.has_hev) caps.push('HEV/Clean');
		if (device.has_relays) caps.push('Relays');
		if (device.has_buttons) caps.push('Buttons');
		return caps.join(', ') || 'None';
	}

	let zonesExpanded = $derived(ui.isZonesExpanded(device.serial));
	let metadataExpanded = $derived(ui.isMetadataExpanded(device.serial));
</script>

<div class="device">
	<!-- Header -->
	<div class="device-header">
		<div>
			<div class="device-serial">{device.serial}</div>
			<div class="device-label">{device.label}</div>
		</div>
		<button class="btn btn-delete btn-sm" onclick={handleDelete} disabled={deleting}>
			{deleting ? '...' : 'Del'}
		</button>
	</div>

	<!-- Badges -->
	<div class="badges">
		<span class="badge" class:badge-power-on={device.power_level > 0} class:badge-power-off={device.power_level === 0}>
			{device.power_level > 0 ? 'ON' : 'OFF'}
		</span>
		<span class="badge badge-capability">P{device.product}</span>
		{#if device.has_color}
			<span class="badge badge-capability">color</span>
		{/if}
		{#if device.has_infrared}
			<span class="badge badge-capability">IR</span>
		{/if}
		{#if device.has_extended_multizone}
			<span class="badge badge-extended-mz">extended-mz×{device.zone_count}</span>
		{:else if device.has_multizone}
			<span class="badge badge-capability">multizone×{device.zone_count}</span>
		{/if}
		{#if device.has_matrix}
			<span class="badge badge-capability">matrix×{device.tile_count}</span>
		{/if}
		{#if device.has_hev}
			<span class="badge badge-capability">HEV</span>
		{/if}
	</div>

	<!-- Metadata toggle -->
	<button type="button" class="toggle-link" onclick={() => ui.toggleMetadataExpanded(device.serial)}>
		{metadataExpanded ? '▾' : '▸'} {metadataExpanded ? 'Hide' : 'Show'} metadata
	</button>
	{#if metadataExpanded}
		<div class="metadata-display">
			<div class="metadata-row">
				<span class="metadata-label">Firmware:</span>
				<span class="metadata-value">{device.version_major}.{device.version_minor}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">Vendor:</span>
				<span class="metadata-value">{device.vendor}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">Product:</span>
				<span class="metadata-value">{device.product}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">Capabilities:</span>
				<span class="metadata-value" style="color: var(--accent-primary);">{getCapabilities()}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">Group:</span>
				<span class="metadata-value">{device.group_label}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">Location:</span>
				<span class="metadata-value">{device.location_label}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">Uptime:</span>
				<span class="metadata-value">{formatUptime(device.uptime_ns)}</span>
			</div>
			<div class="metadata-row">
				<span class="metadata-label">WiFi Signal:</span>
				<span class="metadata-value">{device.wifi_signal.toFixed(1)} dBm</span>
			</div>
		</div>
	{/if}

	<!-- Zones/Tiles/Color display -->
	{#if device.has_multizone && device.zone_colors && device.zone_colors.length > 0}
		<button type="button" class="toggle-link" onclick={() => ui.toggleZonesExpanded(device.serial)}>
			{zonesExpanded ? '▾' : '▸'} {zonesExpanded ? 'Hide' : 'Show'} zones ({device.zone_colors.length})
		</button>
		{#if zonesExpanded}
			<div class="zone-strip">
				{#each device.zone_colors as color}
					<div class="zone-segment" style="background: {hsbkToRgb(color)};"></div>
				{/each}
			</div>
		{/if}
	{:else if device.has_matrix && device.tile_devices && device.tile_devices.length > 0}
		<button type="button" class="toggle-link" onclick={() => ui.toggleZonesExpanded(device.serial)}>
			{zonesExpanded ? '▾' : '▸'} {zonesExpanded ? 'Hide' : 'Show'} tiles ({device.tile_devices.length})
		</button>
		{#if zonesExpanded}
			<div class="tiles-container">
				{#each device.tile_devices as tile, i}
					<div class="tile-item">
						<div class="tile-label">T{i + 1}</div>
						{#if tile.colors && tile.colors.length > 0}
							<div
								class="tile-grid"
								style="grid-template-columns: repeat({tile.width || 8}, 8px);"
							>
								{#each tile.colors.slice(0, (tile.width || 8) * (tile.height || 8)) as color}
									<div class="tile-zone" style="background: {hsbkToRgb(color)};"></div>
								{/each}
							</div>
						{:else}
							<div style="color: var(--text-dimmed);">No color data</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{:else if device.has_color && device.color}
		<div style="margin-top: 4px;">
			<span class="color-swatch" style="background: {hsbkToRgb(device.color)};"></span>
			<span style="color: var(--text-muted); font-size: 0.75em;">Current color</span>
		</div>
	{/if}
</div>
