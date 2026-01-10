"""Tests for circuit breaker service."""

import pytest

from app.services.circuit_breaker_service import CircuitBreakerService, CircuitState


@pytest.fixture
def circuit_breaker():
    """Create circuit breaker service instance."""
    return CircuitBreakerService(
        failure_threshold=3, recovery_timeout=1, half_open_max_calls=2
    )


@pytest.mark.asyncio
async def test_initial_state_closed(circuit_breaker):
    """Test that circuit breaker starts in closed state."""
    service_name = "test-service"

    allowed = await circuit_breaker.is_call_allowed(service_name)
    assert allowed is True

    breaker = circuit_breaker.get_breaker(service_name)
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_opens_after_failures(circuit_breaker):
    """Test that circuit opens after threshold failures."""
    service_name = "test-service"

    # Record 3 failures
    for _ in range(3):
        await circuit_breaker.record_failure(service_name)

    # Circuit should be open
    breaker = circuit_breaker.get_breaker(service_name)
    assert breaker.state == CircuitState.OPEN

    # Calls should not be allowed
    allowed = await circuit_breaker.is_call_allowed(service_name)
    assert allowed is False


@pytest.mark.asyncio
async def test_success_resets_failures(circuit_breaker):
    """Test that success resets failure count in closed state."""
    service_name = "test-service"

    # Record some failures
    await circuit_breaker.record_failure(service_name)
    await circuit_breaker.record_failure(service_name)

    # Record success
    await circuit_breaker.record_success(service_name)

    # Circuit should still be closed
    breaker = circuit_breaker.get_breaker(service_name)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_half_open_state(circuit_breaker):
    """Test half-open state after recovery timeout."""
    import asyncio

    service_name = "test-service"

    # Open the circuit
    for _ in range(3):
        await circuit_breaker.record_failure(service_name)

    breaker = circuit_breaker.get_breaker(service_name)
    assert breaker.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Next call should transition to half-open
    allowed = await circuit_breaker.is_call_allowed(service_name)
    assert allowed is True
    assert breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_closes_on_success(circuit_breaker):
    """Test that half-open closes after successful calls."""
    import asyncio

    service_name = "test-service"

    # Open the circuit
    for _ in range(3):
        await circuit_breaker.record_failure(service_name)

    # Wait for recovery
    await asyncio.sleep(1.1)

    # Transition to half-open
    await circuit_breaker.is_call_allowed(service_name)

    breaker = circuit_breaker.get_breaker(service_name)
    assert breaker.state == CircuitState.HALF_OPEN

    # Record successful calls
    await circuit_breaker.is_call_allowed(service_name)
    await circuit_breaker.record_success(service_name)
    await circuit_breaker.record_success(service_name)

    # Circuit should close
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_get_all_states(circuit_breaker):
    """Test getting all circuit breaker states."""
    await circuit_breaker.is_call_allowed("service-1")
    await circuit_breaker.is_call_allowed("service-2")

    states = circuit_breaker.get_all_states()

    assert "service-1" in states
    assert "service-2" in states
    assert states["service-1"]["state"] == "closed"
