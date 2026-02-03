import type { ViewMode } from '$lib/types';

const STORAGE_KEY_VIEW = 'lifx-emulator-view';
const STORAGE_KEY_PAGE_SIZE = 'lifx-emulator-page-size';
const STORAGE_KEY_EXPANDED = 'lifx-emulator-expanded';

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

function createUiStore() {
	let viewMode = $state<ViewMode>(getStoredView());
	let pageSize = $state<number>(getStoredPageSize());
	let currentPage = $state<number>(1);
	let expanded = $state<Record<string, Set<string>>>(getStoredExpanded());

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
		}
	};
}

export const ui = createUiStore();
