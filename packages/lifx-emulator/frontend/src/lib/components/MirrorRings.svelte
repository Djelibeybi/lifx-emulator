<script lang="ts">
	import type { MirrorRings } from '$lib/utils/mirror';
	import { hsbkToCss } from '$lib/utils/color';

	let {
		rings,
		duration = 0,
		showLabels = false
	}: { rings: MirrorRings; duration?: number; showLabels?: boolean } = $props();

	const ZONE_RADIUS = 9.5;
</script>

<svg
	class="mirror-rings"
	viewBox="0 0 {rings.width} {rings.height}"
	role="img"
	aria-label="Mirror front ring ({rings.front.length} zones) inside back ring ({rings.back.length} zones)"
>
	{#each [{ name: 'back', zones: rings.back }, { name: 'front', zones: rings.front }] as ring (ring.name)}
		{#each ring.zones as z (z.zone)}
			<circle
				cx={z.x}
				cy={z.y}
				r={ZONE_RADIUS}
				class:back={ring.name === 'back'}
				style="fill: {hsbkToCss(z.color)}; transition: fill {duration}ms ease-out;"
			>
				<title>Zone {z.zone} ({ring.name})</title>
			</circle>
			{#if showLabels}
				<text x={z.x} y={z.y} class="zone-label">{z.zone}</text>
			{/if}
		{/each}
	{/each}
</svg>

<style>
	.mirror-rings {
		display: block;
		width: 100%;
		height: auto;
	}

	circle {
		stroke: var(--bg-primary);
		stroke-width: 1.5;
	}

	/* The back ring washes the wall, so it reads as a softer halo. */
	circle.back {
		stroke-dasharray: 3 2;
		stroke: var(--border-primary);
	}

	/* Dark text on a light halo stays legible on any zone colour, from
	   bright yellow to unlit black, in either theme. */
	.zone-label {
		font-family: var(--font-mono);
		font-size: 9px;
		font-weight: 600;
		fill: #111;
		text-anchor: middle;
		dominant-baseline: central;
		paint-order: stroke;
		stroke: rgba(255, 255, 255, 0.85);
		stroke-width: 2.5px;
		pointer-events: none;
	}
</style>
