<script lang="ts">
	import type { Device, TileDevice } from '$lib/types';
	import { devices } from '$lib/stores';
	import { hsbkToRgb } from '$lib/utils/color';

	// Track which devices have seamless tile mode enabled
	let seamlessDevices = $state<Set<string>>(new Set());

	function toggleSeamless(serial: string) {
		seamlessDevices = new Set(seamlessDevices);
		if (seamlessDevices.has(serial)) {
			seamlessDevices.delete(serial);
		} else {
			seamlessDevices.add(serial);
		}
	}

	function getDeviceSpan(device: Device): number {
		if (device.has_matrix && device.tile_devices) {
			// Span equals tile count (1-5)
			return Math.min(device.tile_devices.length, 5);
		}
		if (device.has_multizone && device.zone_count > 50) return 2;
		return 1;
	}

	// Get devices that have visual elements (color, zones, or tiles)
	let visualDevices = $derived.by(() => {
		const filtered = devices.list.filter(
			(d) =>
				(d.has_color && d.color) ||
				(d.has_multizone && d.zone_colors && d.zone_colors.length > 0) ||
				(d.has_matrix && d.tile_devices && d.tile_devices.length > 0)
		);
		console.log('Visualizer devices:', devices.list.length, 'total,', filtered.length, 'visual');
		return filtered;
	});

	// Sort devices by span (largest first) for better grid packing
	let sortedDevices = $derived.by(() => {
		return [...visualDevices].sort((a, b) => getDeviceSpan(b) - getDeviceSpan(a));
	});

	function getTransitionDuration(serial: string): number {
		const transition = devices.getTransition(serial);
		if (!transition) return 0;
		// Only use transition if it's recent (within the last duration + 100ms buffer)
		const elapsed = Date.now() - transition.timestamp;
		if (elapsed > transition.duration_ms + 100) return 0;
		return transition.duration_ms;
	}

	function getDeviceType(device: Device): string {
		if (device.has_relays) return 'Switch';
		if (device.has_matrix) return 'Matrix';
		if (device.has_multizone) return 'Multizone';
		if (device.has_color) return 'Color';
		return 'Light';
	}

	function getTotalZones(device: Device): number {
		if (device.has_matrix && device.tile_devices) {
			return device.tile_devices.reduce(
				(sum, tile) => sum + tile.width * tile.height,
				0
			);
		}
		return device.zone_count;
	}
</script>

