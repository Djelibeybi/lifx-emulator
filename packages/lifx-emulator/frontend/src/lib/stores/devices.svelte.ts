import type { Device } from '$lib/types';

function createDevicesStore() {
	let deviceMap = $state<Map<string, Device>>(new Map());

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
		},

		update(serial: string, changes: Partial<Device>) {
			const existing = deviceMap.get(serial);
			if (existing) {
				deviceMap = new Map(deviceMap);
				deviceMap.set(serial, { ...existing, ...changes });
			}
		},

		clear() {
			deviceMap = new Map();
		}
	};
}

export const devices = createDevicesStore();
