import type { ThemeMode } from '$lib/types';

const STORAGE_KEY = 'lifx-emulator-theme';

function getStoredTheme(): ThemeMode {
	if (typeof localStorage === 'undefined') return 'system';
	const stored = localStorage.getItem(STORAGE_KEY);
	if (stored === 'light' || stored === 'dark' || stored === 'system') {
		return stored;
	}
	return 'system';
}

function getEffectiveTheme(mode: ThemeMode): 'light' | 'dark' {
	if (mode === 'system') {
		if (typeof window === 'undefined') return 'dark';
		return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
	}
	return mode;
}

function createThemeStore() {
	let mode = $state<ThemeMode>(getStoredTheme());
	// Track system theme preference changes
	let systemPrefersDark = $state(
		typeof window !== 'undefined'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
			: true
	);

	// Derive effective theme from mode and system preference
	const effective = $derived.by((): 'light' | 'dark' => {
		if (mode === 'system') {
			return systemPrefersDark ? 'dark' : 'light';
		}
		return mode;
	});

	// Apply theme to document immediately (safe during SSR/CSR)
	function applyTheme() {
		if (typeof document !== 'undefined') {
			document.documentElement.setAttribute('data-theme', effective);
		}
	}

	// Listen for system theme changes
	if (typeof window !== 'undefined') {
		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
			systemPrefersDark = e.matches;
		});
	}

	return {
		get mode() {
			return mode;
		},
		get effective() {
			return effective;
		},
		applyTheme,
		set(newMode: ThemeMode) {
			mode = newMode;
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem(STORAGE_KEY, newMode);
			}
			applyTheme();
		},
		toggle() {
			// Cycle: light -> dark -> system -> light
			const next: ThemeMode = mode === 'light' ? 'dark' : mode === 'dark' ? 'system' : 'light';
			this.set(next);
		}
	};
}

export const theme = createThemeStore();
