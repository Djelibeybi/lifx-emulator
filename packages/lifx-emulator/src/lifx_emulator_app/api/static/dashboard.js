/**
 * LIFX Emulator Dashboard
 * Real-time monitoring and device management interface
 */

'use strict';

let updateInterval;

// DOM helper: create element with optional class and text
function createElement(tag, className, textContent) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (textContent !== undefined) el.textContent = textContent;
    return el;
}

// DOM helper: create element with style
function createStyledElement(tag, style, textContent) {
    const el = document.createElement(tag);
    if (style) el.style.cssText = style;
    if (textContent !== undefined) el.textContent = textContent;
    return el;
}

// Convert HSBK to RGB for display
function hsbkToRgb(hsbk) {
    const h = hsbk.hue / 65535;
    const s = hsbk.saturation / 65535;
    const v = hsbk.brightness / 65535;

    let r, g, b;
    const i = Math.floor(h * 6);
    const f = h * 6 - i;
    const p = v * (1 - s);
    const q = v * (1 - f * s);
    const t = v * (1 - (1 - f) * s);

    switch (i % 6) {
        case 0: r = v; g = t; b = p; break;
        case 1: r = q; g = v; b = p; break;
        case 2: r = p; g = v; b = t; break;
        case 3: r = p; g = q; b = v; break;
        case 4: r = t; g = p; b = v; break;
        case 5: r = v; g = p; b = q; break;
    }

    const red = Math.round(r * 255);
    const green = Math.round(g * 255);
    const blue = Math.round(b * 255);
    return `rgb(${red}, ${green}, ${blue})`;
}

function toggleZones(serial) {
    const element = document.getElementById(`zones-${serial}`);
    const toggle = document.getElementById(`zones-toggle-${serial}`);
    if (element && toggle) {
        const isShown = element.classList.toggle('show');
        // Update toggle icon
        toggle.textContent = isShown
            ? toggle.textContent.replace('▸', '▾')
            : toggle.textContent.replace('▾', '▸');
        // Save state to localStorage
        localStorage.setItem(`zones-${serial}`, isShown ? 'show' : 'hide');
    }
}

function toggleMetadata(serial) {
    const element = document.getElementById(`metadata-${serial}`);
    const toggle = document.getElementById(`metadata-toggle-${serial}`);
    if (element && toggle) {
        const isShown = element.classList.toggle('show');
        // Update toggle icon
        toggle.textContent = isShown
            ? toggle.textContent.replace('▸', '▾')
            : toggle.textContent.replace('▾', '▸');
        // Save state to localStorage
        localStorage.setItem(`metadata-${serial}`, isShown ? 'show' : 'hide');
    }
}

function restoreToggleStates(serial) {
    // Restore zones toggle state
    const zonesState = localStorage.getItem(`zones-${serial}`);
    if (zonesState === 'show') {
        const element = document.getElementById(`zones-${serial}`);
        const toggle = document.getElementById(`zones-toggle-${serial}`);
        if (element && toggle) {
            element.classList.add('show');
            toggle.textContent = toggle.textContent.replace('▸', '▾');
        }
    }

    // Restore metadata toggle state
    const metadataState = localStorage.getItem(`metadata-${serial}`);
    if (metadataState === 'show') {
        const element = document.getElementById(`metadata-${serial}`);
        const toggle = document.getElementById(`metadata-toggle-${serial}`);
        if (element && toggle) {
            element.classList.add('show');
            toggle.textContent = toggle.textContent.replace('▸', '▾');
        }
    }
}

// Create a stat display element
function createStatElement(label, value) {
    const stat = createElement('div', 'stat');
    stat.appendChild(createElement('span', 'stat-label', label));
    stat.appendChild(createElement('span', 'stat-value', String(value)));
    return stat;
}

async function fetchStats() {
    const statsContainer = document.getElementById('stats');
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const stats = await response.json();

        const uptimeValue = Math.floor(stats.uptime_seconds);

        // Clear and rebuild stats using DOM APIs
        statsContainer.textContent = '';
        statsContainer.appendChild(createStatElement('Uptime', uptimeValue + 's'));
        statsContainer.appendChild(createStatElement('Devices', stats.device_count));
        statsContainer.appendChild(createStatElement('Packets RX', stats.packets_received));
        statsContainer.appendChild(createStatElement('Packets TX', stats.packets_sent));
        statsContainer.appendChild(createStatElement('Errors', stats.error_count));

        // Show/hide activity log based on server configuration
        const activityCard = document.getElementById('activity-card');
        if (activityCard) {
            const displayValue = (
                stats.activity_enabled ? 'block' : 'none'
            );
            activityCard.style.display = displayValue;
        }

        return stats.activity_enabled;
    } catch (error) {
        console.error('Failed to fetch stats:', error);

        // Clear and show error using DOM APIs
        statsContainer.textContent = '';
        const stat = createElement('div', 'stat');
        const label = createElement('span', 'stat-label', 'Error loading stats');
        label.style.color = '#d32f2f';
        stat.appendChild(label);
        stat.appendChild(createElement('span', 'stat-value', error.message));
        statsContainer.appendChild(stat);
        return false;
    }
}

