<script lang="ts">
	import type { Device, HsbkColor, TileDevice } from '$lib/types';
	import { devices, ui } from '$lib/stores';
	import { hsbkToCss, directionalGlow } from '$lib/utils/color';

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

	// Pixels per tile column (8 columns = 160px)
	const PX_PER_TILE_COL = 20;

	function getTileMaxWidth(tile: TileDevice): number {
		return tile.width * PX_PER_TILE_COL;
	}

	function getCardWidthStyle(device: Device): string {
		if (device.has_matrix && device.tile_devices && device.tile_devices.length > 0) {
			const tileWidths = device.tile_devices.reduce(
				(sum, tile) => sum + tile.width * PX_PER_TILE_COL, 0
			);
			const gaps = (device.tile_devices.length - 1) * 12;
			const padding = 42; // 20px padding + 1px border, each side
			// Use CSS custom property so the width is only applied at 768px+
			return `--card-width: ${Math.max(200, tileWidths + gaps + padding)}px;`;
		}
		return '';
	}

	function getDeviceSortKey(device: Device): number {
		if (device.has_matrix && device.tile_devices && device.tile_devices.length > 0) {
			return device.tile_devices.reduce((sum, tile) => sum + tile.width * PX_PER_TILE_COL, 0);
		}
		if (device.has_multizone) return device.zone_count;
		return 0;
	}

	// Get devices that have visual elements (color, zones, or tiles)
	let visualDevices = $derived.by(() => {
		return devices.list.filter(
			(d) =>
				(d.has_color && d.color) ||
				(d.has_multizone && d.zone_colors && d.zone_colors.length > 0) ||
				(d.has_matrix && d.tile_devices && d.tile_devices.length > 0)
		);
	});

	// Sort devices by visual width (largest first) for better flex packing
	let sortedDevices = $derived.by(() => {
		return [...visualDevices].sort((a, b) => getDeviceSortKey(b) - getDeviceSortKey(a));
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

	function getDeviceGlow(device: Device): string {
		if (device.power_level === 0) return 'none';

		if (device.has_multizone && device.zone_colors && device.zone_colors.length > 0) {
			// Horizontal strip: left/right edges from zone ends, top/bottom from all
			const zones = device.zone_colors;
			const quarter = Math.max(1, Math.floor(zones.length / 4));
			return directionalGlow({
				top: zones,
				bottom: zones,
				left: zones.slice(0, quarter),
				right: zones.slice(-quarter)
			});
		}

		if (device.has_matrix && device.tile_devices && device.tile_devices.length > 0) {
			// Matrix: extract edge pixels from all tiles combined
			const topEdge: HsbkColor[] = [];
			const bottomEdge: HsbkColor[] = [];
			const leftEdge: HsbkColor[] = [];
			const rightEdge: HsbkColor[] = [];

			for (const tile of device.tile_devices) {
				const w = tile.width;
				const h = tile.height;
				const colors = tile.colors;
				if (colors.length < w * h) continue;

				for (let x = 0; x < w; x++) {
					topEdge.push(colors[x]);                    // first row
					bottomEdge.push(colors[(h - 1) * w + x]);  // last row
				}
				for (let y = 0; y < h; y++) {
					leftEdge.push(colors[y * w]);               // first col
					rightEdge.push(colors[y * w + w - 1]);      // last col
				}
			}

			return directionalGlow({
				top: topEdge,
				right: rightEdge,
				bottom: bottomEdge,
				left: leftEdge
			});
		}

		if (device.has_color && device.color) {
			// Single bulb: same color on all edges
			const c = [device.color];
			return directionalGlow({ top: c, right: c, bottom: c, left: c });
		}

		return 'none';
	}
</script>

<div class="visualizer">
	{#if visualDevices.length === 0}
		<div class="no-devices">
			<p>No devices to visualize</p>
			<p class="hint">Add devices with color, multizone, or matrix capabilities</p>
		</div>
	{:else}
		<div class="viz-toolbar">
			<button
				class="btn btn-sm"
				class:active={ui.autoCompact}
				onclick={() => ui.toggleAutoCompact(sortedDevices.map(d => d.serial))}
			>
				{ui.autoCompact ? 'Default Layout' : 'Compact'}
			</button>
			<button class="btn btn-sm" onclick={() => ui.collapseAllViz(sortedDevices.map(d => d.serial))}>
				Collapse All
			</button>
			<button class="btn btn-sm" onclick={() => ui.expandAllViz()}>
				Expand All
			</button>
		</div>
		<div class="device-grid" class:compact={ui.autoCompact}>
			{#each sortedDevices as device (device.serial)}
				{@const duration = getTransitionDuration(device.serial)}
				{@const glow = getDeviceGlow(device)}
				{@const collapsed = ui.isVizCollapsed(device.serial)}
				<div
					class="viz-device"
					class:viz-matrix={device.has_matrix}
					class:viz-multizone={device.has_multizone && !device.has_matrix}
					class:power-off={device.power_level === 0}
					class:collapsed
					style="--device-glow: {glow}; {getCardWidthStyle(device)}"
				>
					<!-- Collapse chevron -->
					<button
						class="viz-collapse-btn"
						onclick={() => ui.toggleVizCollapsed(device.serial)}
						aria-expanded={!collapsed}
						aria-label={collapsed ? `Expand ${device.label}` : `Collapse ${device.label}`}
					>
						{collapsed ? '▸' : '▾'}
					</button>

					<!-- Header (hidden when collapsed) -->
					{#if !collapsed}
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
					{/if}

					<!-- Visualization area -->
					<div class="viz-display">
						{#if device.has_matrix && device.tile_devices && device.tile_devices.length > 0}
							<!-- Matrix/Tile display -->
							<div class="viz-tiles" class:seamless={seamlessDevices.has(device.serial)}>
								{#each device.tile_devices as tile, i}
									<div class="viz-tile-wrapper" style="max-width: {getTileMaxWidth(tile)}px;">
										{#if !collapsed && !seamlessDevices.has(device.serial) && device.tile_devices && device.tile_devices.length > 1}
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
														background: {hsbkToCss(color)};
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
											background: {hsbkToCss(color)};
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
									background: {hsbkToCss(device.color)};
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
		gap: 16px;
	}

	.viz-toolbar {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		justify-content: flex-end;
		margin-bottom: 8px;
	}

	.viz-device {
		background: var(--bg-secondary);
		border: 1px solid var(--border-primary);
		border-radius: 12px;
		padding: 20px;
		transition: opacity 0.3s ease, box-shadow 0.5s ease;
		box-shadow: var(--device-glow, none);
		position: relative;
		max-width: 100%;
	}

	.viz-device.collapsed {
		padding: 8px;
	}

	.viz-device.power-off {
		opacity: 0.4;
		box-shadow: none;
	}

	.viz-collapse-btn {
		position: absolute;
		top: 6px;
		left: 6px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-primary);
		cursor: pointer;
		color: var(--text-muted);
		font-size: 0.85em;
		padding: 2px 6px;
		border-radius: 4px;
		z-index: 1;
		opacity: 0.8;
		transition: opacity 0.15s ease, background 0.15s ease;
	}

	.viz-collapse-btn:hover {
		opacity: 1;
		background: var(--bg-tertiary);
		color: var(--text-primary);
	}

	.viz-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 10px;
		margin-left: 14px;
		gap: 12px;
	}

	.viz-info {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.viz-label {
		font-size: 0.95em;
		font-weight: 600;
		color: var(--text-primary);
	}

	.viz-serial {
		font-family: var(--font-mono);
		font-size: 0.7em;
		color: var(--text-dimmed);
	}

	.viz-meta {
		display: flex;
		gap: 6px;
		align-items: center;
		flex-wrap: wrap;
	}

	.viz-type {
		background: var(--bg-tertiary);
		padding: 1px 6px;
		border-radius: 4px;
		font-size: 0.7em;
		color: var(--accent-primary);
		font-weight: 500;
	}

	.viz-zones {
		font-size: 0.7em;
		color: var(--text-muted);
	}

	.viz-power {
		padding: 1px 6px;
		border-radius: 4px;
		font-size: 0.65em;
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
		font-size: 0.65em;
		font-weight: 500;
		background: var(--bg-tertiary);
		border: 1px solid var(--border-primary);
		cursor: pointer;
		gap: 0;
	}

	.viz-view-toggle .toggle-option {
		padding: 1px 6px;
		border-radius: 4px;
		color: var(--text-muted);
		transition: all 0.2s ease;
	}

	.viz-view-toggle .toggle-option.active {
		background: var(--accent-primary);
		color: #fff;
	}

	.viz-view-toggle:hover .toggle-option:not(.active) {
		color: var(--text-primary);
	}

	.viz-display {
		min-height: 40px;
	}

	/* Multizone strip */
	.viz-zone-strip {
		display: flex;
		height: 40px;
		border-radius: 6px;
		overflow: hidden;
	}

	.viz-zone {
		flex: 1;
		min-width: 2px;
	}

	/* Tile grid */
	.viz-tiles {
		display: flex;
		gap: 12px;
		justify-content: center;
	}

	.viz-tile-wrapper {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		flex: 1;
		min-width: 0;
		/* max-width set inline based on tile.width */
	}

	.viz-tile-label {
		font-size: 0.65em;
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
	}

	.viz-tiles.seamless .viz-tile-wrapper {
		gap: 0;
	}

	.viz-tiles.seamless .viz-tile-grid {
		border-radius: 0;
		padding: 0;
		background: transparent;
	}

	/* Single color swatch */
	.viz-color-swatch {
		width: 100%;
		height: 60px;
		border-radius: 8px;
	}

	/* Compact layout — tighter spacing for maximum density */
	.device-grid.compact {
		gap: 8px;
	}

	.device-grid.compact .viz-device.collapsed {
		padding: 4px;
	}

	.device-grid.compact .viz-collapse-btn {
		top: 2px;
		left: 2px;
		padding: 1px 4px;
		font-size: 0.75em;
	}

	/* Toolbar buttons use muted style; active compact toggle gets accent */
	.viz-toolbar :global(.btn) {
		background: var(--bg-tertiary);
		color: var(--text-muted);
		border: 1px solid var(--border-primary);
	}

	.viz-toolbar :global(.btn:hover) {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.viz-toolbar :global(.btn.active) {
		background: var(--accent-primary);
		color: #fff;
		border-color: var(--accent-primary);
	}

	/* Responsive adjustments */
	@media (min-width: 768px) {
		.device-grid {
			flex-direction: row;
			flex-wrap: wrap;
			justify-content: center;
			align-items: start;
		}

		/* Non-matrix cards flex to fill available space */
		.viz-device {
			flex: 1 1 250px;
			min-width: 200px;
			max-width: 500px;
		}

		/* Matrix cards use calculated width from CSS custom property */
		.viz-device.viz-matrix {
			flex: 0 0 auto;
			width: var(--card-width, auto);
		}

		/* Multizone cards prefer more width for zone visibility */
		.viz-device.viz-multizone {
			flex: 2 1 280px;
			max-width: none;
		}

		.viz-zone-strip {
			height: 48px;
		}

		.viz-color-swatch {
			height: 80px;
		}
	}

	@media (min-width: 1200px) {
		.viz-zone-strip {
			height: 56px;
		}
	}
</style>
