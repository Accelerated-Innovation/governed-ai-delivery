# Seven actual-change pilots

`consumer.json` contains a separately accepted profile/configuration and small
consumer files, plus baseline/fixed service bytes. It reuses the seven normalized
requests in `../workflows/requests/`: defect, enhancement, refactor, MCP, LLM,
feature and architecture. Existing spec/plan/review references are reused. Artifact
text is a presence fixture; it does not assert an independent review occurred.

`tests/wheel_change_smoke.py` materializes this fixture only in temporary directories,
installs pinned resources into the policy directory, initializes the ungoverned
consumer Git baseline and invokes the real CLI. The service regression, MCP input/
output contract, LLM supplied-output evaluator and literal architecture boundary
all have real failure cases. Defect execution verifies both baseline failure and
current success. Each scenario compares local/CI JSON, replays it and checks that
inspection did not write to either tree. Architecture's measured checks pass, but
its unavailable platform approval stays unknown and its overall exit remains 1.

The same harness runs in fast tests and the installer CI wheel job with runtime-only
dependencies. It is a deterministic synthetic pilot, not evidence of live provider
approval or developer productivity. See `docs/CHANGE_CONFORMANCE.md` for adapting
accepted sources and execution configuration to a real project. Do not apply this
consumer fixture to the GovKit source repository.
