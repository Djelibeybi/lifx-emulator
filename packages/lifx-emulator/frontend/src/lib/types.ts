// Device and protocol types

export interface HsbkColor {
	hue: number;
	saturation: number;
	brightness: number;
	kelvin: number;
}

export interface TileDevice {
	width: number;
	height: number;
	colors: HsbkColor[];
}

export interface Device {
	serial: string;
	label: string;
	product: number;
	vendor: number;
	power_level: number;
	has_color: boolean;
	has_infrared: boolean;
	has_multizone: boolean;
	has_extended_multizone: boolean;
	has_matrix: boolean;
	has_hev: boolean;
	has_relays: boolean;
	has_buttons: boolean;
	has_chain: boolean;
	zone_count: number;
	tile_count: number;
	color?: HsbkColor;
	zone_colors?: HsbkColor[];
	tile_devices?: TileDevice[];
	group_label: string;
	location_label: string;
	wifi_signal: number;
	uptime_ns: number;
	version_major: number;
	version_minor: number;
}

export interface Stats {
	uptime_seconds: number;
	start_time: number;
	device_count: number;
	packets_received: number;
	packets_sent: number;
	packets_received_by_type: Record<string, number>;
	packets_sent_by_type: Record<string, number>;
	error_count: number;
	activity_enabled: boolean;
}

export interface ActivityEvent {
	timestamp: number;
	direction: 'rx' | 'tx';
	packet_type: number;
	packet_name: string;
	device?: string;
	target: string;
	addr: string;
}

export interface ScenarioConfig {
	drop_packets?: Record<string, number>; // packet_type -> drop_rate (0.0-1.0)
	response_delays?: Record<string, number>; // packet_type -> delay_seconds
	malformed_packets?: number[]; // packet types to corrupt
	invalid_field_values?: number[]; // packet types to send as 0xFF
	firmware_version?: [number, number] | null; // [major, minor] tuple
	partial_responses?: number[]; // packet types for incomplete data
	send_unhandled?: boolean;
}

export interface ScenariosState {
	global: ScenarioConfig | null;
	devices: Record<string, ScenarioConfig>;
	types: Record<string, ScenarioConfig>;
	locations: Record<string, ScenarioConfig>;
	groups: Record<string, ScenarioConfig>;
}

// WebSocket message types

export type WebSocketMessageType =
	| 'stats'
	| 'device_added'
	| 'device_removed'
	| 'device_updated'
	| 'activity'
	| 'scenario_changed'
	| 'sync'
	| 'error';

export interface WebSocketMessage {
	type: WebSocketMessageType;
	data?: unknown;
	message?: string;
}

export interface SyncData {
	stats?: Stats;
	devices?: Device[];
	activity?: ActivityEvent[];
	scenarios?: ScenariosState;
}

export interface DeviceUpdatedData {
	serial: string;
	changes: Partial<Device>;
}

export interface ScenarioChangedData {
	scope: 'global' | 'device' | 'type' | 'location' | 'group';
	identifier?: string;
	config: ScenarioConfig | null;
}

// Product type for dropdown
export interface Product {
	pid: number;
	name: string;
}

// Connection state
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// UI preferences
export type ViewMode = 'card' | 'table';
export type ThemeMode = 'light' | 'dark' | 'system';
export type ActiveTab = 'devices' | 'activity' | 'scenarios';
