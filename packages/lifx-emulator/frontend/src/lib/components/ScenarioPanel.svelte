<script lang="ts">
	import type { ScenarioConfig } from '$lib/types';
	import { scenarios, devices } from '$lib/stores';
	import {
		getGlobalScenario,
		setGlobalScenario,
		clearGlobalScenario,
		getScenario,
		setScenario,
		clearScenario
	} from '$lib/utils/api';

	type Scope = 'global' | 'device' | 'type' | 'location' | 'group';
	type ApiScope = 'devices' | 'types' | 'locations' | 'groups';

	const DEVICE_TYPES = ['matrix', 'extended_multizone', 'multizone', 'hev', 'infrared', 'color', 'basic'];

	let activeScope = $state<Scope>('global');
	let selectedIdentifier = $state<string>('');
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Form state
	let dropPackets = $state<Array<{ packetType: string; rate: string }>>([]);
	let responseDelays = $state<Array<{ packetType: string; delay: string }>>([]);
	let malformedPackets = $state<string>('');
	let invalidFieldValues = $state<string>('');
	let firmwareMajor = $state<string>('');
	let firmwareMinor = $state<string>('');
	let partialResponses = $state<string>('');
	let sendUnhandled = $state(false);

	function scopeToApiScope(scope: Scope): ApiScope {
		const map: Record<Scope, ApiScope> = {
			global: 'devices', // not used for global
			device: 'devices',
			type: 'types',
			location: 'locations',
			group: 'groups'
		};
		return map[scope];
	}

	// Available identifiers based on scope
	let availableIdentifiers = $derived(() => {
		switch (activeScope) {
			case 'device':
				return devices.list.map((d) => d.serial);
			case 'type':
				return DEVICE_TYPES;
			case 'location':
				return [...new Set(devices.list.map((d) => d.location_label).filter(Boolean))];
			case 'group':
				return [...new Set(devices.list.map((d) => d.group_label).filter(Boolean))];
			default:
				return [];
		}
	});

	// Current scenario from store
	let currentScenario = $derived(() => {
		switch (activeScope) {
			case 'global':
				return scenarios.global;
			case 'device':
				return selectedIdentifier ? scenarios.devices[selectedIdentifier] : null;
			case 'type':
				return selectedIdentifier ? scenarios.types[selectedIdentifier] : null;
			case 'location':
				return selectedIdentifier ? scenarios.locations[selectedIdentifier] : null;
			case 'group':
				return selectedIdentifier ? scenarios.groups[selectedIdentifier] : null;
			default:
				return null;
		}
	});

	function loadFromScenario(config: ScenarioConfig | null) {
		if (!config) {
			dropPackets = [];
			responseDelays = [];
			malformedPackets = '';
			invalidFieldValues = '';
			firmwareMajor = '';
			firmwareMinor = '';
			partialResponses = '';
			sendUnhandled = true; // Default is on
			return;
		}

		// Drop packets
		if (config.drop_packets && Object.keys(config.drop_packets).length > 0) {
			dropPackets = Object.entries(config.drop_packets).map(([k, v]) => ({
				packetType: k,
				rate: String(v)
			}));
		} else {
			dropPackets = [];
		}

		// Response delays
		if (config.response_delays && Object.keys(config.response_delays).length > 0) {
			responseDelays = Object.entries(config.response_delays).map(([k, v]) => ({
				packetType: k,
				delay: String(v)
			}));
		} else {
			responseDelays = [];
		}

		// Arrays to comma-separated strings
		malformedPackets = config.malformed_packets?.join(', ') || '';
		invalidFieldValues = config.invalid_field_values?.join(', ') || '';
		partialResponses = config.partial_responses?.join(', ') || '';

		// Firmware version
		if (config.firmware_version) {
			firmwareMajor = String(config.firmware_version[0]);
			firmwareMinor = String(config.firmware_version[1]);
		} else {
			firmwareMajor = '';
			firmwareMinor = '';
		}

		sendUnhandled = config.send_unhandled ?? true; // Default is on
	}

	function buildScenarioConfig(): ScenarioConfig {
		const config: ScenarioConfig = {};

		// Drop packets
		if (dropPackets.length > 0) {
			config.drop_packets = {};
			for (const { packetType, rate } of dropPackets) {
				if (packetType && rate) {
					config.drop_packets[packetType] = parseFloat(rate);
				}
			}
		}

		// Response delays
		if (responseDelays.length > 0) {
			config.response_delays = {};
			for (const { packetType, delay } of responseDelays) {
				if (packetType && delay) {
					config.response_delays[packetType] = parseFloat(delay);
				}
			}
		}

		// Parse comma-separated number lists
		if (malformedPackets.trim()) {
			config.malformed_packets = malformedPackets
				.split(',')
				.map((s) => parseInt(s.trim(), 10))
				.filter((n) => !isNaN(n));
		}

		if (invalidFieldValues.trim()) {
			config.invalid_field_values = invalidFieldValues
				.split(',')
				.map((s) => parseInt(s.trim(), 10))
				.filter((n) => !isNaN(n));
		}

		if (partialResponses.trim()) {
			config.partial_responses = partialResponses
				.split(',')
				.map((s) => parseInt(s.trim(), 10))
				.filter((n) => !isNaN(n));
		}

		// Firmware version
		if (firmwareMajor && firmwareMinor) {
			config.firmware_version = [parseInt(firmwareMajor, 10), parseInt(firmwareMinor, 10)];
		}

		// Always include send_unhandled since default is true
		config.send_unhandled = sendUnhandled;

		return config;
	}

	async function handleApply() {
		error = null;
		success = null;
		saving = true;

		try {
			const config = buildScenarioConfig();

			if (activeScope === 'global') {
				await setGlobalScenario(config);
			} else {
				if (!selectedIdentifier) {
					throw new Error('Please select an identifier');
				}
				await setScenario(scopeToApiScope(activeScope), selectedIdentifier, config);
			}

			success = 'Scenario applied successfully';
			setTimeout(() => (success = null), 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to apply scenario';
		} finally {
			saving = false;
		}
	}

	async function handleClear() {
		error = null;
		success = null;
		saving = true;

		try {
			if (activeScope === 'global') {
				await clearGlobalScenario();
			} else {
				if (!selectedIdentifier) {
					throw new Error('Please select an identifier');
				}
				await clearScenario(scopeToApiScope(activeScope), selectedIdentifier);
			}

			loadFromScenario(null);
			success = 'Scenario cleared successfully';
			setTimeout(() => (success = null), 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to clear scenario';
		} finally {
			saving = false;
		}
	}

	function addDropPacket() {
		dropPackets = [...dropPackets, { packetType: '', rate: '1.0' }];
	}

	function removeDropPacket(index: number) {
		dropPackets = dropPackets.filter((_, i) => i !== index);
	}

	function addResponseDelay() {
		responseDelays = [...responseDelays, { packetType: '', delay: '0.5' }];
	}

	function removeResponseDelay(index: number) {
		responseDelays = responseDelays.filter((_, i) => i !== index);
	}

	function clearFirmwareVersion() {
		firmwareMajor = '';
		firmwareMinor = '';
	}

	// Load scenario when scope or identifier changes
	$effect(() => {
		if (activeScope === 'global') {
			loadFromScenario(currentScenario());
		} else if (selectedIdentifier) {
			loadFromScenario(currentScenario());
		} else {
			loadFromScenario(null);
		}
	});

	// Reset identifier when scope changes
	$effect(() => {
		const ids = availableIdentifiers();
		if (activeScope !== 'global' && ids.length > 0 && !ids.includes(selectedIdentifier)) {
			selectedIdentifier = ids[0];
		}
	});
</script>

<div class="card">
	<h2>Scenario Configuration</h2>

	<!-- Scope tabs -->
	<div class="scope-tabs">
		{#each ['global', 'device', 'type', 'location', 'group'] as scope}
			<button
				class="scope-tab"
				class:active={activeScope === scope}
				onclick={() => (activeScope = scope as Scope)}
			>
				{scope.charAt(0).toUpperCase() + scope.slice(1)}
			</button>
		{/each}
	</div>

	<!-- Identifier selector (not for global) -->
	{#if activeScope !== 'global'}
		<div class="form-group" style="margin-top: 12px;">
			<label for="identifier">
				{activeScope.charAt(0).toUpperCase() + activeScope.slice(1)}:
			</label>
			<select id="identifier" bind:value={selectedIdentifier}>
				{#if availableIdentifiers().length === 0}
					<option value="">No {activeScope}s available</option>
				{:else}
					{#each availableIdentifiers() as id}
						<option value={id}>{id}</option>
					{/each}
				{/if}
			</select>
		</div>
	{/if}

	<!-- Scenario form -->
	<div class="scenario-form">
		<!-- Drop Packets -->
		<div class="form-section">
			<div class="section-header">
				<span class="section-title">Drop Packets</span>
				<button type="button" class="btn btn-sm" onclick={addDropPacket}>+ Add</button>
			</div>
			<p class="section-desc">Specify packet types to drop (0.0 = never, 1.0 = always)</p>
			{#each dropPackets as item, i}
				<div class="inline-row">
					<input
						type="text"
						placeholder="Packet type (e.g., 101)"
						bind:value={item.packetType}
						style="width: 140px;"
					/>
					<input
						type="number"
						min="0"
						max="1"
						step="0.1"
						placeholder="Drop rate"
						bind:value={item.rate}
						style="width: 100px;"
					/>
					<button type="button" class="btn btn-delete btn-sm" onclick={() => removeDropPacket(i)}>
						X
					</button>
				</div>
			{/each}
		</div>

		<!-- Response Delays -->
		<div class="form-section">
			<div class="section-header">
				<span class="section-title">Response Delays</span>
				<button type="button" class="btn btn-sm" onclick={addResponseDelay}>+ Add</button>
			</div>
			<p class="section-desc">Add delay (seconds) before responding to packet types</p>
			{#each responseDelays as item, i}
				<div class="inline-row">
					<input
						type="text"
						placeholder="Packet type (e.g., 101)"
						bind:value={item.packetType}
						style="width: 140px;"
					/>
					<input
						type="number"
						min="0"
						step="0.1"
						placeholder="Delay (s)"
						bind:value={item.delay}
						style="width: 100px;"
					/>
					<button type="button" class="btn btn-delete btn-sm" onclick={() => removeResponseDelay(i)}>
						X
					</button>
				</div>
			{/each}
		</div>

		<!-- Malformed Packets -->
		<div class="form-section">
			<label for="malformed" class="section-title">Malformed Packets</label>
			<p class="section-desc">Packet types to send with corrupted payloads (comma-separated)</p>
			<input
				id="malformed"
				type="text"
				placeholder="e.g., 101, 102, 118"
				bind:value={malformedPackets}
			/>
		</div>

		<!-- Invalid Field Values -->
		<div class="form-section">
			<label for="invalid" class="section-title">Invalid Field Values</label>
			<p class="section-desc">Packet types to send with 0xFF bytes (comma-separated)</p>
			<input
				id="invalid"
				type="text"
				placeholder="e.g., 101, 102"
				bind:value={invalidFieldValues}
			/>
		</div>

		<!-- Firmware Version -->
		<div class="form-section">
			<div class="section-header">
				<span class="section-title">Firmware Version Override</span>
				{#if firmwareMajor || firmwareMinor}
					<button type="button" class="btn btn-sm" onclick={clearFirmwareVersion}>Clear</button>
				{/if}
			</div>
			<p class="section-desc">Override reported firmware version (major.minor)</p>
			<div class="inline-row">
				<input
					type="number"
					min="0"
					max="255"
					placeholder="Major"
					bind:value={firmwareMajor}
					style="width: 80px;"
				/>
				<span>.</span>
				<input
					type="number"
					min="0"
					max="255"
					placeholder="Minor"
					bind:value={firmwareMinor}
					style="width: 80px;"
				/>
			</div>
		</div>

		<!-- Partial Responses -->
		<div class="form-section">
			<label for="partial" class="section-title">Partial Responses</label>
			<p class="section-desc">Packet types to send with incomplete data (comma-separated)</p>
			<input
				id="partial"
				type="text"
				placeholder="e.g., 506, 512"
				bind:value={partialResponses}
			/>
		</div>

		<!-- Send Unhandled -->
		<div class="form-section">
			<label class="checkbox-label">
				<input type="checkbox" bind:checked={sendUnhandled} />
				<span>Send Unhandled</span>
			</label>
			<p class="section-desc">Return StateUnhandled for unknown packet types</p>
		</div>
	</div>

	<!-- Status messages -->
	{#if error}
		<p class="message error">{error}</p>
	{/if}
	{#if success}
		<p class="message success">{success}</p>
	{/if}

	<!-- Action buttons -->
	<div class="actions">
		<button class="btn" onclick={handleApply} disabled={saving || (activeScope !== 'global' && !selectedIdentifier)}>
			{saving ? 'Applying...' : 'Apply'}
		</button>
		<button class="btn btn-delete" onclick={handleClear} disabled={saving || (activeScope !== 'global' && !selectedIdentifier)}>
			{saving ? 'Clearing...' : 'Clear'}
		</button>
	</div>
</div>

<style>
	.scope-tabs {
		display: flex;
		gap: 4px;
		border-bottom: 1px solid var(--border-color);
		padding-bottom: 8px;
		margin-bottom: 12px;
	}

	.scope-tab {
		padding: 6px 12px;
		background: transparent;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.85em;
		color: var(--text-muted);
		transition: all 0.15s ease;
	}

	.scope-tab:hover {
		background: var(--bg-hover);
	}

	.scope-tab.active {
		background: var(--accent-primary);
		color: white;
		border-color: var(--accent-primary);
	}

	.scenario-form {
		margin-top: 16px;
	}

	.form-section {
		margin-bottom: 16px;
		padding-bottom: 12px;
		border-bottom: 1px solid var(--border-color);
	}

	.form-section:last-child {
		border-bottom: none;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 4px;
	}

	.section-title {
		font-weight: 500;
		font-size: 0.9em;
	}

	.section-desc {
		font-size: 0.8em;
		color: var(--text-dimmed);
		margin: 4px 0 8px 0;
	}

	.inline-row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 6px;
	}

	.form-section input[type='text'],
	.form-section input[type='number'] {
		padding: 6px 10px;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		background: var(--bg-input);
		color: var(--text-primary);
		font-size: 0.85em;
	}

	.form-section input[type='text'] {
		width: 100%;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 8px;
		cursor: pointer;
		font-weight: 500;
		font-size: 0.9em;
	}

	.checkbox-label input[type='checkbox'] {
		width: 16px;
		height: 16px;
	}

	.message {
		margin: 12px 0;
		padding: 8px 12px;
		border-radius: 4px;
		font-size: 0.85em;
	}

	.message.error {
		background: rgba(255, 100, 100, 0.1);
		color: var(--accent-danger);
	}

	.message.success {
		background: rgba(100, 255, 100, 0.1);
		color: var(--accent-success, #4caf50);
	}

	.actions {
		display: flex;
		gap: 8px;
		margin-top: 16px;
	}
</style>
