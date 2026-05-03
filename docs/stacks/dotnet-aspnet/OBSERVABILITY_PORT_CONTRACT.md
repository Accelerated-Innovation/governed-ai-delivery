# Observability Port Contract

This document defines the outbound port interface that domain services use to emit observability signals (logs, metrics, traces) without depending on infrastructure libraries.

See also: [TECH_STACK.md](TECH_STACK.md) Section 11 (Observability)

---

## 1. Purpose

The domain layer must remain infrastructure-agnostic. Domain services must not import `Serilog`, `OpenTelemetry`, or any observability library directly. Instead, they call methods on an `IObservabilityPort` interface, which is implemented by an adapter.

---

## 2. Port Interface

```csharp
// Ports/Outbound/IObservabilityPort.cs
public interface IObservabilityPort
{
    /// <summary>
    /// Record a structured domain event.
    /// </summary>
    /// <param name="eventName">Event name (e.g., "schema_published", "retry_exhausted")</param>
    /// <param name="level">Log level — "debug", "info", "warning", "error"</param>
    /// <param name="attributes">Structured key-value pairs included in the log entry</param>
    void RecordEvent(string eventName, string level = "info",
        IReadOnlyDictionary<string, object>? attributes = null);

    /// <summary>
    /// Start a trace span around a domain operation.
    /// </summary>
    /// <param name="spanName">Span name (e.g., "publish_schema", "retrieve_schema")</param>
    /// <param name="attributes">Key-value pairs attached to the span</param>
    IDisposable StartSpan(string spanName,
        IReadOnlyDictionary<string, object>? attributes = null);

    /// <summary>
    /// Increment a named counter metric.
    /// </summary>
    /// <param name="name">Metric name (e.g., "schema_publish_count")</param>
    /// <param name="value">Increment amount</param>
    /// <param name="tags">Metric tags for dimension filtering</param>
    void IncrementCounter(string name, int value = 1,
        IReadOnlyDictionary<string, string>? tags = null);
}
```

---

## 3. Adapter Implementation

The adapter lives in `Adapters/` and implements the port using **Serilog** + **OpenTelemetry .NET SDK**:

```csharp
// Adapters/Observability/SerilogOtelObservabilityAdapter.cs
using Serilog;
using System.Diagnostics;
using System.Diagnostics.Metrics;

public sealed class SerilogOtelObservabilityAdapter : IObservabilityPort
{
    private static readonly ActivitySource _activitySource =
        new("YourService.Domain");
    private static readonly Meter _meter =
        new("YourService.Domain");

    public void RecordEvent(string eventName, string level = "info",
        IReadOnlyDictionary<string, object>? attributes = null)
    {
        var logger = Log.ForContext("EventName", eventName);
        if (attributes is not null)
            foreach (var (key, value) in attributes)
                logger = logger.ForContext(key, value);

        Action<string> logAction = level switch
        {
            "debug"   => logger.Debug,
            "warning" => logger.Warning,
            "error"   => logger.Error,
            _         => logger.Information,
        };
        logAction(eventName);
    }

    public IDisposable StartSpan(string spanName,
        IReadOnlyDictionary<string, object>? attributes = null)
    {
        var activity = _activitySource.StartActivity(spanName);
        if (activity is not null && attributes is not null)
            foreach (var (key, value) in attributes)
                activity.SetTag(key, value?.ToString());
        return activity ?? new NoOpDisposable();
    }

    public void IncrementCounter(string name, int value = 1,
        IReadOnlyDictionary<string, string>? tags = null)
    {
        var counter = _meter.CreateCounter<int>(name);
        var tagList = tags is not null
            ? new TagList(tags.Select(kvp =>
                new KeyValuePair<string, object?>(kvp.Key, kvp.Value)).ToArray())
            : default;
        counter.Add(value, tagList);
    }

    private sealed class NoOpDisposable : IDisposable
    {
        public void Dispose() { }
    }
}
```

Register in `Program.cs`:

```csharp
builder.Services.AddSingleton<IObservabilityPort, SerilogOtelObservabilityAdapter>();

builder.Services.AddOpenTelemetry()
    .WithTracing(tracing => tracing
        .AddSource("YourService.Domain")
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter())
    .WithMetrics(metrics => metrics
        .AddMeter("YourService.Domain")
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter());
```

---

## 4. Usage in Domain Services

```csharp
public class SchemaContractService(
    ISchemaRegistryPort registry,
    IObservabilityPort obs) : ISchemaContractServicePort
{
    public async Task PublishAsync(string schemaId, int version, JsonDocument body)
    {
        using var span = obs.StartSpan("publish_schema",
            new Dictionary<string, object> { ["schema_id"] = schemaId });

        obs.RecordEvent("schema_publish_started",
            attributes: new Dictionary<string, object>
            {
                ["schema_id"] = schemaId,
                ["version"]   = version,
            });

        await registry.PublishAsync(schemaId, version, body);

        obs.RecordEvent("schema_published",
            attributes: new Dictionary<string, object>
            {
                ["schema_id"] = schemaId,
                ["version"]   = version,
            });

        obs.IncrementCounter("schema_publish_count",
            tags: new Dictionary<string, string> { ["schema_id"] = schemaId });
    }
}
```

---

## 5. Rules

- Domain services depend on `IObservabilityPort` (the interface), never on the adapter
- The adapter is injected via constructor — never used directly in domain code
- `RecordEvent` must NOT include raw request/response bodies or PII
- Span names should use `verb_noun` format (e.g., `publish_schema`, `retrieve_schema`)
- Counter names should use `snake_case` with a noun suffix (e.g., `schema_publish_count`)
- The port does not expose log formatting — that is the adapter's responsibility

---

## 6. Testing

In unit tests, use a fake that implements `IObservabilityPort`:

```csharp
public sealed class FakeObservability : IObservabilityPort
{
    public List<(string Event, string Level, IReadOnlyDictionary<string, object>? Attrs)> Events = [];
    public List<string> Spans = [];
    public List<(string Name, int Value)> Counters = [];

    public void RecordEvent(string eventName, string level = "info",
        IReadOnlyDictionary<string, object>? attributes = null)
        => Events.Add((eventName, level, attributes));

    public IDisposable StartSpan(string spanName,
        IReadOnlyDictionary<string, object>? attributes = null)
    {
        Spans.Add(spanName);
        return new NoOpDisposable();
    }

    public void IncrementCounter(string name, int value = 1,
        IReadOnlyDictionary<string, string>? tags = null)
        => Counters.Add((name, value));

    private sealed class NoOpDisposable : IDisposable { public void Dispose() { } }
}
```

Assert on `fakeObs.Events`, `fakeObs.Spans`, and `fakeObs.Counters` — not on log output.
