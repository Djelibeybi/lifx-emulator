<script lang="ts">
	import { ui } from '$lib/stores';

	let { totalPages }: { totalPages: number } = $props();

	function goToPreviousPage() {
		if (ui.currentPage > 1) ui.setCurrentPage(ui.currentPage - 1);
	}

	function goToNextPage() {
		if (ui.currentPage < totalPages) ui.setCurrentPage(ui.currentPage + 1);
	}
</script>

{#if totalPages > 1}
	<div class="pagination">
		<button class="btn btn-sm" onclick={goToPreviousPage} disabled={ui.currentPage <= 1}>
			Previous
		</button>
		<span class="page-info">
			Page {ui.currentPage} of {totalPages}
		</span>
		<button class="btn btn-sm" onclick={goToNextPage} disabled={ui.currentPage >= totalPages}>
			Next
		</button>
	</div>
{/if}

<style>
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 16px;
		margin-top: 16px;
		padding-top: 12px;
		border-top: 1px solid var(--border-primary);
	}

	.page-info {
		font-size: 0.9em;
		color: var(--text-muted);
	}
</style>
