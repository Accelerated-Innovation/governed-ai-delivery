# Observability Port Contract

This document defines the outbound port interface that domain services use to emit observability signals (logs, metrics, traces) without depending on infrastructure libraries.

See also: [TECH_STACK.md](TECH_STACK.md) Section 11 (Observability)

---

## 1. Purpose

The domain layer must remain infrastructure-agnostic. Domain services must not import `Logback`, `OpenTelemetry`, or any observability library directly. Instead, they call methods on an `ObservabilityPort` interface, which is implemented by an adapter.

---

## 2. Port Interface

```java
// ports/outbound/ObservabilityPort.java
import java.io.Closeable;
import java.util.Map;

public interface ObservabilityPort {

    /**
     * Record a structured domain event.
     *
     * @param event      Event name (e.g., "schema_published", "retry_exhausted")
     * @param level      Log level — "debug", "info", "warning", "error"
     * @param attributes Structured key-value pairs included in the log entry
     */
    void recordEvent(String event, String level, Map<String, Object> attributes);

    default void recordEvent(String event) {
        recordEvent(event, "info", Map.of());
    }

    /**
     * Start a trace span around a domain operation.
     *
     * @param spanName   Span name (e.g., "publish_schema", "retrieve_schema")
     * @param attributes Key-value pairs attached to the span
     * @return A Closeable that ends the span when closed
     */
    Closeable startSpan(String spanName, Map<String, Object> attributes);

    default Closeable startSpan(String spanName) {
        return startSpan(spanName, Map.of());
    }

    /**
     * Increment a named counter metric.
     *
     * @param name  Metric name (e.g., "schema_publish_count")
     * @param value Increment amount
     * @param tags  Metric tags for dimension filtering
     */
    void incrementCounter(String name, int value, Map<String, String> tags);

    default void incrementCounter(String name) {
        incrementCounter(name, 1, Map.of());
    }
}
```

---

## 3. Adapter Implementation

The adapter lives in `adapters/` and implements the port using **SLF4J/Logback** + **OpenTelemetry Java API**:

```java
// adapters/observability/Slf4jOtelObservabilityAdapter.java
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.metrics.Meter;
import io.opentelemetry.api.trace.Tracer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class Slf4jOtelObservabilityAdapter implements ObservabilityPort {

    private static final Logger log = LoggerFactory.getLogger("domain.observability");
    private final Tracer tracer = GlobalOpenTelemetry.getTracer("your-service.domain");
    private final Meter meter = GlobalOpenTelemetry.getMeter("your-service.domain");

    @Override
    public void recordEvent(String event, String level, Map<String, Object> attributes) {
        var builder = switch (level) {
            case "debug"   -> log.atDebug();
            case "warning" -> log.atWarn();
            case "error"   -> log.atError();
            default        -> log.atInfo();
        };
        attributes.forEach((k, v) -> builder.addKeyValue(k, String.valueOf(v)));
        builder.log(event);
    }

    @Override
    public Closeable startSpan(String spanName, Map<String, Object> attributes) {
        var span = tracer.spanBuilder(spanName).startSpan();
        attributes.forEach((k, v) -> span.setAttribute(k, String.valueOf(v)));
        var scope = span.makeCurrent();
        return () -> {
            scope.close();
            span.end();
        };
    }

    @Override
    public void incrementCounter(String name, int value, Map<String, String> tags) {
        var counter = meter.counterBuilder(name).build();
        var attributes = io.opentelemetry.api.common.Attributes.builder();
        tags.forEach(attributes::put);
        counter.add(value, attributes.build());
    }
}
```

---

## 4. Usage in Domain Services

```java
public class SchemaContractService implements SchemaContractServicePort {

    private final SchemaRegistryPort registry;
    private final ObservabilityPort obs;

    public SchemaContractService(SchemaRegistryPort registry, ObservabilityPort obs) {
        this.registry = registry;
        this.obs = obs;
    }

    public void publish(String schemaId, int version, JsonNode body) {
        try (var span = obs.startSpan("publish_schema",
                Map.of("schema_id", schemaId))) {

            obs.recordEvent("schema_publish_started", "info",
                Map.of("schema_id", schemaId, "version", version));

            registry.publish(schemaId, version, body);

            obs.recordEvent("schema_published", "info",
                Map.of("schema_id", schemaId, "version", version));

            obs.incrementCounter("schema_publish_count", 1,
                Map.of("schema_id", schemaId));
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

```java
public class FakeObservability implements ObservabilityPort {

    public final List<Map<String, Object>> events = new ArrayList<>();
    public final List<String> spans = new ArrayList<>();
    public final List<String> counters = new ArrayList<>();

    @Override
    public void recordEvent(String event, String level, Map<String, Object> attrs) {
        var entry = new HashMap<>(attrs);
        entry.put("event", event);
        entry.put("level", level);
        events.add(entry);
    }

    @Override
    public Closeable startSpan(String spanName, Map<String, Object> attributes) {
        spans.add(spanName);
        return () -> {};
    }

    @Override
    public void incrementCounter(String name, int value, Map<String, String> tags) {
        counters.add(name);
    }
}
```

Assert on `fakeObs.events`, `fakeObs.spans`, and `fakeObs.counters` — not on log output.
