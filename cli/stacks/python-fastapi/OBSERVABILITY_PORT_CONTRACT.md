# Observability Port Contract

This document defines the outbound port interface that domain services use to emit observability signals (logs, metrics, traces) without depending on infrastructure libraries.

See also: [TECH_STACK.md](TECH_STACK.md) Section 11 (Observability)

---

## 1. Purpose

The domain layer must remain infrastructure-agnostic. Domain services must not import `structlog`, `opentelemetry`, or any observability library directly. Instead, they call methods on an `ObservabilityPort` interface, which is implemented by an adapter.

---

## 2. Port Interface

```python
from typing import Any, Protocol
from contextlib import contextmanager

class ObservabilityPort(Protocol):
    """Outbound port for domain observability signals."""

    def record_event(
        self,
        event: str,
        *,
        level: str = "info",
        **attributes: Any,
    ) -> None:
        """Record a structured domain event.

        Args:
            event: Event name (e.g., "schema_published", "retry_exhausted")
            level: Log level — "debug", "info", "warning", "error"
            **attributes: Structured key-value pairs included in the log entry
        """
        ...

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ):
        """Start a trace span around a domain operation.

        Args:
            name: Span name (e.g., "publish_schema", "retrieve_schema")
            attributes: Key-value pairs attached to the span

        Yields:
            A span context (implementation-defined). Domain code should not
            inspect the yielded value — it exists for adapter use.
        """
        ...

    def increment_counter(
        self,
        name: str,
        value: int = 1,
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment a named counter metric.

        Args:
            name: Metric name (e.g., "schema_publish_count")
            value: Increment amount
            tags: Metric tags for dimension filtering
        """
        ...
```

---

## 3. Adapter Implementation

The adapter lives in `adapters/` and implements the port using `structlog` + OpenTelemetry:

```python
import structlog
from opentelemetry import trace
from opentelemetry.metrics import get_meter

class StructlogOtelObservabilityAdapter:
    """Implements ObservabilityPort using structlog and OpenTelemetry."""

    def __init__(self) -> None:
        self._logger = structlog.get_logger()
        self._tracer = trace.get_tracer(__name__)
        self._meter = get_meter(__name__)

    def record_event(self, event: str, *, level: str = "info", **attributes):
        log_method = getattr(self._logger, level, self._logger.info)
        log_method(event, **attributes)

    @contextmanager
    def start_span(self, name: str, *, attributes: dict | None = None):
        with self._tracer.start_as_current_span(name, attributes=attributes or {}) as span:
            yield span

    def increment_counter(self, name: str, value: int = 1, *, tags: dict | None = None):
        counter = self._meter.create_counter(name)
        counter.add(value, attributes=tags or {})
```

---

## 4. Usage in Domain Services

```python
class SchemaContractService:
    def __init__(
        self,
        registry: SchemaRegistryPort,
        observability: ObservabilityPort,
    ) -> None:
        self._registry = registry
        self._obs = observability

    def publish(self, schema_id: str, version: int, body: dict) -> None:
        with self._obs.start_span("publish_schema", attributes={"schema_id": schema_id}):
            self._obs.record_event("schema_publish_started", schema_id=schema_id, version=version)
            self._registry.publish(schema_id, version, body)
            self._obs.record_event("schema_published", schema_id=schema_id, version=version)
            self._obs.increment_counter("schema_publish_count", tags={"schema_id": schema_id})
```

---

## 5. Rules

- Domain services depend on `ObservabilityPort` (the protocol), never on the adapter
- The adapter is injected via constructor — never imported directly in domain code
- `record_event` must NOT include raw request/response bodies or PII
- Span names should be verb_noun format (e.g., `publish_schema`, `retrieve_schema`)
- Counter names should use snake_case with a noun suffix (e.g., `schema_publish_count`)
- The port does not expose log formatting — that is the adapter's responsibility

---

## 6. Testing

In unit tests, use a stub or mock that implements `ObservabilityPort`:

```python
class FakeObservability:
    def __init__(self):
        self.events = []
        self.spans = []
        self.counters = []

    def record_event(self, event, *, level="info", **attributes):
        self.events.append({"event": event, "level": level, **attributes})

    @contextmanager
    def start_span(self, name, *, attributes=None):
        self.spans.append({"name": name, "attributes": attributes or {}})
        yield None

    def increment_counter(self, name, value=1, *, tags=None):
        self.counters.append({"name": name, "value": value, "tags": tags or {}})
```

Assert on `fake_obs.events`, `fake_obs.spans`, and `fake_obs.counters` — not on log output.
