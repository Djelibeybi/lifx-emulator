<script lang="ts">
	import { onMount } from 'svelte';
	import type { Product } from '$lib/types';
	import { fetchProducts, createDevice, deleteAllDevices } from '$lib/utils/api';
	import { devices } from '$lib/stores';

	let products = $state<Product[]>([]);
	let selectedProductId = $state<number | null>(null);
	let loading = $state(false);
	let deleting = $state(false);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			products = await fetchProducts();
			if (products.length > 0) {
				selectedProductId = products[0].pid;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load products';
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (selectedProductId === null) return;

		loading = true;
		error = null;

		try {
			await createDevice(selectedProductId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create device';
		} finally {
			loading = false;
		}
	}

	async function handleRemoveAll() {
		if (devices.count === 0) return;

		if (!confirm(`Remove all ${devices.count} devices?`)) return;

		deleting = true;
		error = null;

		try {
			const result = await deleteAllDevices();
			console.log(`Removed ${result.removed} devices`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to remove devices';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="card">
	<div class="toolbar-header">
		<h2>Device Management</h2>
		<button
			class="btn btn-delete"
			onclick={handleRemoveAll}
			disabled={deleting || devices.count === 0}
			title={devices.count === 0 ? 'No devices to remove' : 'Remove all devices'}
		>
			{deleting ? 'Removing...' : 'Remove All'}
		</button>
	</div>

	<form onsubmit={handleSubmit}>
		<div class="form-row">
			<div class="form-group">
				<label for="product-id">Product</label>
				<select id="product-id" bind:value={selectedProductId} disabled={products.length === 0}>
					{#if products.length === 0}
						<option value="">Loading products...</option>
					{:else}
						{#each products as product (product.pid)}
							<option value={product.pid}>{product.pid} - {product.name}</option>
						{/each}
					{/if}
				</select>
			</div>
			<button type="submit" class="btn" disabled={loading || selectedProductId === null}>
				{loading ? 'Adding...' : 'Add Device'}
			</button>
		</div>
		{#if error}
			<p style="color: var(--accent-danger); font-size: 0.85em; margin-top: 10px;">{error}</p>
		{/if}
	</form>
</div>
