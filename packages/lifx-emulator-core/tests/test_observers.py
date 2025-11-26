"""Tests for observer pattern implementation."""

import time

from lifx_emulator.devices.observers import ActivityLogger, NullObserver, PacketEvent


class TestNullObserver:
    """Test NullObserver implementation."""

    def test_null_observer_on_packet_received(self):
        """Test NullObserver on_packet_received does nothing."""
        observer = NullObserver()
        event = PacketEvent(
            timestamp=time.time(),
            direction="rx",
            packet_type=101,
            packet_name="GetStatus",
            addr="127.0.0.1:56700",
            target="d073d5000001",
        )
        # Should not raise any exception
        observer.on_packet_received(event)

    def test_null_observer_on_packet_sent(self):
        """Test NullObserver on_packet_sent does nothing."""
        observer = NullObserver()
        event = PacketEvent(
            timestamp=time.time(),
            direction="tx",
            packet_type=107,
            packet_name="StateStatus",
            addr="127.0.0.1",
            device="d073d5000001",
        )
        # Should not raise any exception
        observer.on_packet_sent(event)

    def test_null_observer_multiple_calls(self):
        """Test NullObserver can handle multiple calls."""
        observer = NullObserver()
        for i in range(10):
            rx_event = PacketEvent(
                timestamp=time.time(),
                direction="rx",
                packet_type=100 + i,
                packet_name=f"Packet{i}",
                addr=f"127.0.0.{i}:56700",
                target="d073d5000001",
            )
            observer.on_packet_received(rx_event)

            tx_event = PacketEvent(
                timestamp=time.time(),
                direction="tx",
                packet_type=100 + i,
                packet_name=f"Response{i}",
                addr="127.0.0.1",
                device="d073d5000001",
            )
            observer.on_packet_sent(tx_event)


class TestActivityLogger:
    """Test ActivityLogger observer implementation."""

    def test_activity_logger_logs_received_packets(self):
        """Test that ActivityLogger logs received packets."""
        logger = ActivityLogger(max_events=100)
        event = PacketEvent(
            timestamp=time.time(),
            direction="rx",
            packet_type=101,
            packet_name="GetStatus",
            addr="127.0.0.1:56700",
            target="d073d5000001",
        )
        logger.on_packet_received(event)

        activity = logger.get_recent_activity()
        assert len(activity) == 1
        assert activity[0]["direction"] == "rx"
        assert activity[0]["packet_type"] == 101
        assert activity[0]["packet_name"] == "GetStatus"
        assert activity[0]["target"] == "d073d5000001"

    def test_activity_logger_logs_sent_packets(self):
        """Test that ActivityLogger logs sent packets."""
        logger = ActivityLogger(max_events=100)
        event = PacketEvent(
            timestamp=time.time(),
            direction="tx",
            packet_type=107,
            packet_name="StateStatus",
            addr="127.0.0.1",
            device="d073d5000001",
        )
        logger.on_packet_sent(event)

        activity = logger.get_recent_activity()
        assert len(activity) == 1
        assert activity[0]["direction"] == "tx"
        assert activity[0]["packet_type"] == 107
        assert activity[0]["packet_name"] == "StateStatus"
        assert activity[0]["device"] == "d073d5000001"

    def test_activity_logger_respects_max_events(self):
        """Test that ActivityLogger respects max_events limit."""
        logger = ActivityLogger(max_events=5)

        for i in range(10):
            event = PacketEvent(
                timestamp=time.time(),
                direction="rx" if i % 2 == 0 else "tx",
                packet_type=100 + i,
                packet_name=f"Packet{i}",
                addr=f"127.0.0.{i}:56700",
                target="d073d5000001" if i % 2 == 0 else None,
                device="d073d5000001" if i % 2 == 1 else None,
            )
            if i % 2 == 0:
                logger.on_packet_received(event)
            else:
                logger.on_packet_sent(event)

        activity = logger.get_recent_activity()
        assert len(activity) == 5  # Should not exceed max_events

    def test_activity_logger_mixed_events(self):
        """Test ActivityLogger with mixed packet events."""
        logger = ActivityLogger(max_events=100)

        # Add some received events
        for i in range(3):
            rx_event = PacketEvent(
                timestamp=time.time(),
                direction="rx",
                packet_type=100 + i,
                packet_name=f"RxPacket{i}",
                addr="127.0.0.1:56700",
                target="d073d5000001",
            )
            logger.on_packet_received(rx_event)

        # Add some sent events
        for i in range(3):
            tx_event = PacketEvent(
                timestamp=time.time(),
                direction="tx",
                packet_type=200 + i,
                packet_name=f"TxPacket{i}",
                addr="127.0.0.1",
                device="d073d5000001",
            )
            logger.on_packet_sent(tx_event)

        activity = logger.get_recent_activity()
        assert len(activity) == 6  # 3 RX + 3 TX

        # Verify we have both types
        rx_count = sum(1 for a in activity if a["direction"] == "rx")
        tx_count = sum(1 for a in activity if a["direction"] == "tx")
        assert rx_count == 3
        assert tx_count == 3
