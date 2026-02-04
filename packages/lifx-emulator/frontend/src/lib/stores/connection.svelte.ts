import type {
	ConnectionStatus,
	WebSocketMessage,
	SyncData,
	DeviceUpdatedData,
	ScenarioChangedData,
	Stats,
	Device,
	ActivityEvent
} from '$lib/types';
import { stats } from './stats.svelte';
import { devices } from './devices.svelte';
import { activity } from './activity.svelte';
import { scenarios } from './scenarios.svelte';

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_DELAY_MS = 30000;

function createConnectionStore() {
	let status = $state<ConnectionStatus>('disconnected');
	let ws: WebSocket | null = null;
	let reconnectDelay = RECONNECT_DELAY_MS;
	let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
	let shouldReconnect = true;

	function getWebSocketUrl(): string {
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		return `${protocol}//${window.location.host}/ws`;
	}

	function handleMessage(event: MessageEvent) {
		try {
			const msg: WebSocketMessage = JSON.parse(event.data);

			switch (msg.type) {
				case 'sync': {
					const data = msg.data as SyncData;
					if (data.stats) stats.set(data.stats);
					if (data.devices) devices.set(data.devices);
					if (data.activity) activity.set(data.activity);
					if (data.scenarios) scenarios.setAll(data.scenarios);
					break;
				}
				case 'stats':
					stats.set(msg.data as Stats);
					break;
				case 'device_added':
					devices.add(msg.data as Device);
					break;
				case 'device_removed': {
					const { serial } = msg.data as { serial: string };
					devices.remove(serial);
					break;
				}
				case 'device_updated': {
					const { serial, changes } = msg.data as DeviceUpdatedData;
					console.log('device_updated received:', serial, changes);
					// Use transition-aware update if this is a state change with duration
					if (changes.category !== undefined) {
						console.log('Using updateWithTransition for category:', changes.category);
						devices.updateWithTransition(serial, changes);
					} else {
						devices.update(serial, changes);
					}
					break;
				}
				case 'activity':
					activity.add(msg.data as ActivityEvent);
					break;
				case 'scenario_changed':
					scenarios.handleChange(msg.data as ScenarioChangedData);
					break;
				case 'error':
					console.error('WebSocket error:', msg.message);
					break;
			}
		} catch (e) {
			console.error('Failed to parse WebSocket message:', e);
		}
	}

	function connect() {
		shouldReconnect = true;
		if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
			return;
		}

		status = 'connecting';

		try {
			ws = new WebSocket(getWebSocketUrl());

			ws.onopen = () => {
				status = 'connected';
				reconnectDelay = RECONNECT_DELAY_MS; // Reset delay on successful connect

				// Subscribe to all topics
				ws!.send(
					JSON.stringify({
						type: 'subscribe',
						topics: ['stats', 'devices', 'activity', 'scenarios']
					})
				);

				// Request full state sync
				ws!.send(JSON.stringify({ type: 'sync' }));
			};

			ws.onmessage = handleMessage;

			ws.onclose = () => {
				status = 'disconnected';
				ws = null;
				if (shouldReconnect) scheduleReconnect();
			};

			ws.onerror = () => {
				status = 'error';
				ws?.close();
			};
		} catch (e) {
			console.error('WebSocket connection error:', e);
			status = 'error';
			scheduleReconnect();
		}
	}

	function scheduleReconnect() {
		if (reconnectTimeout) {
			clearTimeout(reconnectTimeout);
		}

		reconnectTimeout = setTimeout(() => {
			reconnectTimeout = null;
			connect();
		}, reconnectDelay);

		// Exponential backoff
		reconnectDelay = Math.min(reconnectDelay * 1.5, MAX_RECONNECT_DELAY_MS);
	}

	function disconnect() {
		shouldReconnect = false;
		if (reconnectTimeout) {
			clearTimeout(reconnectTimeout);
			reconnectTimeout = null;
		}

		if (ws) {
			ws.close();
			ws = null;
		}

		status = 'disconnected';
	}

	function send(message: object) {
		if (ws && ws.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify(message));
		}
	}

	return {
		get status() {
			return status;
		},

		connect,
		disconnect,
		send,

		// Request a fresh sync
		sync() {
			send({ type: 'sync' });
		}
	};
}

export const connection = createConnectionStore();
