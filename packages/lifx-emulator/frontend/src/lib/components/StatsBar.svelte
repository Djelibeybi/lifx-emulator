<script lang="ts">
	import { stats } from '$lib/stores';
	import { formatUptime } from '$lib/utils/color';
</script>

<div class="card">
	<h2>
		<span class="status-indicator"></span>
		Server Statistics
	</h2>
	<div class="stats-list">
		<div class="stat">
			<span class="stat-label">Uptime</span>
			<span class="stat-value">{formatUptime(stats.value.uptime_seconds)}</span>
		</div>
		<div class="stat">
			<span class="stat-label">Devices</span>
			<span class="stat-value">{stats.value.device_count}</span>
		</div>
		<div class="stat">
			<span class="stat-label">Packets RX</span>
			<span class="stat-value">{stats.value.packets_received}</span>
		</div>
		<div class="stat">
			<span class="stat-label">Packets TX</span>
			<span class="stat-value">{stats.value.packets_sent}</span>
		</div>
		<div class="stat">
			<span class="stat-label">Errors</span>
			<span class="stat-value">{stats.value.error_count}</span>
		</div>
	</div>
</div>
