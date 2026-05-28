# Observability Port Contract

This document defines the outbound port interface that domain services use to emit observability signals (logs, metrics, traces) without depending on infrastructure libraries.

See also: [TECH_STACK.md](TECH_STACK.md) Section 11 (Observability)

---

## 1. Purpose

The domain layer must remain infrastructure-agnostic. Domain services must not import `go.uber.org/zap`, `go.opentelemetry.io/otel`, or any observability library directly. Instead, they call methods on an `ObservabilityPort` interface, which is implemented by an adapter.

---

## 2. Port Interface

```go
// internal/ports/observability_port.go
package ports

import "context"

// Span is returned by StartSpan and must be ended when the operation completes.
type Span interface {
    End()
}

// ObservabilityPort is the outbound port for domain observability signals.
type ObservabilityPort interface {
    // RecordEvent records a structured domain event.
    // event:      Event name (e.g., "schema_published", "retry_exhausted")
    // level:      Log level — "debug", "info", "warning", "error"
    // attributes: Structured key-value pairs included in the log entry
    RecordEvent(ctx context.Context, event, level string, attributes map[string]any)

    // StartSpan starts a trace span around a domain operation.
    // Returns a Span that must be ended via span.End() when the operation completes.
    // spanName:   Span name (e.g., "publish_schema", "retrieve_schema")
    // attributes: Key-value pairs attached to the span
    StartSpan(ctx context.Context, spanName string, attributes map[string]any) (context.Context, Span)

    // IncrementCounter increments a named counter metric.
    // name:  Metric name (e.g., "schema_publish_count")
    // value: Increment amount
    // tags:  Metric tags for dimension filtering
    IncrementCounter(name string, value int, tags map[string]string)
}
```

---

## 3. Adapter Implementation

The adapter lives in `internal/adapters/` and implements the port using **zap** + **OpenTelemetry Go SDK**:

```go
// internal/adapters/observability/zap_otel_adapter.go
package observability

import (
    "context"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/metric"
    "go.opentelemetry.io/otel/trace"
    "go.uber.org/zap"

    "yourmodule/internal/ports"
)

type ZapOtelObservabilityAdapter struct {
    logger *zap.Logger
    tracer trace.Tracer
    meter  metric.Meter
}

func NewZapOtelObservabilityAdapter(logger *zap.Logger) *ZapOtelObservabilityAdapter {
    return &ZapOtelObservabilityAdapter{
        logger: logger,
        tracer: otel.Tracer("your-service.domain"),
        meter:  otel.Meter("your-service.domain"),
    }
}

func (a *ZapOtelObservabilityAdapter) RecordEvent(
    ctx context.Context, event, level string, attributes map[string]any,
) {
    fields := make([]zap.Field, 0, len(attributes)+1)
    fields = append(fields, zap.String("event", event))
    for k, v := range attributes {
        fields = append(fields, zap.Any(k, v))
    }
    switch level {
    case "debug":
        a.logger.Debug(event, fields...)
    case "warning":
        a.logger.Warn(event, fields...)
    case "error":
        a.logger.Error(event, fields...)
    default:
        a.logger.Info(event, fields...)
    }
}

type otelSpan struct{ span trace.Span }

func (s *otelSpan) End() { s.span.End() }

func (a *ZapOtelObservabilityAdapter) StartSpan(
    ctx context.Context, spanName string, attributes map[string]any,
) (context.Context, ports.Span) {
    attrs := make([]attribute.KeyValue, 0, len(attributes))
    for k, v := range attributes {
        attrs = append(attrs, attribute.String(k, fmt.Sprintf("%v", v)))
    }
    ctx, span := a.tracer.Start(ctx, spanName, trace.WithAttributes(attrs...))
    return ctx, &otelSpan{span: span}
}

func (a *ZapOtelObservabilityAdapter) IncrementCounter(
    name string, value int, tags map[string]string,
) {
    counter, _ := a.meter.Int64Counter(name)
    attrs := make([]attribute.KeyValue, 0, len(tags))
    for k, v := range tags {
        attrs = append(attrs, attribute.String(k, v))
    }
    counter.Add(context.Background(), int64(value), metric.WithAttributes(attrs...))
}
```

---

## 4. Usage in Domain Services

```go
// internal/domain/services/schema_contract_service.go
type SchemaContractService struct {
    registry ports.SchemaRegistryPort
    obs      ports.ObservabilityPort
}

func (s *SchemaContractService) Publish(
    ctx context.Context, schemaID string, version int, body any,
) error {
    ctx, span := s.obs.StartSpan(ctx, "publish_schema",
        map[string]any{"schema_id": schemaID})
    defer span.End()

    s.obs.RecordEvent(ctx, "schema_publish_started", "info",
        map[string]any{"schema_id": schemaID, "version": version})

    if err := s.registry.Publish(ctx, schemaID, version, body); err != nil {
        return fmt.Errorf("publishing schema: %w", err)
    }

    s.obs.RecordEvent(ctx, "schema_published", "info",
        map[string]any{"schema_id": schemaID, "version": version})

    s.obs.IncrementCounter("schema_publish_count", 1,
        map[string]string{"schema_id": schemaID})

    return nil
}
```

---

## 5. Rules

- Domain services depend on `ObservabilityPort` (the interface), never on the adapter
- The adapter is injected via constructor — never imported directly in domain code
- `RecordEvent` must NOT include raw request/response bodies or PII
- Span names should use `verb_noun` format (e.g., `publish_schema`, `retrieve_schema`)
- Counter names should use `snake_case` with a noun suffix (e.g., `schema_publish_count`)
- The port does not expose log formatting — that is the adapter's responsibility

---

## 6. Testing

In unit tests, use a fake that implements `ObservabilityPort`:

```go
// internal/testhelpers/fake_observability.go
type FakeObservability struct {
    Events   []map[string]any
    Spans    []string
    Counters []string
}

type noopSpan struct{}
func (s *noopSpan) End() {}

func (f *FakeObservability) RecordEvent(
    ctx context.Context, event, level string, attributes map[string]any,
) {
    entry := map[string]any{"event": event, "level": level}
    for k, v := range attributes {
        entry[k] = v
    }
    f.Events = append(f.Events, entry)
}

func (f *FakeObservability) StartSpan(
    ctx context.Context, spanName string, attributes map[string]any,
) (context.Context, ports.Span) {
    f.Spans = append(f.Spans, spanName)
    return ctx, &noopSpan{}
}

func (f *FakeObservability) IncrementCounter(
    name string, value int, tags map[string]string,
) {
    f.Counters = append(f.Counters, name)
}
```

Assert on `fakeObs.Events`, `fakeObs.Spans`, and `fakeObs.Counters` — not on log output.
