<script lang="ts">
	import { onMount } from 'svelte';
	import type { Product } from '$lib/types';
	import { fetchProducts, createDevice } from '$lib/utils/api';

	let products = $state<Product[]>([]);
	let selectedProductId = $state<number | null>(null);
	let loading = $state(false);
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
</script>

<div class="card">
	<h2>Add Device</h2>
	<form onsubmit={handleSubmit}>
		<div class="form-group">
			<label for="product-id">Product ID</label>
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
		{#if error}
			<p style="color: var(--accent-danger); font-size: 0.85em; margin-bottom: 10px;">{error}</p>
		{/if}
		<button type="submit" class="btn" disabled={loading || selectedProductId === null}>
			{loading ? 'Adding...' : 'Add Device'}
		</button>
	</form>
</div>
