"""Tests for handler registry functionality."""

import pytest

from lifx_emulator.handlers.device_handlers import GetPowerHandler, GetServiceHandler
from lifx_emulator.handlers.light_handlers import SetColorHandler
from lifx_emulator.handlers.registry import HandlerRegistry


@pytest.fixture
def registry():
    """Create a fresh handler registry for each test."""
    return HandlerRegistry()


class TestHandlerRegistration:
    """Test handler registration and retrieval."""

    def test_register_handler(self, registry):
        """Test registering a single handler."""
        registry.register(GetServiceHandler)
        assert registry.has_handler(GetServiceHandler.PKT_TYPE)

    def test_register_multiple_handlers(self, registry):
        """Test registering multiple handlers."""
        handlers = [GetServiceHandler, SetColorHandler]
        for handler in handlers:
            registry.register(handler)

        for handler in handlers:
            assert registry.has_handler(handler.PKT_TYPE)

    def test_has_handler_returns_false_for_unregistered(self, registry):
        """Test has_handler returns False for unregistered packet types."""
        assert not registry.has_handler(9999)

    def test_get_handler(self, registry):
        """Test retrieving a registered handler."""
        registry.register(GetServiceHandler)
        handler = registry.get_handler(GetServiceHandler.PKT_TYPE)
        assert handler is GetServiceHandler

    def test_get_handler_returns_none_for_unregistered(self, registry):
        """Test get_handler returns None for unregistered types."""
        handler = registry.get_handler(9999)
        assert handler is None

    def test_registry_length(self, registry):
        """Test __len__ returns handler count."""
        assert len(registry) == 0
        registry.register(GetServiceHandler)
        assert len(registry) == 1
        registry.register(SetColorHandler)
        assert len(registry) == 2

    def test_list_handlers(self, registry):
        """Test list_handlers returns all registered handlers."""
        registry.register(GetServiceHandler)
        registry.register(SetColorHandler)

        handlers = registry.list_handlers()
        # list_handlers returns list of (pkt_type, handler_name) tuples
        pkt_types = [h[0] for h in handlers]
        assert GetServiceHandler.PKT_TYPE in pkt_types
        assert SetColorHandler.PKT_TYPE in pkt_types
        assert len(handlers) == 2

    def test_registry_repr(self, registry):
        """Test __repr__ provides useful string representation."""
        registry.register(GetServiceHandler)
        registry.register(SetColorHandler)

        repr_str = repr(registry)
        assert "HandlerRegistry" in repr_str
        assert "2" in repr_str or "handlers" in repr_str.lower()

    def test_register_handler_without_pkt_type_attribute(self, registry):
        """Test registering a handler without PKT_TYPE raises error."""

        class BadHandler:
            pass

        # When a handler doesn't have PKT_TYPE, registration should fail
        with pytest.raises(ValueError, match="missing PKT_TYPE"):
            registry.register(BadHandler)  # type: ignore

    def test_handler_replacement(self, registry):
        """Test that replacing a handler updates the registry."""
        registry.register(GetServiceHandler)
        assert registry.get_handler(GetServiceHandler.PKT_TYPE) is GetServiceHandler

        # Register the same handler again - should just update
        registry.register(GetServiceHandler)
        assert registry.get_handler(GetServiceHandler.PKT_TYPE) is GetServiceHandler
        assert len(registry) == 1  # Should still have only 1 handler

    def test_register_multiple_calls(self, registry):
        """Test registering multiple handlers in sequence."""
        for handler in [GetServiceHandler, GetPowerHandler, SetColorHandler]:
            registry.register(handler)
            assert registry.has_handler(handler.PKT_TYPE)

        assert len(registry) == 3
