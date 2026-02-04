import type { Device, DeviceTransition, DeviceStateChanges } from '$lib/types';

function createDevicesStore() {
	let deviceMap = $state<Map<string, Device>>(new Map());
	let transitionMap = $state<Map<string, DeviceTransition>>(new Map());

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
			const existing = deviceMap.get(serial);
			if (!existing) {
				console.warn('updateWithTransition: device not found:', serial);
				return;
			}

			console.log('updateWithTransition:', serial, changes);

			// Update device state
			const updatedDevice: Device = { ...existing };
			if (changes.color) {
				updatedDevice.color = changes.color;
				console.log('Updated color:', changes.color);
			}
			if (changes.power_level !== undefined) {
				updatedDevice.power_level = changes.power_level;
				console.log('Updated power_level:', changes.power_level);
			}
			if (changes.zone_colors) {
				updatedDevice.zone_colors = changes.zone_colors;
				console.log('Updated zone_colors:', changes.zone_colors.length, 'zones');
			}
			if (changes.tile_devices) {
				updatedDevice.tile_devices = changes.tile_devices;
				console.log('Updated tile_devices:', changes.tile_devices.length, 'tiles');
			}

			deviceMap = new Map(deviceMap);
			deviceMap.set(serial, updatedDevice);

			// Update transition info
			if (changes.duration_ms !== undefined && changes.duration_ms > 0) {
				transitionMap = new Map(transitionMap);
				transitionMap.set(serial, {
					serial,
					duration_ms: changes.duration_ms,
					timestamp: Date.now()
				});
				console.log('Set transition:', changes.duration_ms, 'ms');
			}
		},

		clear() {
			deviceMap = new Map();
			transitionMap = new Map();
		}
	};
}

export const devices = createDevicesStore();
