import type { HsbkColor } from '$lib/types';

/**
 * Convert sRGB gamma-encoded value (0-1) to linear.
 */
function srgbToLinear(c: number): number {
	return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/**
 * Convert kelvin color temperature to linear sRGB.
 * Uses Tanner Helland's approximation of CIE standard observer data.
 * Returns normalized RGB where the brightest channel = 1.
 */
function kelvinToLinearRgb(kelvin: number): [number, number, number] {
	const temp = Math.max(1500, Math.min(9000, kelvin)) / 100;

	let r: number, g: number, b: number;

	// Red channel
	if (temp <= 66) {
		r = 1;
	} else {
		r = 329.698727446 * Math.pow(temp - 60, -0.1332047592) / 255;
	}

	// Green channel
	if (temp <= 66) {
		g = (99.4708025861 * Math.log(temp) - 161.1195681661) / 255;
	} else {
		g = 288.1221695283 * Math.pow(temp - 60, -0.0755148492) / 255;
	}

	// Blue channel
	if (temp >= 66) {
		b = 1;
	} else if (temp <= 19) {
		b = 0;
	} else {
		b = (138.5177312231 * Math.log(temp - 10) - 305.0447927307) / 255;
	}

	// Clamp to [0, 1]
	r = Math.max(0, Math.min(1, r));
	g = Math.max(0, Math.min(1, g));
	b = Math.max(0, Math.min(1, b));

	// Convert from sRGB to linear
	r = srgbToLinear(r);
	g = srgbToLinear(g);
	b = srgbToLinear(b);

	// Normalize so max channel = 1 (preserve chromaticity, not intensity)
	const maxC = Math.max(r, g, b, 1e-6);
	return [r / maxC, g / maxC, b / maxC];
}

/**
 * Convert HSV hue (0-1) to linear sRGB at full saturation and brightness.
 * The output is the pure spectral hue in linear light.
 */
function hueToLinearRgb(hue: number): [number, number, number] {
	const i = Math.floor(hue * 6);
	const f = hue * 6 - i;

	// HSV with S=1, V=1 → p=0, q=1-f, t=f
	let r: number, g: number, b: number;
	switch (i % 6) {
		case 0: r = 1; g = f; b = 0; break;
		case 1: r = 1 - f; g = 1; b = 0; break;
		case 2: r = 0; g = 1; b = f; break;
		case 3: r = 0; g = 1 - f; b = 1; break;
		case 4: r = f; g = 0; b = 1; break;
		default: r = 1; g = 0; b = 1 - f; break;
	}

	// These are sRGB values — linearize for Oklab
	return [srgbToLinear(r), srgbToLinear(g), srgbToLinear(b)];
}

/**
 * Convert linear sRGB to Oklab perceptual color space.
 * Returns [L, a, b] where L is lightness (0-1), a/b are chromaticity axes.
 */
function linearRgbToOklab(r: number, g: number, b: number): [number, number, number] {
	const l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
	const m_ = 0.2119034982 * r + 0.7736482137 * g + 0.0144482941 * b;
	const s_ = 0.0883024619 * r + 0.2289318678 * g + 0.6727557165 * b;

	const l = Math.cbrt(l_);
	const m = Math.cbrt(m_);
	const s = Math.cbrt(s_);

	return [
		0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
		1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
		0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
	];
}

const cssCache = new Map<string, string>();
const CSS_CACHE_MAX = 4096;

function evictHalf(cache: Map<string, unknown>) {
	let i = 0;
	const half = Math.floor(cache.size / 2);
	for (const k of cache.keys()) {
		if (i++ >= half) break;
		cache.delete(k);
	}
}

function cacheAndReturn(key: string, value: string): string {
	if (cssCache.size >= CSS_CACHE_MAX) evictHalf(cssCache);
	cssCache.set(key, value);
	return value;
}

/**
 * Convert LIFX HSBK color to a CSS oklch() color string.
 *
 * HSBK: hue/saturation/brightness are 16-bit (0-65535), kelvin is 1500-9000.
 *
 * When saturation is low, kelvin determines the white point (warm amber to cool blue).
 * When saturation is high, hue determines the color and kelvin is ignored.
 * Brightness controls overall lightness.
 */
export function hsbkToCss(hsbk: HsbkColor): string {
	const key = `${hsbk.hue},${hsbk.saturation},${hsbk.brightness},${hsbk.kelvin}`;
	const cached = cssCache.get(key);
	if (cached) return cached;

	const h = hsbk.hue / 65535;
	const s = hsbk.saturation / 65535;
	const v = hsbk.brightness / 65535;

	if (v === 0) {
		return cacheAndReturn(key, 'oklch(0% 0 none)');
	}

	// Blend between pure hue color and kelvin white based on saturation
	const hueRgb = hueToLinearRgb(h);
	const kelvinRgb = kelvinToLinearRgb(hsbk.kelvin);

	const r = (s * hueRgb[0] + (1 - s) * kelvinRgb[0]) * v;
	const g = (s * hueRgb[1] + (1 - s) * kelvinRgb[1]) * v;
	const b = (s * hueRgb[2] + (1 - s) * kelvinRgb[2]) * v;

	// Convert to Oklab, then to polar Oklch
	const [L, a, ob] = linearRgbToOklab(r, g, b);
	const C = Math.sqrt(a * a + ob * ob);
	let H = Math.atan2(ob, a) * (180 / Math.PI);
	if (H < 0) H += 360;

	const lPct = Math.max(0, Math.min(100, L * 100));

	// When chroma is negligible, use achromatic form
	if (C < 0.002) {
		return cacheAndReturn(key, `oklch(${lPct.toFixed(1)}% 0 none)`);
	}

	return cacheAndReturn(key, `oklch(${lPct.toFixed(1)}% ${C.toFixed(4)} ${H.toFixed(1)})`);
}

/**
 * Convert a single HSBK to linear RGB [r, g, b] (not clamped, not gamma-encoded).
 */
const linearRgbCache = new Map<string, [number, number, number]>();
const LINEAR_RGB_CACHE_MAX = 4096;

function hsbkToLinearRgb(hsbk: HsbkColor): [number, number, number] {
	const key = `${hsbk.hue},${hsbk.saturation},${hsbk.brightness},${hsbk.kelvin}`;
	const cached = linearRgbCache.get(key);
	if (cached) return cached;

	const h = hsbk.hue / 65535;
	const s = hsbk.saturation / 65535;
	const v = hsbk.brightness / 65535;

	const hueRgb = hueToLinearRgb(h);
	const kelvinRgb = kelvinToLinearRgb(hsbk.kelvin);

	const result: [number, number, number] = [
		(s * hueRgb[0] + (1 - s) * kelvinRgb[0]) * v,
		(s * hueRgb[1] + (1 - s) * kelvinRgb[1]) * v,
		(s * hueRgb[2] + (1 - s) * kelvinRgb[2]) * v
	];

	if (linearRgbCache.size >= LINEAR_RGB_CACHE_MAX) evictHalf(linearRgbCache);
	linearRgbCache.set(key, result);
	return result;
}

/**
 * Average an array of HSBK colors in linear RGB space and return an oklch
 * glow color string with alpha. Returns null if colors are too dark.
 */
function averageToGlowColor(colors: HsbkColor[]): string | null {
	if (colors.length === 0) return null;

	let rSum = 0, gSum = 0, bSum = 0;
	for (const color of colors) {
		const [r, g, b] = hsbkToLinearRgb(color);
		rSum += r;
		gSum += g;
		bSum += b;
	}
	const n = colors.length;
	const rAvg = rSum / n, gAvg = gSum / n, bAvg = bSum / n;

	if (rAvg + gAvg + bAvg < 0.005) return null;

	const [L, a, ob] = linearRgbToOklab(rAvg, gAvg, bAvg);
	const C = Math.sqrt(a * a + ob * ob);
	let H = Math.atan2(ob, a) * (180 / Math.PI);
	if (H < 0) H += 360;

	const glowL = Math.min(85, L * 130);
	const avgBrightness = Math.sqrt(rAvg * rAvg + gAvg * gAvg + bAvg * bAvg);
	const alpha = Math.min(0.55, 0.15 + avgBrightness * 0.5);

	return C < 0.002
		? `oklch(${glowL.toFixed(0)}% 0 none / ${alpha.toFixed(2)})`
		: `oklch(${glowL.toFixed(0)}% ${C.toFixed(3)} ${H.toFixed(0)} / ${alpha.toFixed(2)})`;
}

/**
 * Ambilight-style directional glow. Each edge of the card glows the color
 * of the zones nearest to it. Accepts edge color arrays for top/right/bottom/left.
 */
export function directionalGlow(edges: {
	top: HsbkColor[];
	right: HsbkColor[];
	bottom: HsbkColor[];
	left: HsbkColor[];
}): string {
	const shadows: string[] = [];

	const top = averageToGlowColor(edges.top);
	const right = averageToGlowColor(edges.right);
	const bottom = averageToGlowColor(edges.bottom);
	const left = averageToGlowColor(edges.left);

	if (top) shadows.push(`inset 0 8px 18px -2px ${top}`);
	if (right) shadows.push(`inset -8px 0 18px -2px ${right}`);
	if (bottom) shadows.push(`inset 0 -8px 18px -2px ${bottom}`);
	if (left) shadows.push(`inset 8px 0 18px -2px ${left}`);

	return shadows.length > 0 ? shadows.join(', ') : 'none';
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