// Create a metadata row element
function createMetadataRow(label, value, valueStyle) {
    const row = createElement('div', 'metadata-row');
    row.appendChild(createElement('span', 'metadata-label', label));
    const valueEl = createElement('span', 'metadata-value', value);
    if (valueStyle) valueEl.style.cssText = valueStyle;
    row.appendChild(valueEl);
    return row;
}

// Create a badge element
function createBadge(text, badgeClass) {
    return createElement('span', `badge ${badgeClass}`, text);
}

// Create zone segment element for multizone strips
function createZoneSegment(color) {
    const segment = createElement('div', 'zone-segment');
    segment.style.background = hsbkToRgb(color);
    return segment;
}

// Create tile zone element for matrix devices
function createTileZone(color) {
    const zone = createElement('div', 'tile-zone');
    zone.style.background = hsbkToRgb(color);
    return zone;
}

// Build metadata section for a device
function buildMetadataSection(dev) {
    const container = document.createDocumentFragment();

    // Metadata toggle
    const toggle = createElement('div', 'metadata-toggle', '▸ Show metadata');
    toggle.id = `metadata-toggle-${dev.serial}`;
    toggle.addEventListener('click', () => toggleMetadata(dev.serial));
    container.appendChild(toggle);

    // Metadata display
    const display = createElement('div', 'metadata-display');
    display.id = `metadata-${dev.serial}`;

    const uptimeSeconds = Math.floor(dev.uptime_ns / 1e9);
    const firmware = `${dev.version_major}.${dev.version_minor}`;

    // Build capabilities text
    const capabilitiesMetadata = [];
    if (dev.has_color) capabilitiesMetadata.push('Color');
    if (dev.has_infrared) capabilitiesMetadata.push('Infrared');
    if (dev.has_multizone) {
        capabilitiesMetadata.push(`Multizone (${dev.zone_count} zones)`);
    }
    if (dev.has_extended_multizone) {
        capabilitiesMetadata.push('Extended Multizone');
    }
    if (dev.has_matrix) {
        capabilitiesMetadata.push(`Matrix (${dev.tile_count} tiles)`);
    }
    if (dev.has_hev) capabilitiesMetadata.push('HEV/Clean');
    const capabilitiesText = capabilitiesMetadata.join(', ') || 'None';

    display.appendChild(createMetadataRow('Firmware:', firmware));
    display.appendChild(createMetadataRow('Vendor:', String(dev.vendor)));
    display.appendChild(createMetadataRow('Product:', String(dev.product)));
    display.appendChild(
        createMetadataRow('Capabilities:', capabilitiesText, 'color: #4a9eff;')
    );
    display.appendChild(createMetadataRow('Group:', dev.group_label));
    display.appendChild(createMetadataRow('Location:', dev.location_label));
    display.appendChild(createMetadataRow('Uptime:', `${uptimeSeconds}s`));
    display.appendChild(
        createMetadataRow('WiFi Signal:', `${dev.wifi_signal.toFixed(1)} dBm`)
    );

    container.appendChild(display);
    return container;
}

