import type { HsbkColor } from '$lib/types';

/**
 * Convert LIFX HSBK color to CSS RGB string.
 * HSBK values are 16-bit (0-65535) for hue, saturation, brightness.
 * Kelvin is ignored for RGB conversion (used for white temperature).
 */
export function hsbkToRgb(hsbk: HsbkColor): string {
	const h = hsbk.hue / 65535;
	const s = hsbk.saturation / 65535;
	const v = hsbk.brightness / 65535;

	let r: number, g: number, b: number;

	const i = Math.floor(h * 6);
	const f = h * 6 - i;
	const p = v * (1 - s);
	const q = v * (1 - f * s);
	const t = v * (1 - (1 - f) * s);

	switch (i % 6) {
		case 0:
			r = v;
			g = t;
			b = p;
			break;
		case 1:
			r = q;
			g = v;
			b = p;
			break;
		case 2:
			r = p;
			g = v;
			b = t;
			break;
		case 3:
			r = p;
			g = q;
			b = v;
			break;
		case 4:
			r = t;
			g = p;
			b = v;
			break;
		default:
			r = v;
			g = p;
			b = q;
			break;
	}

	const red = Math.round(r * 255);
	const green = Math.round(g * 255);
	const blue = Math.round(b * 255);

	return `rgb(${red}, ${green}, ${blue})`;
}

/**
 * Format uptime seconds to human-readable string.
 */
export function formatUptime(seconds: number): string {
	const s = Math.floor(seconds);
	if (s < 60) return `${s}s`;
	if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
	const hours = Math.floor(s / 3600);
	const mins = Math.floor((s % 3600) / 60);
	return `${hours}h ${mins}m`;
}
