# Historical native rendering v2 fixture

Captured using the real `preview_install` / `apply_install` at merged PR #204
(`42c07b9284d3344618a846f9c8a176d8be02b65a`), before implementing invocation
policy portability. The sample Claude install contains a pinned Codex explicit-only
policy that v2 copied without translating or aliasing its default prompt.
Preserve these original bytes: this fixture proves historical offline replay and
explicit upgrade behavior without recreating an old lock using new production code.