// Build zones/tiles section for a device
function buildZonesSection(dev) {
    const container = document.createDocumentFragment();

    if (dev.has_multizone && dev.zone_colors && dev.zone_colors.length > 0) {
        // Multizone strip display
        const toggle = createElement(
            'div', 'zones-toggle',
            `▸ Show zones (${dev.zone_colors.length})`
        );
        toggle.id = `zones-toggle-${dev.serial}`;
        toggle.addEventListener('click', () => toggleZones(dev.serial));
        container.appendChild(toggle);

        const display = createElement('div', 'zones-display');
        display.id = `zones-${dev.serial}`;
        const strip = createElement('div', 'zone-strip');
        dev.zone_colors.forEach(color => {
            strip.appendChild(createZoneSegment(color));
        });
        display.appendChild(strip);
        container.appendChild(display);

    } else if (dev.has_matrix && dev.tile_devices &&
               dev.tile_devices.length > 0) {
        // Tile matrix display
        const toggle = createElement(
            'div', 'zones-toggle',
            `▸ Show tiles (${dev.tile_devices.length})`
        );
        toggle.id = `zones-toggle-${dev.serial}`;
        toggle.addEventListener('click', () => toggleZones(dev.serial));
        container.appendChild(toggle);

        const display = createElement('div', 'zones-display');
        display.id = `zones-${dev.serial}`;
        const tilesContainer = createElement('div', 'tiles-container');

        dev.tile_devices.forEach((tile, tileIndex) => {
            const tileItem = createElement('div', 'tile-item');

            // Tile label
            const label = createStyledElement(
                'div',
                'font-size: 0.7em; color: #666; margin-bottom: 2px; text-align: center;',
                `T${tileIndex + 1}`
            );
            tileItem.appendChild(label);

            if (!tile.colors || tile.colors.length === 0) {
                tileItem.appendChild(
                    createStyledElement('div', 'color: #666;', 'No color data')
                );
            } else {
                const width = tile.width || 8;
                const height = tile.height || 8;
                const totalZones = width * height;

                const grid = createElement('div', 'tile-grid');
                grid.style.gridTemplateColumns = `repeat(${width}, 8px)`;

                tile.colors.slice(0, totalZones).forEach(color => {
                    grid.appendChild(createTileZone(color));
                });
                tileItem.appendChild(grid);
            }
            tilesContainer.appendChild(tileItem);
        });

        display.appendChild(tilesContainer);
        container.appendChild(display);

    } else if (dev.has_color && dev.color) {
        // Single color swatch
        const wrapper = createStyledElement('div', 'margin-top: 4px;');
        const swatch = createElement('span', 'color-swatch');
        swatch.style.background = hsbkToRgb(dev.color);
        wrapper.appendChild(swatch);
        wrapper.appendChild(
            createStyledElement('span', 'color: #888; font-size: 0.75em;', 'Current color')
        );
        container.appendChild(wrapper);
    }

    return container;
}

// Build a complete device card element
function buildDeviceCard(dev) {
    const device = createElement('div', 'device');

    // Device header
    const header = createElement('div', 'device-header');
    const headerInfo = createElement('div');
    headerInfo.appendChild(createElement('div', 'device-serial', dev.serial));
    headerInfo.appendChild(createElement('div', 'device-label', dev.label));
    header.appendChild(headerInfo);

    const deleteBtn = createElement('button', 'btn btn-delete', 'Del');
    deleteBtn.addEventListener('click', () => deleteDevice(dev.serial));
    header.appendChild(deleteBtn);
    device.appendChild(header);

    // Badges section
    const badgesDiv = createElement('div');

    // Power badge
    const powerClass = dev.power_level > 0 ? 'badge-power-on' : 'badge-power-off';
    const powerText = dev.power_level > 0 ? 'ON' : 'OFF';
    badgesDiv.appendChild(createBadge(powerText, powerClass));

    // Product badge
    badgesDiv.appendChild(createBadge(`P${dev.product}`, 'badge-capability'));

    // Capability badges
    if (dev.has_color) {
        badgesDiv.appendChild(createBadge('color', 'badge-capability'));
    }
    if (dev.has_infrared) {
        badgesDiv.appendChild(createBadge('IR', 'badge-capability'));
    }
    if (dev.has_extended_multizone) {
        badgesDiv.appendChild(
            createBadge(`extended-mz×${dev.zone_count}`, 'badge-extended-mz')
        );
    } else if (dev.has_multizone) {
        badgesDiv.appendChild(
            createBadge(`multizone×${dev.zone_count}`, 'badge-capability')
        );
    }
    if (dev.has_matrix) {
        badgesDiv.appendChild(
            createBadge(`matrix×${dev.tile_count}`, 'badge-capability')
        );
    }
    if (dev.has_hev) {
        badgesDiv.appendChild(createBadge('HEV', 'badge-capability'));
    }

    device.appendChild(badgesDiv);

    // Metadata section
    device.appendChild(buildMetadataSection(dev));

    // Zones section
    device.appendChild(buildZonesSection(dev));

    return device;
}

