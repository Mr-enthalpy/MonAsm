# N5a probe: protected merge authorization

> Evidence only. This file is not a contract and is never a build input. The
> normative requirement is `ADR-0128` §8.1/§8.3; this file records what the
> repository configuration actually was when probed, and no more.

- Probe time: 2026-11-20, 11:39Z–11:41Z.
- Subject: `Mr-enthalpy/MonAsm`, `main` at `6df307e` (the H2-0 merge).
- Actor: GitHub account `Mr-enthalpy`.
- Token scopes reported by `gh auth status`: `admin:public_key`, `gist`,
  `read:org`, `repo`.

## Probes and raw results

| Request | Result |
|---|---|
| `GET /repos/Mr-enthalpy/MonAsm` | `permissions: {admin: true, maintain: true, push: true}`, `visibility: public`, `allow_auto_merge: false`, `allow_merge_commit: true`, `allow_squash_merge: true`, `allow_rebase_merge: true`, `delete_branch_on_merge: false` |
| `GET /repos/Mr-enthalpy/MonAsm/branches/main` | `protected: false` |
| `GET /repos/Mr-enthalpy/MonAsm/branches/main/protection` | HTTP 404, body `{"message":"Branch not protected"}` (not 403) |
| `GET /repos/Mr-enthalpy/MonAsm/rulesets` | `[]` |
| `GET /repos/Mr-enthalpy/MonAsm/rulesets?targets=branch` | `[]` |
| `GET /repos/Mr-enthalpy/MonAsm/environments` | `{"total_count":0,"environments":[]}` |
| `GET /repos/Mr-enthalpy/MonAsm/actions/permissions` | `enabled: true`, `allowed_actions: all`, `sha_pinning_required: false` |
| `gh pr view 4 --json reviewDecision,reviews` | `reviewDecision: ""`, `reviews: 0` (merged) |
| `gh pr view 5 --json reviewDecision,reviews` | `reviewDecision: ""`, `reviews: 0` (merged) |
| `.github/workflows/gates.yml` triggers | `push` on `main`, `pull_request`, `workflow_dispatch`; no `merge_group` |
| `.github/workflows/determinism.yml` triggers | same; no `merge_group` |
| Workflow action references | `actions/checkout@v4`, `actions/setup-python@v5` (mutable tags, not pinned commits) |

Both the planning PR #4 (`1850494`) and the acceptance PR #5 (`6df307e`) were
merged with a plain merge commit immediately after the PR checks turned green.
Neither carried an approving review.

## What this establishes

1. **Read access was sufficient.** `permissions.admin` is true and the branch
   protection endpoint answered 404 "Branch not protected" rather than 403.
   The empty results are the current configuration, not a permission gap. The
   earlier observation of a 403 is therefore not the state of this probe and
   must not be reused as this round's evidence.
2. **No protected merge channel exists today.** There is no branch protection,
   no repository ruleset, no environment gate, no required status check, no
   required review and no merge queue. Direct pushes, force pushes and branch
   deletion are not blocked by configuration.
3. **Gate provenance is not enforced.** Gate workflows are reached through
   mutable action tags, repository policy does not require SHA pinning, and no
   workflow listens for `merge_group`. A workflow edit is an ordinary PR edit.
4. **Candidate tree = landed tree is not established.** `pull_request` jobs
   build GitHub's synthetic merge commit for that event; nothing records that
   the commit which later lands has the same tree. A plain merge after the base
   advances can produce a different tree with the same green checks.
5. **Required-check names are not yet unique.** `determinism.yml` names its
   matrix jobs `ubuntu-latest`, `macos-latest` and `windows-latest`. The first
   version of `n1b-poc.yml` reused the same names, so a required check with one
   of those names could be satisfied by the much smaller PoC workflow. The PoC
   jobs are now `n1b-poc (<os>)`; this collision must be kept out of the required
   set when a ruleset is enabled.

## N5a verdict

`AuthorizedMerge(B,T,e,M)` is **not satisfied** in the current configuration.
This is not a claim that protection is impossible: the account has `admin:true`
and GitHub rulesets are available to this repository. It is a claim that no
protected merge channel exists to demonstrate, so the publication predicate
`P(B,T,e,M) = Q(B,T,e) ∧ AuthorizedMerge(B,T,e,M)` has no evidence for its
second conjunct.

Consequently the H2-0 merge itself has only procedural, not enforced,
authorization. Its content is a docs-only status flip and remains valid as a
decision; it is not N5a evidence.

## Feasibility path (not yet executed)

A minimal demonstration would need all of the following recorded in one trial:

- a branch ruleset on `main` with required status checks for the existing gate
  jobs under names that are unique across workflows, required pull request,
  blocked force pushes and blocked deletion;
- merge queue enabled, with a `merge_group` trigger on the gate workflows and a
  workflow that builds the queued tree;
- SHA-pinned action references (or repository policy requiring them) so the
  gate logic cannot change without review;
- one PR that merges through the queue, recording the tested tree SHA, the
  `merge_group` run, the landed merge commit and its tree SHA, with the last two
  equal.

Enabling that ruleset changes repository settings and CI triggers; it is a
separate decision from this probe and is not performed here.

## Non-claims

- Absence of protection does not prove that unreviewed changes have occurred or
  that contributors act in bad faith.
- A future ruleset does not by itself prove the gate logic is correct; it only
  makes the gate's source and the tested tree enforceable.
- This probe does not check GitHub-side audit logs, organization policy or
  branch protection on other branches.
