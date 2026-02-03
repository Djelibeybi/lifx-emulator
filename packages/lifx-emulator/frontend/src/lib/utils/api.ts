import type { Product, ScenarioConfig } from '$lib/types';

const API_BASE = '/api';

type ScenarioScope = 'devices' | 'types' | 'locations' | 'groups';

/**
 * Fetch list of available products from the API.
 */
export async function fetchProducts(): Promise<Product[]> {
	const response = await fetch(`${API_BASE}/products`);
	if (!response.ok) {
		throw new Error(`Failed to fetch products: ${response.status}`);
	}
	return response.json();
}

/**
 * Create a new device with the specified product ID.
 */
export async function createDevice(productId: number): Promise<void> {
	const response = await fetch(`${API_BASE}/devices`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ product_id: productId })
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || `Failed to create device: ${response.status}`);
	}
}

/**
 * Delete a device by serial.
 */
export async function deleteDevice(serial: string): Promise<void> {
	const response = await fetch(`${API_BASE}/devices/${serial}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error(`Failed to delete device: ${response.status}`);
	}
}

/**
 * Delete all devices.
 */
export async function deleteAllDevices(): Promise<{ message: string; removed: number }> {
	const response = await fetch(`${API_BASE}/devices`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error(`Failed to remove devices: ${response.status}`);
	}
	return response.json();
}

// Scenario API functions

/**
 * Get the global scenario configuration.
 */
export async function getGlobalScenario(): Promise<ScenarioConfig | null> {
	const response = await fetch(`${API_BASE}/scenarios/global`);
	if (!response.ok) {
		throw new Error(`Failed to get global scenario: ${response.status}`);
	}
	const data = await response.json();
	return data.scenario;
}

/**
 * Set the global scenario configuration.
 */
export async function setGlobalScenario(config: ScenarioConfig): Promise<void> {
	const response = await fetch(`${API_BASE}/scenarios/global`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(config)
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || `Failed to set global scenario: ${response.status}`);
	}
}

/**
 * Clear the global scenario configuration.
 */
export async function clearGlobalScenario(): Promise<void> {
	const response = await fetch(`${API_BASE}/scenarios/global`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		throw new Error(`Failed to clear global scenario: ${response.status}`);
	}
}

/**
 * Get a scenario for a specific scope and identifier.
 */
export async function getScenario(
	scope: ScenarioScope,
	identifier: string
): Promise<ScenarioConfig | null> {
	const response = await fetch(`${API_BASE}/scenarios/${scope}/${encodeURIComponent(identifier)}`);
	if (response.status === 404) {
		return null;
	}
	if (!response.ok) {
		throw new Error(`Failed to get ${scope} scenario: ${response.status}`);
	}
	const data = await response.json();
	return data.scenario;
}

/**
 * Set a scenario for a specific scope and identifier.
 */
export async function setScenario(
	scope: ScenarioScope,
	identifier: string,
	config: ScenarioConfig
): Promise<void> {
	const response = await fetch(`${API_BASE}/scenarios/${scope}/${encodeURIComponent(identifier)}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(config)
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || `Failed to set ${scope} scenario: ${response.status}`);
	}
}

/**
 * Clear a scenario for a specific scope and identifier.
 */
export async function clearScenario(scope: ScenarioScope, identifier: string): Promise<void> {
	const response = await fetch(`${API_BASE}/scenarios/${scope}/${encodeURIComponent(identifier)}`, {
		method: 'DELETE'
	});
	if (response.status === 404) {
		// Already cleared, not an error
		return;
	}
	if (!response.ok) {
		throw new Error(`Failed to clear ${scope} scenario: ${response.status}`);
	}
}
