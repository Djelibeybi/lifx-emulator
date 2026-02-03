import type { ScenarioConfig, ScenariosState, ScenarioChangedData } from '$lib/types';

function createScenariosStore() {
	let state = $state<ScenariosState>({
		global: null,
		devices: {},
		types: {},
		locations: {},
		groups: {}
	});

	return {
		get global() {
			return state.global;
		},
		get devices() {
			return state.devices;
		},
		get types() {
			return state.types;
		},
		get locations() {
			return state.locations;
		},
		get groups() {
			return state.groups;
		},

		setGlobal(config: ScenarioConfig | null) {
			state.global = config;
		},

		setDevice(serial: string, config: ScenarioConfig | null) {
			if (config === null) {
				const { [serial]: _, ...rest } = state.devices;
				state.devices = rest;
			} else {
				state.devices = { ...state.devices, [serial]: config };
			}
		},

		setType(type: string, config: ScenarioConfig | null) {
			if (config === null) {
				const { [type]: _, ...rest } = state.types;
				state.types = rest;
			} else {
				state.types = { ...state.types, [type]: config };
			}
		},

		setLocation(location: string, config: ScenarioConfig | null) {
			if (config === null) {
				const { [location]: _, ...rest } = state.locations;
				state.locations = rest;
			} else {
				state.locations = { ...state.locations, [location]: config };
			}
		},

		setGroup(group: string, config: ScenarioConfig | null) {
			if (config === null) {
				const { [group]: _, ...rest } = state.groups;
				state.groups = rest;
			} else {
				state.groups = { ...state.groups, [group]: config };
			}
		},

		setAll(data: ScenariosState) {
			state = {
				global: data.global ?? null,
				devices: data.devices ?? {},
				types: data.types ?? {},
				locations: data.locations ?? {},
				groups: data.groups ?? {}
			};
		},

		handleChange(data: ScenarioChangedData) {
			switch (data.scope) {
				case 'global':
					state.global = data.config;
					break;
				case 'device':
					if (data.identifier) {
						if (data.config === null) {
							const { [data.identifier]: _, ...rest } = state.devices;
							state.devices = rest;
						} else {
							state.devices = { ...state.devices, [data.identifier]: data.config };
						}
					}
					break;
				case 'type':
					if (data.identifier) {
						if (data.config === null) {
							const { [data.identifier]: _, ...rest } = state.types;
							state.types = rest;
						} else {
							state.types = { ...state.types, [data.identifier]: data.config };
						}
					}
					break;
				case 'location':
					if (data.identifier) {
						if (data.config === null) {
							const { [data.identifier]: _, ...rest } = state.locations;
							state.locations = rest;
						} else {
							state.locations = { ...state.locations, [data.identifier]: data.config };
						}
					}
					break;
				case 'group':
					if (data.identifier) {
						if (data.config === null) {
							const { [data.identifier]: _, ...rest } = state.groups;
							state.groups = rest;
						} else {
							state.groups = { ...state.groups, [data.identifier]: data.config };
						}
					}
					break;
			}
		}
	};
}

export const scenarios = createScenariosStore();
