<script lang="ts">
	import { onMount } from 'svelte';
	import type { Product } from '$lib/types';
	import { fetchProducts, createDevice, deleteAllDevices } from '$lib/utils/api';
	import { devices, ui } from '$lib/stores';

	let products = $state<Product[]>([]);
	let selectedProductId = $state<number | null>(null);
	let loading = $state(false);
	let deleting = $state(false);
	let error = $state<string | null>(null);

	const PAGE_SIZES = [10, 20, 50, 100];

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

	function handlePageSizeChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		ui.setPageSize(parseInt(target.value, 10));
	}
</script>

<div class="card">
	<div class="toolbar-header">
		<h2>Device Management</h2>
		<div class="toolbar-actions">
			<!-- View toggle -->
			<div class="view-toggle">
				<button
					class="view-btn"
					class:active={ui.viewMode === 'card'}
					onclick={() => ui.setViewMode('card')}
					title="Card view"
				>
					<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
						<rect x="1" y="1" width="6" height="6" rx="1" />
						<rect x="9" y="1" width="6" height="6" rx="1" />
						<rect x="1" y="9" width="6" height="6" rx="1" />
						<rect x="9" y="9" width="6" height="6" rx="1" />
					</svg>
				</button>
				<button
					class="view-btn"
					class:active={ui.viewMode === 'table'}
					onclick={() => ui.setViewMode('table')}
					title="Table view"
				>
					<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
						<rect x="1" y="2" width="14" height="2" rx="0.5" />
						<rect x="1" y="7" width="14" height="2" rx="0.5" />
						<rect x="1" y="12" width="14" height="2" rx="0.5" />
					</svg>
				</button>
			</div>

			<!-- Page size -->
			<div class="page-size">
				<label for="page-size">Show:</label>
				<select id="page-size" value={ui.pageSize} onchange={handlePageSizeChange}>
					{#each PAGE_SIZES as size}
						<option value={size}>{size}</option>
					{/each}
				</select>
			</div>

			<button
				class="btn btn-delete"
				onclick={handleRemoveAll}
				disabled={deleting || devices.count === 0}
				title={devices.count === 0 ? 'No devices to remove' : 'Remove all devices'}
			>
				{deleting ? 'Removing...' : 'Remove All'}
			</button>
		</div>
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

<style>
	.toolbar-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
		flex-wrap: wrap;
		gap: 12px;
	}

	.toolbar-actions {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.view-toggle {
		display: flex;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		overflow: hidden;
	}

	.view-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 28px;
		background: var(--bg-secondary);
		border: none;
		cursor: pointer;
		color: var(--text-muted);
		transition: all 0.15s ease;
	}

	.view-btn:hover {
		background: var(--bg-hover);
	}

	.view-btn.active {
		background: var(--accent-primary);
		color: white;
	}

	.view-btn:first-child {
		border-right: 1px solid var(--border-color);
	}

	.page-size {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.85em;
	}

	.page-size label {
		color: var(--text-muted);
	}

	.page-size select {
		padding: 4px 8px;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		background: var(--bg-input);
		color: var(--text-primary);
		font-size: 0.9em;
	}
</style>
