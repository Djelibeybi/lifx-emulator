import type { Stats } from '$lib/types';

const DEFAULT_STATS: Stats = {
	uptime_seconds: 0,
	start_time: 0,
	device_count: 0,
	packets_received: 0,
	packets_sent: 0,
	packets_received_by_type: {},
	packets_sent_by_type: {},
	error_count: 0,
	activity_enabled: false
};

function createStatsStore() {
	let stats = $state<Stats>({ ...DEFAULT_STATS });

	return {
		get value() {
			return stats;
		},

		set(newStats: Stats) {
			stats = newStats;
		},

		reset() {
			stats = { ...DEFAULT_STATS };
		}
	};
}

export const stats = createStatsStore();
