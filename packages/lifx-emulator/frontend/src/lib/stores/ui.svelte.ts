import type { ViewMode, ActiveTab } from '$lib/types';

const STORAGE_KEY_VIEW = 'lifx-emulator-view';
const STORAGE_KEY_PAGE_SIZE = 'lifx-emulator-page-size';
const STORAGE_KEY_EXPANDED = 'lifx-emulator-expanded';
const STORAGE_KEY_TAB = 'lifx-emulator-tab';
const STORAGE_KEY_SHOW_STATS = 'lifx-emulator-show-stats';
const STORAGE_KEY_VIZ_COLLAPSED = 'lifx-emulator-viz-collapsed';
const STORAGE_KEY_AUTO_COMPACT = 'lifx-emulator-auto-compact';

function getStoredView(): ViewMode {
	if (typeof localStorage === 'undefined') return 'card';
	const stored = localStorage.getItem(STORAGE_KEY_VIEW);
	return stored === 'table' ? 'table' : 'card';
}

function getStoredPageSize(): number {
	if (typeof localStorage === 'undefined') return 20;
	const stored = localStorage.getItem(STORAGE_KEY_PAGE_SIZE);
	const parsed = stored ? parseInt(stored, 10) : 20;
	return [10, 20, 50, 100].includes(parsed) ? parsed : 20;
}

function getStoredExpanded(): Record<string, Set<string>> {
	if (typeof localStorage === 'undefined') return { zones: new Set(), metadata: new Set() };
	try {
		const stored = localStorage.getItem(STORAGE_KEY_EXPANDED);
		if (!stored) return { zones: new Set(), metadata: new Set() };
		const parsed = JSON.parse(stored);
		return {
			zones: new Set(parsed.zones || []),
			metadata: new Set(parsed.metadata || [])
		};
	} catch {
		return { zones: new Set(), metadata: new Set() };
	}
}

function getStoredTab(): ActiveTab {
	if (typeof localStorage === 'undefined') return 'visualizer';
	const stored = localStorage.getItem(STORAGE_KEY_TAB);
	if (
		stored === 'visualizer' ||
		stored === 'devices' ||
		stored === 'activity' ||
		stored === 'scenarios'
	)
		return stored;
	return 'visualizer';
}

function getStoredShowStats(): boolean {
	if (typeof localStorage === 'undefined') return false;
	const stored = localStorage.getItem(STORAGE_KEY_SHOW_STATS);
	return stored === 'true';
}

function getStoredVizCollapsed(): Set<string> {
	if (typeof localStorage === 'undefined') return new Set();
	try {
		const stored = localStorage.getItem(STORAGE_KEY_VIZ_COLLAPSED);
		return stored ? new Set(JSON.parse(stored)) : new Set();
	} catch {
		return new Set();
	}
}

function getStoredAutoCompact(): boolean {
	if (typeof localStorage === 'undefined') return false;
	return localStorage.getItem(STORAGE_KEY_AUTO_COMPACT) === 'true';
}

function createUiStore() {
	let viewMode = $state<ViewMode>(getStoredView());
	let pageSize = $state<number>(getStoredPageSize());
	let currentPage = $state<number>(1);
	let expanded = $state<Record<string, Set<string>>>(getStoredExpanded());
	let activeTab = $state<ActiveTab>(getStoredTab());
	let showStats = $state<boolean>(getStoredShowStats());
	let vizCollapsed = $state<Set<string>>(getStoredVizCollapsed());
	let autoCompact = $state<boolean>(getStoredAutoCompact());

	function persistExpanded() {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(
				STORAGE_KEY_EXPANDED,
				JSON.stringify({
					zones: [...expanded.zones],
					metadata: [...expanded.metadata]
				})
			);
		}
	}

	return {
		get viewMode() {
			return viewMode;
		},
		get pageSize() {
			return pageSize;
		},
		get currentPage() {
			return currentPage;
		},
		get expanded() {
			return expanded;
		},
		get activeTab() {
			return activeTab;
		},
		get showStats() {
			return showStats;
		},
		get autoCompact() {
			return autoCompact;
		},

		setViewMode(mode: ViewMode) {
			viewMode = mode;
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_VIEW, mode);
			}
		},

		setPageSize(size: number) {
			pageSize = size;
			currentPage = 1; // Reset to first page
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_PAGE_SIZE, String(size));
			}
		},

		setCurrentPage(page: number) {
			currentPage = page;
		},

		setActiveTab(tab: ActiveTab) {
			activeTab = tab;
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_TAB, tab);
			}
		},

		toggleShowStats() {
			showStats = !showStats;
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_SHOW_STATS, String(showStats));
			}
		},

		toggleZonesExpanded(serial: string) {
			if (expanded.zones.has(serial)) {
				expanded.zones.delete(serial);
			} else {
				expanded.zones.add(serial);
			}
			expanded = { ...expanded }; // Trigger reactivity
			persistExpanded();
		},

		toggleMetadataExpanded(serial: string) {
			if (expanded.metadata.has(serial)) {
				expanded.metadata.delete(serial);
			} else {
				expanded.metadata.add(serial);
			}
			expanded = { ...expanded }; // Trigger reactivity
			persistExpanded();
		},

		isZonesExpanded(serial: string): boolean {
			return expanded.zones.has(serial);
		},

		isMetadataExpanded(serial: string): boolean {
			return expanded.metadata.has(serial);
		},

		isVizCollapsed(serial: string): boolean {
			if (autoCompact) return !vizCollapsed.has(serial);
			return vizCollapsed.has(serial);
		},

		toggleVizCollapsed(serial: string) {
			vizCollapsed = new Set(vizCollapsed);
			if (vizCollapsed.has(serial)) {
				vizCollapsed.delete(serial);
			} else {
				vizCollapsed.add(serial);
			}
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_VIZ_COLLAPSED, JSON.stringify([...vizCollapsed]));
			}
		},

		collapseAllViz(_serials: string[]) {
			// In auto-compact: clear exceptions → all collapsed by default.
			// In default: clear set → none collapsed, then... we need all collapsed.
			// Actually: in default mode, set = collapsed serials; in auto-compact, set = expanded exceptions.
			vizCollapsed = autoCompact ? new Set() : new Set(_serials);
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_VIZ_COLLAPSED, JSON.stringify([...vizCollapsed]));
			}
		},

		expandAllViz(serials: string[]) {
			// In auto-compact: set = expanded exceptions, so add all serials.
			// In default: set = collapsed devices, so clear it.
			vizCollapsed = autoCompact ? new Set(serials) : new Set();
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_VIZ_COLLAPSED, JSON.stringify([...vizCollapsed]));
			}
		},

		toggleAutoCompact() {
			autoCompact = !autoCompact;
			// In auto-compact, vizCollapsed holds exceptions (expanded devices).
			// In default mode, vizCollapsed holds collapsed devices.
			// Clear on toggle so we start fresh in either mode.
			vizCollapsed = new Set();
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY_AUTO_COMPACT, String(autoCompact));
				localStorage.setItem(STORAGE_KEY_VIZ_COLLAPSED, JSON.stringify([...vizCollapsed]));
			}
		}
	};
}

export const ui = createUiStore();
