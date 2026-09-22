# Phase 3 Plan 01: mDNS Candidate Evidence

- **Decision:** provisional
- **Reason:** One or more required platform, packaging, oracle, benchmark or lifecycle gates remain untested.
- **Active work:** 1348.090s / 14400s
- **Input specification:** `ce65e5472a6614bed6cc4fa09069a1de8aea17f486ed03127224d16142285717`

## Candidate ledger

### zeroconf

Execution: `completed`; suitability: `provisional`.

| Criterion | Status | Evidence | Acquisition step |
|---|---|---|---|
| daemon_coexistence | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| direct_address_queries | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| exact_txt_and_family | demonstrated | TXT=[{'fw': '4.200', 'id': 'd073d5000001', 'p': '27', 'tm': '1'}]; A-only=True | — |
| intel_pyapp_first_run | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| legacy_wire | demonstrated | {"a_only": true, "all_cache_flush_clear": true, "client_endpoint": ["192.168.17.244", 50249], "datagram_size": 174, "interface": "192.168.17.244", "lifx_async_version": "7.3.0", "peer": ["192.168.17.244", 5353], "query_id": 48879, "question_count": 1, "record_count": 5, "record_types": ["PTR", "SRV", "A", "TYPE47", "TXT"], "required_records_present": true, "response_id": 48879, "response_received_on_ephemeral_socket": true, "service_port": 53574, "threads_before_close": ["MainThread"], "ttl_valid": true, "ttl_values": [10, 10, 10, 10, 10], "txt_exact": true, "txt_records": [{"fw": "4.200", "id": "d073d5000001", "p": "27", "tm": "1"}], "zeroconf_version": "0.151.3"} | — |
| lifecycle_cleanup | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| macos_multicast | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| mixed_100_benchmark | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| mixed_10_benchmark | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| official_provenance | demonstrated | PyPI JSON resolved latest non-yanked zeroconf 0.151.3 with sdist SHA256 ce6c548e665759b6150cef4db9ab9d7bdd89857e90c513abd6b7340bdd7dbd6a; annotated tag resolves to b7aea22b51d82f2139c9143292e86a361ea6796f. GitHub commits API and a detached exact-SHA fetch verified oracle 48b7efbff59656499373b13ef17e3008d125feb5. | — |
| oracle_discovery | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| packet_boundary | demonstrated | One captured datagram carried record types ['PTR', 'SRV', 'A', 'TYPE47', 'TXT'] and 5 records. | — |
| thread_benchmark | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| ubuntu_multicast | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| wifi_benchmark | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |
| windows_socket_simulation | untested | Not yet reached by the progressive candidate sequence. | Run the named local or exact-head CI probe and merge its receipt. |

## Platform and packaging

PR: not recorded

## Deferred coverage

MDNS-01–09 and MDNS-11 remain pending until a human selects an evidence-valid go route.
