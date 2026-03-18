import type { Product } from '$lib/types';
import { fetchProducts } from '$lib/utils/api';

function createProductsStore() {
	let items = $state<Product[]>([]);
	let loaded = $state(false);
	let loading = $state(false);
	let error = $state<string | null>(null);

	return {
		get list(): Product[] {
			return items;
		},

		get isLoaded(): boolean {
			return loaded;
		},

		get isLoading(): boolean {
			return loading;
		},

		get error(): string | null {
			return error;
		},

		async load() {
			if (loaded || loading) return;
			loading = true;
			error = null;
			try {
				items = await fetchProducts();
				loaded = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to load products';
			} finally {
				loading = false;
			}
		},

		getName(pid: number): string {
			const product = items.find((p) => p.pid === pid);
			return product?.name ?? `Product ${pid}`;
		}
	};
}

export const products = createProductsStore();
