# Digest: Nouns and Verbs (ch: nouns_and_verbs)

## Core principle
The point of noun/verb naming is to distinguish **commands** (tell the object
to do something) from **queries** (ask the object what it knows). The split
is semantic, not syntactic.

## Rules of thumb (from manuscript)
- **Objects and types** → noun names (`customer`, `PhoneDialer`, `Invoice`)
- **Commands** → verb or verb phrase (`dial()`, `cancel()`, `submit_order()`)
- **Attribute getters / queries** → **noun preferred** over `get_X()` verb form
  - `customer.preferred_name()` reads as "name IS the customer's preferred name"
  - `get_preferred_name()` adds noise without information
  - Exception: when a framework requires `get_` or `set_` prefixes, comply
- **Interfaces, protocols, mixins** → adjective-like (`Serializable`, `FileLike`)
  or the abstract-type-as-noun pattern (`Messenger` → `SMSMessenger`,
  `EmailMessenger`)
- **IFoo / Foo splits** → considered inferior; use only when framework or team
  insists

## `as` conversions
`customer.date_as_ISO8601` signals the *Customer* shouldn't own this
conversion. It belongs on the date type: `customer.date.as_ISO8601()`.
Repeated `as_X()` methods suggest a missing whole-value-object.

## Framework override
When a framework uses reflection and demands `get_`/`set_` warts or `_field`
private prefixes, comply. Fighting your tools is not the point.

## The real question
*"Which of these calls is a command and which is a query?"*
If it's not clear from reading the call site, the name is failing.
