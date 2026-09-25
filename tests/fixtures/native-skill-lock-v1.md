# Historical native skill lock fixture

`native-skill-lock-v1/` is actual installer output from main at `722482e`
(GovKit 0.21.1), captured before implementing `install-as-v1` rendering.
It installs the deterministic `make_pack(..., skills=True)` sample fixture
through `preview_install` / `apply_install`, with the Codex sample profile.

The native directory is `sample-help`, but the original frontmatter says
`help`. The pinned files and lock contain their original byte-copy hashes.
Do not regenerate it with a newer renderer: tests use this historical artifact
to prove offline replay, protected explicit upgrade and unchanged pinned bytes.
