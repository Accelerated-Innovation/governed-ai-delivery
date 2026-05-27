# Observability Port Contract

This document defines the outbound port interface that domain services use to emit observability signals (logs, metrics, traces) without depending on infrastructure libraries.

See also: [TECH_STACK.md](TECH_STACK.md) Section 11 (Observability)

---

## 1. Purpose

The domain layer must remain infrastructure-agnostic. Domain services must not import `pino`, `@opentelemetry/api`, or any observability library directly. Instead, they call methods on an `ObservabilityPort` interface, which is implemented by an adapter.

---

## 2. Port Interface

```typescript
// ports/outbound/ObservabilityPort.ts
export interface ObservabilityPort {
  /**
   * Record a structured domain event.
   * @param event      Event name (e.g., "schema_published", "retry_exhausted")
   * @param level      Log level — "debug" | "info" | "warning" | "error"
   * @param attributes Structured key-value pairs included in the log entry
   */
  recordEvent(
    event: string,
    level?: 'debug' | 'info' | 'warning' | 'error',
    attributes?: Record<string, unknown>
  ): void

  /**
   * Start a trace span around a domain operation.
   * Returns a Disposable-like object — call end() when the operation completes.
   * @param spanName   Span name (e.g., "publish_schema", "retrieve_schema")
   * @param attributes Key-value pairs attached to the span
   */
  startSpan(
    spanName: string,
    attributes?: Record<string, unknown>
  ): { end(): void }

  /**
   * Increment a named counter metric.
   * @param name  Metric name (e.g., "schema_publish_count")
   * @param value Increment amount (default: 1)
   * @param tags  Metric tags for dimension filtering
   */
  incrementCounter(
    name: string,
    value?: number,
    tags?: Record<string, string>
  ): void
}
```

---

## 3. Adapter Implementation

The adapter lives in `adapters/` and implements the port using **pino** + **OpenTelemetry Node SDK**:

```typescript
// adapters/observability/PinoOtelObservabilityAdapter.ts
import pino from 'pino'
import { trace, metrics } from '@opentelemetry/api'

const logger = pino({ name: 'domain' })
const tracer = trace.getTracer('your-service.domain')
const meter  = metrics.getMeter('your-service.domain')

export class PinoOtelObservabilityAdapter implements ObservabilityPort {
  recordEvent(
    event: string,
    level: 'debug' | 'info' | 'warning' | 'error' = 'info',
    attributes: Record<string, unknown> = {}
  ): void {
    const logLevel = level === 'warning' ? 'warn' : level
    logger[logLevel]({ event, ...attributes })
  }

  startSpan(spanName: string, attributes: Record<string, unknown> = {}): { end(): void } {
    const span = tracer.startSpan(spanName)
    Object.entries(attributes).forEach(([k, v]) => span.setAttribute(k, String(v)))
    return {
      end() { span.end() },
    }
  }

  incrementCounter(name: string, value = 1, tags: Record<string, string> = {}): void {
    const counter = meter.createCounter(name)
    counter.add(value, tags)
  }
}
```

Register in the composition root (`app.ts`):

```typescript
import { PinoOtelObservabilityAdapter } from './adapters/observability/PinoOtelObservabilityAdapter.js'

const obs = new PinoOtelObservabilityAdapter()
const userService = new UserService(userRepo, obs)
```

---

## 4. Usage in Domain Services

```typescript
export class SchemaContractService implements SchemaContractServicePort {
  constructor(
    private readonly registry: SchemaRegistryPort,
    private readonly obs: ObservabilityPort
  ) {}

  async publish(schemaId: string, version: number, body: unknown): Promise<void> {
    const span = this.obs.startSpan('publish_schema', { schema_id: schemaId })
    try {
      this.obs.recordEvent('schema_publish_started', 'info', {
        schema_id: schemaId,
        version,
      })

      await this.registry.publish(schemaId, version, body)

      this.obs.recordEvent('schema_published', 'info', {
        schema_id: schemaId,
        version,
      })

      this.obs.incrementCounter('schema_publish_count', 1, { schema_id: schemaId })
    } finally {
      span.end()
    }
  }
}
```

---

## 5. Rules

- Domain services depend on `ObservabilityPort` (the interface), never on the adapter
- The adapter is injected via constructor — never imported directly in domain code
- `recordEvent` must NOT include raw request/response bodies or PII
- Span names should use `verb_noun` format (e.g., `publish_schema`, `retrieve_schema`)
- Counter names should use `snake_case` with a noun suffix (e.g., `schema_publish_count`)
- The port does not expose log formatting — that is the adapter's responsibility

---

## 6. Testing

In unit tests, use a fake that implements `ObservabilityPort`:

```typescript
// __tests__/fakes/FakeObservability.ts
export class FakeObservability implements ObservabilityPort {
  events: Array<{ event: string; level: string; attributes: Record<string, unknown> }> = []
  spans: string[] = []
  counters: Array<{ name: string; value: number }> = []

  recordEvent(
    event: string,
    level: 'debug' | 'info' | 'warning' | 'error' = 'info',
    attributes: Record<string, unknown> = {}
  ): void {
    this.events.push({ event, level, attributes })
  }

  startSpan(spanName: string): { end(): void } {
    this.spans.push(spanName)
    return { end: () => {} }
  }

  incrementCounter(name: string, value = 1): void {
    this.counters.push({ name, value })
  }
}
```

Assert on `fakeObs.events`, `fakeObs.spans`, and `fakeObs.counters` — not on log output.
