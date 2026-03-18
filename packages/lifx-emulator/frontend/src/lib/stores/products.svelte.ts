import type { Product } from '$lib/types';
import { fetchProducts } from '$lib/utils/api';

function createProductsStore() {
	let items = $state<Product[]>([]);
	let loaded = false;
	let loading = false;

	return {
		get list(): Product[] {
			return items;
		},

		get isLoaded(): boolean {
			return loaded;
		},

		async load() {
			if (loaded || loading) return;
			loading = true;
			try {
				items = await fetchProducts();
				loaded = true;
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
