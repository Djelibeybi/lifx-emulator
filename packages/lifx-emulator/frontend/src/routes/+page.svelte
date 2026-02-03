<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { connection } from '$lib/stores';
	import { Header, StatsBar, AddDeviceForm, DeviceList, ActivityLog } from '$lib/components';

	onMount(() => {
		connection.connect();
	});

	onDestroy(() => {
		connection.disconnect();
	});
</script>

<div class="container">
	<Header />

	<div class="grid">
		<StatsBar />
		<AddDeviceForm />
	</div>

	<DeviceList />

	<div style="margin-top: 25px;">
		<ActivityLog />
	</div>
</div>