<div class="visualizer">
	{#if visualDevices.length === 0}
		<div class="no-devices">
			<p>No devices to visualize</p>
			<p class="hint">Add devices with color, multizone, or matrix capabilities</p>
		</div>
	{:else}
		<div class="device-grid">
			{#each sortedDevices as device (device.serial)}
				{@const duration = getTransitionDuration(device.serial)}
				{@const span = getDeviceSpan(device)}
				<div class="viz-device span-{span}" class:power-off={device.power_level === 0}>
					<!-- Header -->
					<div class="viz-header">
						<div class="viz-info">
							<span class="viz-label">{device.label}</span>
							<span class="viz-serial">{device.serial}</span>
						</div>
						<div class="viz-meta">
							<span class="viz-type">{getDeviceType(device)}</span>
							{#if device.has_multizone || device.has_matrix}
								<span class="viz-zones">{getTotalZones(device)} zones</span>
							{/if}
							{#if device.has_matrix && device.tile_devices && device.tile_devices.length > 1}
								<button
									class="viz-view-toggle"
									class:seamless={seamlessDevices.has(device.serial)}
									onclick={() => toggleSeamless(device.serial)}
									title={seamlessDevices.has(device.serial) ? 'Show tiles separately' : 'Show as seamless matrix'}
								>
									<span class="toggle-option" class:active={!seamlessDevices.has(device.serial)}>Tiled</span>
									<span class="toggle-option" class:active={seamlessDevices.has(device.serial)}>Seamless</span>
								</button>
							{/if}
							<span class="viz-power" class:on={device.power_level > 0}>
								{device.power_level > 0 ? 'ON' : 'OFF'}
							</span>
						</div>
					</div>

					<!-- Visualization area -->
					<div class="viz-display">
						{#if device.has_matrix && device.tile_devices && device.tile_devices.length > 0}
							<!-- Matrix/Tile display -->
							<div class="viz-tiles" class:seamless={seamlessDevices.has(device.serial)}>
								{#each device.tile_devices as tile, i}
									<div class="viz-tile-wrapper">
										{#if !seamlessDevices.has(device.serial)}
											<div class="viz-tile-label">T{i + 1}</div>
										{/if}
										<div
											class="viz-tile-grid"
											style="
												grid-template-columns: repeat({tile.width}, 1fr);
												aspect-ratio: {tile.width} / {tile.height};
											"
										>
											{#each tile.colors as color}
												<div
													class="viz-tile-zone"
													style="
														background: {hsbkToRgb(color)};
														transition: background {duration}ms ease-out;
													"
												></div>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						{:else if device.has_multizone && device.zone_colors && device.zone_colors.length > 0}
							<!-- Multizone display -->
							<div class="viz-zone-strip">
								{#each device.zone_colors as color}
									<div
										class="viz-zone"
										style="
											background: {hsbkToRgb(color)};
											transition: background {duration}ms ease-out;
										"
									></div>
								{/each}
							</div>
						{:else if device.has_color && device.color}
							<!-- Single color display -->
							<div
								class="viz-color-swatch"
								style="
									background: {hsbkToRgb(device.color)};
									transition: background {duration}ms ease-out;
								"
							></div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.visualizer {
		padding: 0;
	}

	.no-devices {
		text-align: center;
		padding: 60px 20px;
		color: var(--text-muted);
	}

	.no-devices p {
		margin: 0;
	}

	.no-devices .hint {
		font-size: 0.85em;
		color: var(--text-dimmed);
		margin-top: 8px;
	}

	.device-grid {
		display: flex;
		flex-direction: column;
		gap: 20px;
	}

	.viz-device {
		background: var(--bg-secondary);
		border: 1px solid var(--border-primary);
		border-radius: 12px;
		padding: 16px;
		transition: opacity 0.3s ease;
	}

	.viz-device.power-off {
		opacity: 0.5;
	}

	.viz-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 16px;
		gap: 16px;
	}

	.viz-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.viz-label {
		font-size: 1.1em;
		font-weight: 600;
		color: var(--text-primary);
	}

	.viz-serial {
		font-family: var(--font-mono);
		font-size: 0.8em;
		color: var(--text-dimmed);
	}

	.viz-meta {
		display: flex;
		gap: 8px;
		align-items: center;
		flex-wrap: wrap;
	}

	.viz-type {
		background: var(--bg-tertiary);
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 0.75em;
		color: var(--accent-primary);
		font-weight: 500;
	}

	.viz-zones {
		font-size: 0.75em;
		color: var(--text-muted);
	}

	.viz-power {
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 0.7em;
		font-weight: 600;
		background: #555;
		color: #aaa;
	}

	.viz-power.on {
		background: var(--accent-success);
		color: #000;
	}

	.viz-view-toggle {
		display: flex;
		padding: 2px;
		border-radius: 6px;
		font-size: 0.7em;
		font-weight: 500;
		background: var(--bg-tertiary);
		border: 1px solid var(--border-primary);
		cursor: pointer;
		gap: 0;
	}

	.viz-view-toggle .toggle-option {
		padding: 2px 8px;
		border-radius: 4px;
		color: var(--text-muted);
		transition: all 0.2s ease;
	}

	.viz-view-toggle .toggle-option.active {
		background: var(--accent-primary);
		color: #000;
	}

	.viz-view-toggle:hover .toggle-option:not(.active) {
		color: var(--text-primary);
	}

	.viz-display {
		min-height: 60px;
	}

	/* Multizone strip */
	.viz-zone-strip {
		display: flex;
		height: 48px;
		border-radius: 6px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	.viz-zone {
		flex: 1;
		min-width: 2px;
	}

	/* Tile grid */
	.viz-tiles {
		display: flex;
		gap: 16px;
		justify-content: center;
	}

	.viz-tile-wrapper {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		flex: 1;
		min-width: 0;
		max-width: 250px;
	}

	.viz-tile-label {
		font-size: 0.7em;
		color: var(--text-dimmed);
		font-weight: 500;
	}

	.viz-tile-grid {
		display: grid;
		gap: 1px;
		background: var(--bg-primary);
		padding: 2px;
		border-radius: 4px;
		width: 100%;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	.viz-tile-zone {
		aspect-ratio: 1;
		border-radius: 1px;
	}

	/* Seamless mode - tiles appear as one continuous matrix */
	.viz-tiles.seamless {
		gap: 1px;
		background: var(--bg-primary);
		border-radius: 6px;
		padding: 2px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	.viz-tiles.seamless .viz-tile-wrapper {
		gap: 0;
	}

	.viz-tiles.seamless .viz-tile-grid {
		border-radius: 0;
		padding: 0;
		box-shadow: none;
		background: transparent;
	}

	/* Single color swatch */
	.viz-color-swatch {
		width: 100%;
		height: 80px;
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	/* Responsive adjustments */
	@media (min-width: 768px) {
		.device-grid {
			display: grid;
			grid-template-columns: repeat(3, 1fr);
		}

		.viz-zone-strip {
			height: 64px;
		}

		.viz-color-swatch {
			height: 120px;
		}

		/* Tablet: 3 columns, cap spans at 3 */
		.viz-device.span-2 { grid-column: span 2; }
		.viz-device.span-3,
		.viz-device.span-4,
		.viz-device.span-5 { grid-column: span 3; }
	}

	@media (min-width: 1200px) {
		.device-grid {
			grid-template-columns: repeat(4, 1fr);
		}

		.viz-zone-strip {
			height: 80px;
		}

		/* Desktop: 4 columns, cap spans at 4 */
		.viz-device.span-3 { grid-column: span 3; }
		.viz-device.span-4,
		.viz-device.span-5 { grid-column: span 4; }
	}

	@media (min-width: 1400px) {
		.device-grid {
			grid-template-columns: repeat(5, 1fr);
		}

		/* Wide: 5 columns, full spanning */
		.viz-device.span-4 { grid-column: span 4; }
		.viz-device.span-5 { grid-column: span 5; }
	}
</style>
