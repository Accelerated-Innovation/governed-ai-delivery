# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pure, deterministic capability graph selection over already-read snapshots."""

from __future__ import annotations

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .pack_models import DependencyEdge, PackDecision, PackResolution, PackSnapshot
from .profiles import ProjectProfile, resolve_profile


def resolve_packs(
    profile: ProjectProfile, catalog: tuple[PackSnapshot, ...], *, govkit_version: str
) -> PackResolution:
    """Never fetch, install, execute, or infer accepted policy from a pack.

    Different providers require an explicit selection. For one provider, try
    compatible versions in descending order, backtracking across dependencies.
    Pins constrain selection; they do not enable an otherwise undesired pack.
    """
    pins = {p["id"]: p for p in profile.document.get("packs", [])}
    context = profile.repository.integrations
    profile_result = resolve_profile(profile)
    initial = tuple(
        PackDecision(d.code, d.affected, d.message)
        for d in profile_result.plan.selections.unresolved
    )
    required = {c.id for c in profile.repository.policy.required_checks}
    available = tuple(sorted({cap for pack in catalog for cap in pack.provides}))
    catalog = tuple(
        sorted(catalog, key=lambda p: (p.id, Version(p.version), p.source_kind, p.digest))
    )

    def result(selected, edges, decisions):
        packs = tuple(selected[key] for key in sorted(selected))
        checks = required | {c.id for p in packs for c in p.checks if c.required}
        return PackResolution(
            profile.digest,
            govkit_version,
            available,
            packs,
            tuple(sorted(set(edges), key=lambda e: (e.parent, e.capability, e.provider, e.reason))),
            tuple(sorted(checks)),
            initial + tuple(decisions),
        )

    def finish(selected, edges):
        decisions = []
        capabilities = {cap for p in selected.values() for cap in p.provides}
        for pack in selected.values():
            for conflict in sorted(set(pack.conflicts) & capabilities):
                decisions.append(
                    PackDecision(
                        "capability-conflict",
                        (pack.id, conflict),
                        f"{pack.id} conflicts with {conflict}",
                    )
                )
        graph = {identifier: set() for identifier in selected}
        for edge in edges:
            if edge.parent in graph:
                graph[edge.parent].add(edge.provider)
        visiting, visited = set(), set()

        def cycle(node):
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            if any(cycle(child) for child in sorted(graph[node])):
                return True
            visiting.remove(node)
            visited.add(node)
            return False

        if any(cycle(node) for node in sorted(graph)):
            decisions.append(
                PackDecision(
                    "dependency-cycle",
                    tuple(sorted(visiting)),
                    "Capability dependency cycle; reconcile the declared requirements",
                )
            )
        check_owners, skill_owners = {}, {}
        for pack in selected.values():
            for kind, identifiers, owners in (
                ("check", [c.id for c in pack.checks], check_owners),
                ("skill", [s.install_as for s in pack.skills], skill_owners),
            ):
                for identifier in identifiers:
                    if identifier in owners:
                        decisions.append(
                            PackDecision(
                                f"duplicate-{kind}",
                                (identifier, owners[identifier], pack.id),
                                f"Multiple packs install {kind} {identifier}",
                            )
                        )
                    owners[identifier] = pack.id
        for check in sorted(required - check_owners.keys()):
            decisions.append(
                PackDecision(
                    "unavailable-check",
                    (check,),
                    f"Accepted policy requires executable check {check}; select its provider",
                )
            )
        return result(selected, edges, decisions)

    def search(pending, selected, edges):
        if not pending:
            return finish(selected, edges)
        parent, capability, constraint, reason = pending[0]
        rest = pending[1:]
        specifier = SpecifierSet("" if constraint == "*" else constraint)
        candidates = [p for p in catalog if capability in p.provides]

        def fail(code, message):
            return result(selected, edges, [PackDecision(code, (parent, capability), message)])

        if not candidates:
            return fail("missing-capability", f"No available pack provides {capability}")
        pinned_ids = {p.id for p in candidates if p.id in pins}
        if pinned_ids:
            candidates = [p for p in candidates if p.id in pinned_ids]
        candidates = [
            p
            for p in candidates
            if p.id not in pins
            or (
                Version(p.version) == Version(pins[p.id]["version"])
                and p.source_kind == pins[p.id]["source"]
                and ("digest" not in pins[p.id] or p.digest == pins[p.id]["digest"])
            )
        ]
        if not candidates:
            return fail(
                "unavailable-pin",
                f"No source matches the exact version/digest pin for {capability}",
            )
        candidates = [p for p in candidates if Version(p.version) in specifier]
        if not candidates:
            return fail(
                "incompatible-version", f"No version of {capability} satisfies {constraint}"
            )
        candidates = [
            p for p in candidates if Version(govkit_version) >= Version(p.govkit_min_version)
        ]
        if not candidates:
            return fail(
                "govkit-version", f"{capability} requires a newer GovKit than {govkit_version}"
            )
        candidates = [
            p for p in candidates if not p.project_types or context.project_type in p.project_types
        ]
        if not candidates:
            return fail(
                "project-type", f"{capability} requires an explicitly supported project type"
            )
        candidates = [
            p
            for p in candidates
            if (not p.skills and context.agent is None) or context.agent in p.agents
        ]
        if not candidates:
            return fail(
                "agent-integration",
                f"{capability} requires an explicitly supported agent integration",
            )
        if len({p.id for p in candidates}) > 1:
            return fail(
                "ambiguous-provider",
                f"Multiple packs provide {capability}; pin the intended provider",
            )
        if len({p.source_kind for p in candidates}) > 1:
            return fail(
                "ambiguous-source",
                f"{capability} has bundled and local providers; pin source, version and digest",
            )
        by_version = {}
        for pack in candidates:
            by_version.setdefault(pack.version, set()).add(pack.digest)
        if any(len(digests) > 1 for digests in by_version.values()):
            return fail(
                "ambiguous-source",
                f"{capability} has different content at the same version; pin its digest",
            )
        candidates = sorted(candidates, key=lambda p: (Version(p.version), p.digest), reverse=True)
        first_failure = None
        for pack in candidates:
            existing = selected.get(pack.id)
            if existing and (existing.version, existing.digest) != (pack.version, pack.digest):
                continue
            edge = DependencyEdge(parent, capability, pack.id, reason)
            dependencies = (
                []
                if existing
                else [
                    (pack.id, d.capability, d.version, d.reason)
                    for d in sorted(
                        pack.requires, key=lambda d: (d.capability, d.version, d.reason)
                    )
                ]
            )
            attempt = search(rest + dependencies, {**selected, pack.id: pack}, edges + [edge])
            if attempt.ready:
                return attempt
            if first_failure is None:
                first_failure = attempt
        return first_failure or fail(
            "incompatible-version", f"Requirements select incompatible versions of {capability}"
        )

    desired = [
        (f"profile:{profile.repository.id}", c.id, "*", "Explicit desired capability")
        for c in sorted(profile.repository.capabilities, key=lambda c: c.id)
    ]
    return search(desired, {}, [])