async function fetchDevices() {
    const devicesContainer = document.getElementById('devices');
    try {
        const response = await fetch('/api/devices');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const devices = await response.json();

        document.getElementById('device-count').textContent = devices.length;

        // Clear container
        devicesContainer.textContent = '';

        if (devices.length === 0) {
            devicesContainer.appendChild(
                createElement('div', 'no-devices', 'No devices emulated')
            );
            return;
        }

        // Build device cards using DOM APIs
        devices.forEach(dev => {
            devicesContainer.appendChild(buildDeviceCard(dev));
        });

        // Restore toggle states for all devices
        devices.forEach(dev => restoreToggleStates(dev.serial));
    } catch (error) {
        console.error('Failed to fetch devices:', error);

        // Clear and show error using DOM APIs
        devicesContainer.textContent = '';
        const errorDiv = createElement('div', 'no-devices', `Error loading devices: ${error.message}`);
        errorDiv.style.color = '#d32f2f';
        devicesContainer.appendChild(errorDiv);
    }
}

// Build an activity item element
function buildActivityItem(act) {
    const item = createElement('div', 'activity-item');

    const timestamp = act.timestamp * 1000;
    const time = new Date(timestamp).toLocaleTimeString();
    item.appendChild(createElement('span', 'activity-time', time));

    const isRx = act.direction === 'rx';
    const dirClass = isRx ? 'activity-rx' : 'activity-tx';
    const dirLabel = isRx ? 'RX' : 'TX';
    item.appendChild(createElement('span', dirClass, dirLabel));

    item.appendChild(createElement('span', 'activity-packet', act.packet_name));

    const device = act.device || act.target || 'N/A';
    item.appendChild(createElement('span', 'device-serial', device));

    item.appendChild(createStyledElement('span', 'color: #666', act.addr));

    return item;
}

async function fetchActivity() {
    const logElement = document.getElementById('activity-log');
    try {
        const response = await fetch('/api/activity');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const activities = await response.json();

        // Clear container
        logElement.textContent = '';

        if (activities.length === 0) {
            logElement.appendChild(
                createStyledElement('div', 'color: #666', 'No activity yet')
            );
            return;
        }

        // Build activity items using DOM APIs (reversed order)
        activities.slice().reverse().forEach(act => {
            logElement.appendChild(buildActivityItem(act));
        });
    } catch (error) {
        console.error('Failed to fetch activity:', error);

        // Clear and show error using DOM APIs
        logElement.textContent = '';
        const errorDiv = createElement('div', null, `Error loading activity: ${error.message}`);
        errorDiv.style.color = '#d32f2f';
        logElement.appendChild(errorDiv);
    }
}

async function deleteDevice(serial) {
    if (!confirm(`Delete device ${serial}?`)) return;

    const response = await fetch(`/api/devices/${serial}`, {
        method: 'DELETE'
    });

    if (response.ok) {
        await updateAll();
    } else {
        alert('Failed to delete device');
    }
}

async function removeAllDevices() {
    const deviceCount = document.getElementById('device-count').textContent;
    if (deviceCount === '0') {
        alert('No devices to remove');
        return;
    }

    const line1 = (
        `Remove all ${deviceCount} device(s) from the server?\n\n`
    );
    const line2 = (
        'This will stop all devices from ' +
        'responding to LIFX protocol packets, '
    );
    const line3 = 'but will not delete persistent storage.';
    const confirmMsg = line1 + line2 + line3;
    if (!confirm(confirmMsg)) return;

    const response = await fetch('/api/devices', {
        method: 'DELETE'
    });

    if (response.ok) {
        const result = await response.json();
        alert(result.message);
        await updateAll();
    } else {
        alert('Failed to remove all devices');
    }
}

async function fetchProducts() {
    const select = document.getElementById('product-id');
    try {
        const response = await fetch('/api/products');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const products = await response.json();

        select.textContent = '';
        products.forEach(p => {
            const option = document.createElement('option');
            option.value = p.pid;
            option.textContent = `${p.pid} - ${p.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to fetch products:', error);
        select.textContent = '';
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Error loading products';
        select.appendChild(option);
    }
}

async function updateAll() {
    const activityEnabled = await fetchStats();
    const tasks = [fetchDevices()];
    if (activityEnabled) {
        tasks.push(fetchActivity());
    }
    await Promise.all(tasks);
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Set up add device form
    const addDeviceForm = document.getElementById('add-device-form');
    addDeviceForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const productId = parseInt(document.getElementById('product-id').value);

        const response = await fetch('/api/devices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ product_id: productId })
        });

        if (response.ok) {
            await updateAll();
        } else {
            const error = await response.json();
            alert(`Failed to create device: ${error.detail}`);
        }
    });

    // Load product list (one-time) and initial data
    fetchProducts();
    updateAll();

    // Auto-refresh every 2 seconds
    updateInterval = setInterval(updateAll, 2000);
});
