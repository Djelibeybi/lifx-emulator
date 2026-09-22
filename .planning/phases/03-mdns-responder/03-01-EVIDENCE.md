# Phase 3 Plan 01: mDNS Candidate Evidence

- **Decision:** provisional
- **Reason:** One or more required platform, packaging, oracle, benchmark or lifecycle gates remain untested.
- **Active work:** 3703.753s / 14400s
- **Input specification:** `c36e962ef41e7c1fd5976f45f24574e86249221be6af2cc05b746ae520bcd595`

## Environment

- `darwin/arm64/3.14.7`: `0a21200ab877a4beb36c16b42dc8ceaae71c856cd59244142ffc2e5697069d47`

## Candidate ledger

### zeroconf

Execution: `completed`; suitability: `rejected`.

| Criterion | Status | Evidence | Acquisition step |
|---|---|---|---|
| daemon_coexistence | demonstrated | Identified host daemons: ['mDNSResponder', 'mDNSResponderHelper']. | — |
| direct_address_queries | demonstrated | WiFi A={'complete_datagrams': 2, 'complete_devices': 0, 'complete_discovery_seconds': 0.00297, 'cpu_seconds': 0.001135, 'datagram_count': 3, 'datagram_sizes': [778, 778, 69], 'direct_match': True, 'discovered': 1, 'expected': 1, 'peak_rss': 70729728, 'record_counts': [16, 16, 2], 'record_types': ['A', 'AAAA', 'PTR', 'SRV', 'TXT', 'TYPE47'], 'serials': []}; Thread AAAA={'complete_datagrams': 1, 'complete_devices': 0, 'complete_discovery_seconds': 0.002576, 'cpu_seconds': 0.000535, 'datagram_count': 2, 'datagram_sizes': [778, 84], 'direct_match': True, 'discovered': 1, 'expected': 1, 'peak_rss': 70729728, 'record_counts': [16, 2], 'record_types': ['AAAA', 'PTR', 'SRV', 'TXT', 'TYPE47'], 'serials': []} | — |
| exact_txt_and_family | demonstrated | TXT=[{'fw': '4.200', 'id': 'd073d5000001', 'p': '27', 'tm': '1'}]; A-only=True | — |
| intel_pyapp_first_run | untested | Exact-head CI evidence has not yet been merged. | Collect and merge the exact-head CI artefact for this gate. |
| legacy_wire | demonstrated | {"a_only": true, "all_cache_flush_clear": true, "client_endpoint": ["selected-ipv4", 50249], "datagram_size": 174, "interface": "selected-ipv4", "lifx_async_version": "7.3.0", "peer": ["selected-ipv4", 5353], "query_id": 48879, "question_count": 1, "record_count": 5, "record_types": ["PTR", "SRV", "A", "TYPE47", "TXT"], "required_records_present": true, "response_id": 48879, "response_received_on_ephemeral_socket": true, "service_port": 53574, "threads_before_close": ["MainThread"], "ttl_valid": true, "ttl_values": [10, 10, 10, 10, 10], "txt_exact": true, "txt_records": [{"fw": "4.200", "id": "d073d5000001", "p": "27", "tm": "1"}], "zeroconf_version": "0.151.3"} | — |
| lifecycle_cleanup | demonstrated | threads before=['MainThread']; after=['MainThread']; pending=[] | — |
| macos_multicast | untested | Exact-head CI evidence has not yet been merged. | Collect and merge the exact-head CI artefact for this gate. |
| mixed_100_benchmark | failed | Diagnostic only, not decision-supporting: executed before the mixed-10 rejection was isolated. {"complete_datagrams": 0, "complete_devices": 0, "complete_discovery_seconds": 0.029959, "cpu_seconds": 0.00956, "datagram_count": 12, "datagram_sizes": [1438, 1418, 1438, 1449, 1459, 1420, 1425, 1455, 1449, 1425, 1449, 736], "direct_a": {"complete_datagrams": 0, "complete_devices": 0, "complete_discovery_seconds": 0.001649, "cpu_seconds": 0.000342, "datagram_count": 1, "datagram_sizes": [69], "direct_match": true, "discovered": 1, "expected": 1, "peak_rss": 70729728, "record_counts": [2], "record_types": ["A", "TYPE47"], "serials": []}, "direct_aaaa": {"complete_datagrams": 0, "complete_devices": 0, "complete_discovery_seconds": 0.000675, "cpu_seconds": 0.000235, "datagram_count": 1, "datagram_sizes": [84], "direct_match": true, "discovered": 1, "expected": 1, "peak_rss": 70729728, "record_counts": [2], "record_types": ["AAAA", "TYPE47"], "serials": []}, "direct_match": false, "discovered": 100, "expected": 100, "peak_rss": 70729728, "raw_thread_address": "::1", "record_counts": [52, 51, 41, 42, 43, 40, 41, 43, 42, 42, 42, 21], "record_types": ["A", "AAAA", "PTR", "SRV", "TXT", "TYPE47"], "serials": ["d073d5000000", "d073d5000001", "d073d5000002", "d073d5000003", "d073d5000004", "d073d5000005", "d073d5000006", "d073d5000007", "d073d5000008", "d073d5000009", "d073d500000a", "d073d500000b", "d073d500000c", "d073d500000d", "d073d500000e", "d073d500000f", "d073d5000010", "d073d5000011", "d073d5000012", "d073d5000013", "d073d5000014", "d073d5000015", "d073d5000016", "d073d5000017", "d073d5000018", "d073d5000019", "d073d500001a", "d073d500001b", "d073d500001c", "d073d500001d", "d073d500001e", "d073d500001f", "d073d5000020", "d073d5000021", "d073d5000022", "d073d5000023", "d073d5000024", "d073d5000025", "d073d5000026", "d073d5000027", "d073d5000028", "d073d5000029", "d073d500002a", "d073d500002b", "d073d500002c", "d073d500002d", "d073d500002e", "d073d500002f", "d073d5000030", "d073d5000031", "d073d5000032", "d073d5000033", "d073d5000034", "d073d5000035", "d073d5000036", "d073d5000037", "d073d5000038", "d073d5000039", "d073d500003a", "d073d500003b", "d073d500003c", "d073d500003d", "d073d500003e", "d073d500003f", "d073d5000040", "d073d5000041", "d073d5000042", "d073d5000043", "d073d5000044", "d073d5000045", "d073d5000046", "d073d5000047", "d073d5000048", "d073d5000049", "d073d500004a", "d073d500004b", "d073d500004c", "d073d500004d", "d073d500004e", "d073d500004f", "d073d5000050", "d073d5000051", "d073d5000052", "d073d5000053", "d073d5000054", "d073d5000055", "d073d5000056", "d073d5000057", "d073d5000058", "d073d5000059", "d073d500005a", "d073d500005b", "d073d500005c", "d073d500005d", "d073d500005e", "d073d500005f", "d073d5000060", "d073d5000061", "d073d5000062", "d073d5000063"], "thread": 50, "threads_before": ["MainThread"], "wifi": 50} | — |
| mixed_10_benchmark | failed | {"complete_datagrams": 1, "complete_devices": 9, "complete_discovery_seconds": 0.003217, "cpu_seconds": 0.001767, "datagram_count": 2, "datagram_sizes": [1445, 118], "direct_a": {"complete_datagrams": 0, "complete_devices": 0, "complete_discovery_seconds": 0.003562, "cpu_seconds": 0.000703, "datagram_count": 1, "datagram_sizes": [69], "direct_match": true, "discovered": 1, "expected": 1, "peak_rss": 70729728, "record_counts": [2], "record_types": ["A", "TYPE47"], "serials": []}, "direct_aaaa": {"complete_datagrams": 0, "complete_devices": 0, "complete_discovery_seconds": 0.002276, "cpu_seconds": 0.000501, "datagram_count": 1, "datagram_sizes": [84], "direct_match": true, "discovered": 1, "expected": 1, "peak_rss": 70729728, "record_counts": [2], "record_types": ["AAAA", "TYPE47"], "serials": []}, "direct_match": false, "discovered": 10, "expected": 10, "peak_rss": 70729728, "raw_thread_address": "::1", "record_counts": [48, 2], "record_types": ["A", "AAAA", "PTR", "SRV", "TXT", "TYPE47"], "serials": ["d073d5000000", "d073d5000001", "d073d5000002", "d073d5000003", "d073d5000004", "d073d5000005", "d073d5000006", "d073d5000007", "d073d5000008", "d073d5000009"], "thread": 5, "threads_before": ["MainThread"], "wifi": 5} | — |
| official_provenance | demonstrated | PyPI JSON resolved latest non-yanked zeroconf 0.151.3 with sdist SHA256 ce6c548e665759b6150cef4db9ab9d7bdd89857e90c513abd6b7340bdd7dbd6a; annotated tag resolves to b7aea22b51d82f2139c9143292e86a361ea6796f. GitHub commits API and a detached exact-SHA fetch verified oracle 48b7efbff59656499373b13ef17e3008d125feb5. | — |
| oracle_discovery | demonstrated | Pinned lifx-async public discover_mdns() WiFi result=['d073d5000001'] on selected IPv4; Thread result=['d073d5000002']. | — |
| packet_boundary | demonstrated | One captured datagram carried record types ['PTR', 'SRV', 'A', 'TYPE47', 'TXT'] and 5 records. | — |
| thread_benchmark | demonstrated | {"complete_datagrams": 2, "complete_devices": 1, "complete_discovery_seconds": 0.005193, "cpu_seconds": 0.001363, "datagram_count": 2, "datagram_sizes": [1438, 189], "direct_a": null, "direct_aaaa": {"complete_datagrams": 1, "complete_devices": 0, "complete_discovery_seconds": 0.002576, "cpu_seconds": 0.000535, "datagram_count": 2, "datagram_sizes": [778, 84], "direct_match": true, "discovered": 1, "expected": 1, "peak_rss": 70729728, "record_counts": [16, 2], "record_types": ["AAAA", "PTR", "SRV", "TXT", "TYPE47"], "serials": []}, "direct_match": false, "discovered": 1, "expected": 1, "peak_rss": 70729728, "raw_thread_address": "::1", "record_counts": [29, 5], "record_types": ["AAAA", "PTR", "SRV", "TXT", "TYPE47"], "serials": ["d073d5000000"], "thread": 1, "threads_before": ["MainThread"], "wifi": 0} | — |
| ubuntu_multicast | untested | Exact-head CI evidence has not yet been merged. | Collect and merge the exact-head CI artefact for this gate. |
| wifi_benchmark | demonstrated | {"complete_datagrams": 2, "complete_devices": 1, "complete_discovery_seconds": 0.003965, "cpu_seconds": 0.001754, "datagram_count": 2, "datagram_sizes": [1438, 174], "direct_a": {"complete_datagrams": 2, "complete_devices": 0, "complete_discovery_seconds": 0.00297, "cpu_seconds": 0.001135, "datagram_count": 3, "datagram_sizes": [778, 778, 69], "direct_match": true, "discovered": 1, "expected": 1, "peak_rss": 70729728, "record_counts": [16, 16, 2], "record_types": ["A", "AAAA", "PTR", "SRV", "TXT", "TYPE47"], "serials": []}, "direct_aaaa": null, "direct_match": false, "discovered": 1, "expected": 1, "peak_rss": 70729728, "raw_thread_address": null, "record_counts": [29, 5], "record_types": ["A", "AAAA", "PTR", "SRV", "TXT", "TYPE47"], "serials": ["d073d5000000"], "thread": 0, "threads_before": ["MainThread"], "wifi": 1} | — |
| windows_socket_simulation | simulated | Windows remains identified simulation-only in the initial spike. | — |

