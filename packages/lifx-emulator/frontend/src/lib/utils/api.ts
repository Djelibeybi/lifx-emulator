import type { Product } from '$lib/types';

const API_BASE = '/api';

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
