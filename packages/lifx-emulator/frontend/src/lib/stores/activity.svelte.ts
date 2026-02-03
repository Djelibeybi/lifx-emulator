import type { ActivityEvent } from '$lib/types';

const MAX_EVENTS = 100;

function createActivityStore() {
	let events = $state<ActivityEvent[]>([]);

	return {
		get list(): ActivityEvent[] {
			return events;
		},

		get count(): number {
			return events.length;
		},

		set(newEvents: ActivityEvent[]) {
			// Keep only the most recent MAX_EVENTS
			events = newEvents.slice(-MAX_EVENTS);
		},

		add(event: ActivityEvent) {
			// Add to the end and trim from the beginning if needed
			events = [...events, event].slice(-MAX_EVENTS);
		},

		clear() {
			events = [];
		},

		// Get events in reverse chronological order (newest first)
		get reversed(): ActivityEvent[] {
			return [...events].reverse();
		}
	};
}

export const activity = createActivityStore();
