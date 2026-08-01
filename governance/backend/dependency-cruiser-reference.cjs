/*
 * dependency-cruiser reference configuration for hexagonal architecture
 * enforcement on the `nodejs-fastify` stack.
 *
 * Copy this file to `.dependency-cruiser.cjs` in your repository root — the
 * filename cli/stacks/nodejs-fastify/TECH_STACK.md already names. No
 * placeholders to replace: the rules are keyed on layer folder names, not on
 * your package name.
 *
 * Install: npm install --save-dev dependency-cruiser
 * Run:     npx depcruise src --config .dependency-cruiser.cjs
 *
 * This configuration enforces the layering rules defined in:
 *   docs/backend/architecture/ARCH_CONTRACT.md
 *   docs/backend/architecture/BOUNDARIES.md
 *
 * It is the Node equivalent of governance/backend/importlinter-reference.toml
 * and expresses the same contract: `api` and `adapters` are independent
 * siblings above `services`, above `ports`, above `models`, above `common`,
 * with `api -> services` forbidden outright.
 *
 * ---------------------------------------------------------------------------
 * TWO WAYS THIS TOOL PASSES WITHOUT CHECKING ANYTHING. Both were reproduced
 * against dependency-cruiser 17.4.3; both fail *open*, so neither announces
 * itself.
 *
 * 1. `--output-type json` prints every violation and still exits 0. Use the
 *    default (`err`) reporter in CI. A gate built on the JSON reporter is
 *    green on a repo that breaches every boundary.
 *
 * 2. With **TypeScript 7** installed, dependency-cruiser 17 cruises
 *    0 modules and exits 0 — it uses the TypeScript 5.x compiler API, which
 *    TypeScript 7 replaced. The run looks identical to a clean one.
 *
 * After copying this in, confirm the output reports a NON-ZERO module count:
 *
 *     no dependency violations found (7 modules, 8 dependencies cruised)
 *                                     ^^^^^^^^^
 *
 * "0 modules cruised" means the analysis found nothing, however green the
 * result. ci/<flavour>/boundary-gate-node.yml asserts this for you.
 * ---------------------------------------------------------------------------
 *
 * LAYOUT. The rules accept both source layouts the payload describes:
 *
 *   src/<layer>/...              flat — cli/stacks/nodejs-fastify/LAYER_IMPLEMENTATION.md
 *   src/<package>/<layer>/...    nested — docs/backend/architecture/REPO_STRUCTURE_README.md
 *
 * COMPOSITION ROOT. Whatever wires adapters into services at startup
 * necessarily imports both, so it must live outside the six layer folders —
 * `src/app.ts` or `src/container.ts`, as LAYER_IMPLEMENTATION.md prescribes.
 * A composition root placed inside `api/` or `adapters/` trips the sibling
 * rule below.
 */

// Each layer matches at both depths: `src/api/` and `src/<package>/api/`.
// Expressed as an array rather than one regex with an optional group —
// dependency-cruiser rejects `^src/(?:[^/]+/)?api/` as ReDoS-unsafe.
const layer = (...names) => {
  const group = names.length > 1 ? `(${names.join('|')})` : names[0];
  return [`^src/${group}/`, `^src/[^/]+/${group}/`];
};

module.exports = {
  forbidden: [
    {
      // BOUNDARIES.md section 2: the API invokes behaviour through
      // `ports/inbound/` only. Importing entities from `models/` is allowed —
      // inbound port signatures carry them.
      name: 'api-not-to-services',
      comment: 'api/ must reach the domain through ports/inbound/, never directly',
      severity: 'error',
      from: { path: layer('api') },
      to: { path: layer('services') },
    },
    {
      // `api` and `adapters` are both adapters in the pattern — inbound and
      // outbound. Neither may import the other; they meet at the composition
      // root. This pair is the equivalent of import-linter's `api | adapters`.
      name: 'api-not-to-adapters',
      comment: 'api/ and adapters/ are independent siblings',
      severity: 'error',
      from: { path: layer('api') },
      to: { path: layer('adapters') },
    },
    {
      name: 'adapters-not-to-api',
      comment: 'api/ and adapters/ are independent siblings',
      severity: 'error',
      from: { path: layer('adapters') },
      to: { path: layer('api') },
    },
    {
      // The single most important forbidden edge — ARCH_CONTRACT.md section 3,
      // BOUNDARIES.md section 2. The domain depends on port interfaces; the
      // adapters implement them.
      name: 'services-not-to-adapters-or-api',
      comment: 'the domain must not import infrastructure',
      severity: 'error',
      from: { path: layer('services') },
      to: { path: layer('api', 'adapters') },
    },
    {
      // ports/ sits *below* services/: it holds interfaces and may reference
      // entities, while services imports the ports it depends on. Granting the
      // reverse as well would create the cycle BOUNDARIES.md forbids.
      name: 'ports-not-upward',
      comment: 'ports/ is interface-only and depends on models/ and common/ alone',
      severity: 'error',
      from: { path: layer('ports') },
      to: { path: layer('api', 'adapters', 'services') },
    },
    {
      name: 'models-not-upward',
      comment: 'domain entities stay ignorant of behaviour and interfaces',
      severity: 'error',
      from: { path: layer('models') },
      to: { path: layer('api', 'adapters', 'services', 'ports') },
    },
    {
      name: 'common-not-upward',
      comment: 'common/ is cross-cutting and must stay dependency-free',
      severity: 'error',
      from: { path: layer('common') },
      to: { path: layer('api', 'adapters', 'services', 'ports', 'models') },
    },
    {
      // Multi-service repositories. The layer rules above apply *within* each
      // service and say nothing about service-to-service edges —
      // orders/services importing billing/services passes all of them.
      //
      // Unlike import-linter's `independence` contract, which has to be
      // uncommented deliberately, this one ships enabled: the pattern requires
      // a `src/<service>/<layer>/` segment, so it matches nothing in a flat
      // single-service repo and starts enforcing the moment one grows a
      // service package.
      name: 'services-are-independent',
      comment: 'one service must not import another; talk over a port',
      severity: 'error',
      from: { path: '^src/([^/]+)/(api|ports|services|models|adapters|common)/' },
      to: {
        path: '^src/([^/]+)/(api|ports|services|models|adapters|common)/',
        pathNot: '^src/$1/',
      },
    },
  ],
  options: {
    // Follow `import type` as well as value imports. A type-only import still
    // couples the layers, and ARCH_CONTRACT.md's boundaries are about coupling.
    tsPreCompilationDeps: true,
    doNotFollow: { path: 'node_modules' },
  },
};
