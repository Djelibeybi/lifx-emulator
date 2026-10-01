// Ring layout for matrix devices whose zones do not follow buffer order (the
// LIFX Mirror). The device's zone_map gives the zone at each buffer position;
// this module places each zone on its physical ring so the dashboard can draw
// the fixture as it looks instead of as its 4x13 buffer.

import type { Device, HsbkColor } from '$lib/types';

export interface RingZone {
	zone: number;
	x: number;
	y: number;
	color: HsbkColor;
}

export interface MirrorRings {
	width: number;
	height: number;
	front: RingZone[];
	back: RingZone[];
}

// Firmware layout: zone 9 (front) and zone 40 (back) sit at top centre. The
// front ring runs clockwise and the back ring anticlockwise, both starting at
// the lower left in the default portrait orientation.
const FRONT_TOP_ZONE = 9;
const BACK_TOP_ZONE = 40;

// The fixture is a 22 x 36 capsule; the back ring washes the wall from the
// outer edge and the front ring faces the room just inside it.
const VIEW_WIDTH = 220;
const VIEW_HEIGHT = 360;
const OUTER_INSET = 14;
const INNER_INSET = 37;

/**
 * Point at fraction `f` (0-1) of a portrait capsule's perimeter, measured
 * clockwise from top centre.
 */
function capsulePoint(f: number, inset: number): { x: number; y: number } {
	const cx = VIEW_WIDTH / 2;
	const cy = VIEW_HEIGHT / 2;
	const r = VIEW_WIDTH / 2 - inset;
	const straight = VIEW_HEIGHT - 2 * inset - 2 * r;
	const topY = cy - straight / 2;
	const bottomY = cy + straight / 2;
	const quarterArc = (Math.PI * r) / 2;

	let s = f * (2 * straight + 2 * Math.PI * r);
	if (s < quarterArc) return arcPoint(cx, topY, r, -Math.PI / 2 + s / r);
	s -= quarterArc;
	if (s < straight) return { x: cx + r, y: topY + s };
	s -= straight;
	if (s < 2 * quarterArc) return arcPoint(cx, bottomY, r, s / r);
	s -= 2 * quarterArc;
	if (s < straight) return { x: cx - r, y: bottomY - s };
	s -= straight;
	return arcPoint(cx, topY, r, Math.PI + s / r);
}

function arcPoint(cx: number, cy: number, r: number, theta: number): { x: number; y: number } {
	return { x: cx + r * Math.cos(theta), y: cy + r * Math.sin(theta) };
}

function wrap(f: number): number {
	return ((f % 1) + 1) % 1;
}

function placeRing(
	zones: number[],
	topZone: number,
	clockwise: boolean,
	inset: number,
	colorOf: (zone: number) => HsbkColor
): RingZone[] {
	const count = zones.length;
	return zones.map((zone) => {
		const steps = clockwise ? zone - topZone : topZone - zone;
		const { x, y } = capsulePoint(wrap(steps / count), inset);
		return { zone, x, y, color: colorOf(zone) };
	});
}

/**
 * Lay out a device's zones on its front and back rings, or return null when
 * the device has no zone map (its zones follow buffer order).
 */
export function mirrorRings(device: Device): MirrorRings | null {
	const zoneMap = device.zone_map;
	const colors = device.tile_devices?.[0]?.colors;
	if (!zoneMap || device.uplight_zone_count == null || !colors) return null;
	if (colors.length < zoneMap.length) return null;

	const bufferPosition = new Map<number, number>();
	zoneMap.forEach((zone, position) => {
		if (zone >= 0) bufferPosition.set(zone, position);
	});
	const colorOf = (zone: number) => colors[bufferPosition.get(zone) as number];

	// The uplight (back) ring is the trailing zones in zone order.
	const zones = [...bufferPosition.keys()].sort((a, b) => a - b);
	const frontCount = zones.length - device.uplight_zone_count;

	return {
		width: VIEW_WIDTH,
		height: VIEW_HEIGHT,
		front: placeRing(zones.slice(0, frontCount), FRONT_TOP_ZONE, true, INNER_INSET, colorOf),
		back: placeRing(zones.slice(frontCount), BACK_TOP_ZONE, false, OUTER_INSET, colorOf)
	};
}

/** Number of zones that drive a light, excluding unused buffer positions. */
export function addressableZoneCount(device: Device): number | null {
	if (!device.zone_map) return null;
	return device.zone_map.filter((zone) => zone >= 0).length;
}
