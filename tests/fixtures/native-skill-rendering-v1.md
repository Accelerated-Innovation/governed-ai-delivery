# Original alias-rendering lock fixture

`native-skill-rendering-v1/` is actual installer output from PR #203 at
`638bc92`, before the reference-style destination fix. Its lock records
`install-as-v1`, whose native bytes change `[guide]: unit-testing` into
`[guide]: craft-unit-testing`, despite the resource retaining its original name.

Tests retain that old lock and its exact bytes for offline replay, then explicitly
preview/apply `install-as-v2` to repair the native reference without changing any
pinned source bytes. Do not regenerate this fixture with the corrected renderer.