### lifx-direct

Execution: `completed`; suitability: `provisional`.

| Criterion | Status | Evidence | Acquisition step |
|---|---|---|---|
| configuration_interface_fit | demonstrated | The materialiser accepts an explicit eligible advertisement set and explicit matching-family addresses without production APIs. | — |
| daemon_coexistence | demonstrated | Identified host daemons: ['mDNSResponder', 'mDNSResponderHelper']. | — |
| direct_address_queries | demonstrated | Direct A and AAAA queries echoed their IDs/questions with one address. | — |
| dynamic_lifecycle_recovery_fit | demonstrated | Four independent responder/server lifecycles closed with no owned tasks or threads remaining. | — |
| exact_txt_and_family | demonstrated | WiFi replies contained A only; Thread replies contained AAAA only; TXT was exactly id/p/fw/tm. | — |
| intel_pyapp_first_run | untested | The direct extension gate has not run. | Run the named local or exact-head CI probe and merge its receipt. |
| legacy_wire | demonstrated | Every response echoed the non-zero ID and question, cleared cache-flush, used TTL 10, and carried exact TXT. | — |
| lifecycle_cleanup | demonstrated | threads before=['MainThread']; after=['MainThread']; pending=[] | — |
| macos_multicast | untested | The direct extension gate has not run. | Run the named local or exact-head CI probe and merge its receipt. |
| malformed_truncated_flood_bounds | demonstrated | Truncated queries raise a bounded ValueError; the 100-device query returned exactly 100 bounded responses. | — |
| mixed_100_benchmark | demonstrated | {"complete_devices": 100, "complete_discovery_seconds": 0.006162, "cpu_seconds": 0.005543, "datagram_count": 100, "datagram_sizes": [270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 270, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282, 282], "direct_queries": {"thread": true, "wifi": true}, "discovered": 100, "expected": 100, "peak_rss": 71499776, "raw_thread_address_class": "loopback-::1", "server_port": 59837, "thread": 50, "wifi": 50, "wire_checks_passed": true} | — |
| mixed_10_benchmark | demonstrated | {"complete_devices": 10, "complete_discovery_seconds": 0.004108, "cpu_seconds": 0.002486, "datagram_count": 10, "datagram_sizes": [270, 270, 270, 270, 270, 282, 282, 282, 282, 282], "direct_queries": {"thread": true, "wifi": true}, "discovered": 10, "expected": 10, "peak_rss": 71499776, "raw_thread_address_class": "loopback-::1", "server_port": 60440, "thread": 5, "wifi": 5, "wire_checks_passed": true} | — |
| official_provenance | demonstrated | Pinned lifx-async 48b7efbff59656499373b13ef17e3008d125feb5 tree b26ce32ae60a65c13709ed4ecd30675f1bce1533; mDNS subtree archive a91c5a8fd4bba00c7d22a98b83a80c75415368ac8b0774c63d33a8af0032874b; overlay 7633bbdd56142fadb9a6bb26aed2f8a5c505261f9df7e6ca68ca71f4da85bad9. | — |
| oracle_discovery | demonstrated | Pinned public oracle results: {'thread': {'address_class': 'reachable-ula-gua', 'expected_serial': 'd073d6000002', 'matched': True, 'matched_serials': ['d073d6000002']}, 'wifi': {'address_class': 'selected-ipv4', 'expected_serial': 'd073d6000001', 'matched': True, 'matched_serials': ['d073d6000001']}}. | — |
| packet_boundary | demonstrated | Each synthetic device produced one isolated complete datagram. | — |
| thread_benchmark | demonstrated | {"complete_devices": 1, "complete_discovery_seconds": 0.000805, "cpu_seconds": 0.000713, "datagram_count": 1, "datagram_sizes": [282], "direct_queries": {"thread": true}, "discovered": 1, "expected": 1, "peak_rss": 71499776, "raw_thread_address_class": "loopback-::1", "server_port": 62374, "thread": 1, "wifi": 0, "wire_checks_passed": true} | — |
| ubuntu_multicast | untested | The direct extension gate has not run. | Run the named local or exact-head CI probe and merge its receipt. |
| wifi_benchmark | demonstrated | {"complete_devices": 1, "complete_discovery_seconds": 0.000743, "cpu_seconds": 0.000664, "datagram_count": 1, "datagram_sizes": [270], "direct_queries": {"wifi": true}, "discovered": 1, "expected": 1, "peak_rss": 71499776, "raw_thread_address_class": null, "server_port": 61090, "thread": 0, "wifi": 1, "wire_checks_passed": true} | — |
| windows_socket_simulation | simulated | Windows remains identified simulation-only in the initial spike. | — |

## Benchmarks

Benchmark measurements are retained in the candidate criteria; post-rejection diagnostics are labelled non-decision-supporting.

## Platform and packaging

PR: https://github.com/Djelibeybi/lifx-emulator/pull/224

## Decision

**provisional** — One or more required platform, packaging, oracle, benchmark or lifecycle gates remain untested.

## Deferred coverage

MDNS-01–09 and MDNS-11 remain pending until a human selects an evidence-valid go route.
