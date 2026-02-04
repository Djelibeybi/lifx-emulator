import type { Device, DeviceTransition, DeviceStateChanges } from '$lib/types';

function createDevicesStore() {
	let deviceMap = $state<Map<string, Device>>(new Map());
	let transitionMap = $state<Map<string, DeviceTransition>>(new Map());

	// Throttle high-frequency updates using requestAnimationFrame
	let pendingUpdates = new Map<string, { device: Device; transition?: DeviceTransition }>();
	let rafScheduled = false;

	function flushPendingUpdates() {
		if (pendingUpdates.size === 0) {
			rafScheduled = false;
			return;
		}

		// Apply all pending updates in one batch
		const newDeviceMap = new Map(deviceMap);
		const newTransitionMap = new Map(transitionMap);

		for (const [serial, update] of pendingUpdates) {
			newDeviceMap.set(serial, update.device);
			if (update.transition) {
				newTransitionMap.set(serial, update.transition);
			} else {
				newTransitionMap.delete(serial);
			}
		}

		deviceMap = newDeviceMap;
		transitionMap = newTransitionMap;
		pendingUpdates.clear();
		rafScheduled = false;
	}

	function scheduleUpdate(serial: string, device: Device, transition?: DeviceTransition) {
		pendingUpdates.set(serial, { device, transition });
		if (!rafScheduled) {
			rafScheduled = true;
			requestAnimationFrame(flushPendingUpdates);
		}
	}

	return {
		get map() {
			return deviceMap;
		},

		get list(): Device[] {
			return [...deviceMap.values()];
		},

		get count(): number {
			return deviceMap.size;
		},

		get(serial: string): Device | undefined {
			return deviceMap.get(serial);
		},

		getTransition(serial: string): DeviceTransition | undefined {
			return transitionMap.get(serial);
		},

		set(devices: Device[]) {
			const newMap = new Map<string, Device>();
			for (const device of devices) {
				newMap.set(device.serial, device);
			}
			deviceMap = newMap;
		},

		add(device: Device) {
			deviceMap = new Map(deviceMap);
			deviceMap.set(device.serial, device);
		},

		remove(serial: string) {
			pendingUpdates.delete(serial);
			deviceMap = new Map(deviceMap);
			deviceMap.delete(serial);
			transitionMap = new Map(transitionMap);
			transitionMap.delete(serial);
		},

		update(serial: string, changes: Partial<Device>) {
			const existing = deviceMap.get(serial);
			if (existing) {
				deviceMap = new Map(deviceMap);
				deviceMap.set(serial, { ...existing, ...changes });
			}
		},

		updateWithTransition(serial: string, changes: DeviceStateChanges) {
			// Check pending updates first, then fall back to current state
			const pending = pendingUpdates.get(serial);
			const existing = pending?.device ?? deviceMap.get(serial);
			if (!existing) {
				return;
			}

			// Update device state
			const updatedDevice: Device = { ...existing };
			if (changes.color) {
				updatedDevice.color = changes.color;
			}
			if (changes.power_level !== undefined) {
				updatedDevice.power_level = changes.power_level;
			}
			if (changes.zone_colors !== undefined) {
				updatedDevice.zone_colors = changes.zone_colors;
			}
			if (changes.tile_devices !== undefined) {
				updatedDevice.tile_devices = changes.tile_devices;
			}

			// Build transition info
			let transition: DeviceTransition | undefined;
			if (changes.duration_ms !== undefined && changes.duration_ms > 0) {
				transition = {
					serial,
					duration_ms: changes.duration_ms,
					timestamp: Date.now()
				};
			}

			// Schedule the update to be applied on next animation frame
			scheduleUpdate(serial, updatedDevice, transition);
		},

		clear() {
			pendingUpdates.clear();
			deviceMap = new Map();
			transitionMap = new Map();
		}
	};
}

export const devices = createDevicesStore();
