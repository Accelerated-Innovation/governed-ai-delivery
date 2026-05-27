# Architecture Contract Set Schema

This placeholder describes the expected shape for extension-declared architecture contract sets.

Required fields:

- `id`
- `description`
- `paths`

Optional fields:

- `applies_to`
- `capabilities`
- `required_for_level`
- `required_when_extension_enabled`

Govkit validation should ensure every declared path exists after the extension is applied.
