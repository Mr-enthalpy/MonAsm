# N5a trial: the protected merge channel on `main`

> Evidence only. This file is not a contract and is never a build input. The
> normative requirement is `ADR-0128` §8.1/§8.3; this record states what the
> repository now enforces and what it still does not. It does **not** declare
> N5a satisfied.

- Trial branch, first entry: `he1/n5a-trial-1`, opened 2026-11-20 after the
  ruleset became active.
- Repository: `Mr-enthalpy/MonAsm` (public, user-owned).
- `main` at the time the ruleset was enabled:
  `5b7285538edb2b6213df5a3f1f35dc8d2bb3f24c` (the merge of PR #8).

## 1. What was enabled

A single repository ruleset on `refs/heads/main`, created through
`POST /repos/Mr-enthalpy/MonAsm/rulesets`:

- id `27723469`, name `main: protected merge channel`, target `branch`,
  enforcement `active`;
- `bypass_actors: []`, and the API reports `current_user_can_bypass: "never"`
  for the repository owner — the owner cannot bypass their own rules;
- repository setting `allow_auto_merge` changed `false` → `true`.

Verbatim `rules` array as the API returns it:

```json
[
  { "type": "deletion" },
  { "type": "non_fast_forward" },
  {
    "type": "pull_request",
    "parameters": {
      "allowed_merge_methods": ["merge"],
      "dismiss_stale_reviews_on_push": true,
      "require_code_owner_review": false,
      "require_extra_approval_for_unattributed_changes": true,
      "require_last_push_approval": false,
      "required_approving_review_count": 0,
      "required_review_thread_resolution": true,
      "required_reviewers": []
    }
  },
  {
    "type": "required_status_checks",
    "parameters": {
      "do_not_enforce_on_create": false,
      "required_status_checks": [
        { "context": "document and definition gates" },
        { "context": "workspace tests" },
        { "context": "oracle rerun" },
        { "context": "H0 payload baseline" },
        { "context": "ubuntu-latest" },
        { "context": "macos-latest" },
        { "context": "windows-latest" }
      ],
      "strict_required_status_checks_policy": true
    }
  }
]
```

Why exactly these seven contexts: they are the job names of `gates.yml` and
`determinism.yml` on the merged tree, read from a passing run of PR #8 and
confirmed in the workflow files. The `n1b-poc (<os>)` jobs are deliberately
**not** required — that workflow is path-filtered, so requiring it would block
every change outside `research/he1/n1b-poc/**`. The earlier name collision with
the determinism matrix is fixed (`n5a-merge-authorization-probe.md` finding 5),
so no required context can be satisfied by the smaller workflow.

`required_approving_review_count` is `0` because the repository has one
maintainer account and no second reviewer. That is a property of this
demonstration, not a claim that zero approvals is enough for a real release
process; the review gap is recorded in §5.

## 2. Merge queue: unavailable on this repository

The intended channel was a merge queue, so that the tested tree and the landed
tree are the same object by construction. It cannot be enabled here.

Enabling it was attempted in three shapes and the API rejected every one:

| Payload | Response |
|---|---|
| full ruleset incl. `merge_queue` | `422` `{"errors":["Invalid rule 'merge_queue': "]}` |
| `merge_queue` alone, minimal parameters | `422`, same error |
| `PUT` the existing ruleset to add `merge_queue` | `422`, same error |

The rule name is recognised (a genuinely unknown rule type returns
`Invalid property /rules/0: data matches no possible input`), so this is not a
syntax error. It is an availability limit: GitHub documents merge queues as
available "in any public repository owned by an organization, or in private
repositories owned by organizations using GitHub Enterprise Cloud", and this
repository is owned by a user account, not an organization.

Consequences, stated plainly:

- No `merge_group` check will ever run in this repository as configured. The
  `merge_group` triggers added to `gates.yml` and `determinism.yml` are dormant;
  they are kept because they are exactly what a queue needs if the repository
  moves to an organization, but they are not evidence of anything today.
- `Allow auto-merge` is enabled and unused.
- The queue's guarantee — the tested tree *is* the landed tree, with no window
  between them — is therefore not available and not claimed. The closest
  available substitute is the strict up-to-date policy described in §4.

Resolved later the same day: the repository was transferred to the
`Teancher-H` organization and the queue was enabled — see §7. Everything above
remains accurate about the repository as it was owned by `Mr-enthalpy`.

## 3. Observed negative evidence

Both attempts were made with the owner credential, after the ruleset was active.

```
PATCH /repos/Mr-enthalpy/MonAsm/git/refs/heads/main
{"sha": "5d7adfbdce90b61e2d8d064d3dcfc4831073259c", "force": true}

422 Repository rule violations found
    Cannot force-push to this branch
    Changes must be made through a pull request.
```

```
DELETE /repos/Mr-enthalpy/MonAsm/git/refs/heads/main

422 Cannot delete the default branch
```

`main` was `5b7285538edb2b6213df5a3f1f35dc8d2bb3f24c` before both attempts and
after both attempts.

Read this carefully:

- The force-push refusal names two rules and is a direct observation of
  `non_fast_forward` and `pull_request` being enforced.
- The deletion refusal comes from GitHub's own default-branch rule, which
  predates the ruleset. It does **not** isolate the ruleset's `deletion` rule;
  that rule is part of the active set but this probe cannot show it firing on
  its own.

## 4. Procedure for each trial entry

The same sequence is used for every merge in this log, so the comparison is
mechanical rather than narrative:

1. Branch from `main`, commit, push, open a pull request.
2. Record the PR base and head (`gh pr view --json baseRefOid,headRefOid`) and
   its `mergeStateStatus` while required checks are still running; it must not
   be mergeable then.
3. With all seven required checks green, record the commit GitHub tested:
   `git ls-remote origin refs/pull/<n>/merge` and its tree
   (`git rev-parse <sha>^{tree}`).
4. Merge with `gh pr merge <n> --merge`; the ruleset permits only the `merge`
   method, so the landed commit must be a merge commit.
5. After the merge, record the merge commit `M`, its tree and its first parent.
6. Assert `tree(tested) == tree(M)` and `base == parent_1(M)`.

Step 3 is only meaningful because of the strict policy: if `main` advances
between step 2 and step 4, GitHub refuses the merge and the PR must be updated
and re-tested. That closes the ordinary stale-check window. It does not close a
same-instant race, which is precisely what the unavailable queue would have
removed — so a green row in this log is evidence for "the merged tree is the
tree the gates ran on, with the base re-checked at merge time", not for the
queue's stronger ordering guarantee.

## 5. What this trial does not establish

- **The queue closes the tested/landed gap; approval does not.** Entries 1 and 2
  predate the queue and establish only that under strict up-to-date the landed
  tree equals the tested tree. Entries 3 to 6 are queued merges where the landed
  commit *is* the tested commit, so on that path the two cannot diverge. What
  remains is independent authorization: `required_approving_review_count` is 0,
  and the same account writes, merges and administers, so the merge is enforced
  but not independently approved. `AuthorizedMerge(B,T,e,M)` is therefore still
  not satisfied. This is an accepted open gap while the project has a single
  author; it is recorded, not worked around.
- **Gate logic provenance is pinned; the runner is not.** As of entry 6 every
  `uses:` names a full commit and the repository setting `sha_pinning_required`
  is `true`, so a mutable tag no longer resolves — §8 records the policy and the
  negative test that shows an unpinned reference fails in `Set up job`. What
  pinning does not cover is the runner image and the toolchain it ships:
  `ubuntu-latest` keeps moving, and only the LLVM release the oracle step names
  is pinned. Pinning fixes *which* code the workflow runs, not the machine.
- **A workflow change is still judged by the workflow it introduces.** For
  `pull_request` and `merge_group` events the checks come from the revision's own
  workflow files. The ruleset makes such a change reviewable and recorded; it
  does not make the change self-verifying.
- **No stale-CI counterexample is recorded here.** A queued entry whose build
  fails must be removed and the branch returned; that is a different experiment
  from this log and belongs to the N5a evidence set.
- **Only single-entry groups have been exercised.** `grouping_strategy` is
  `ALLGREEN` with `max_entries_to_merge` 5, but no group of two has been built,
  so the combined-tree case is untested.
- **No claim about other branches, tags, organization policy, or audit logs.**

## 6. Log

Entries are appended by a change that merges *after* the one being described,
because a commit cannot contain its own merge SHAs. The table records every
merge completed under this channel up to the change that wrote it; the merge
that lands the newest entry is checked by the same procedure and becomes the next
entry when one is added. Six consecutive entries show this is not a single-run
accident: two merges under strict up-to-date and four through the queue. Every
merge after entry 1 went through this channel.

| Entry | PR | Tested tree | Landed commit | Landed tree | Equal |
|---|---|---|---|---|---|
| 1 | #9 | `88c65951b350a513247338a3fdda1d470d677933` | `c9ae2648e5230f0ba79c6be4919806b20763959d` | `88c65951b350a513247338a3fdda1d470d677933` | yes |
| 2 | #10 | `cdcbd458b6508080e99f5605da139060de5b6c0c` | `e3fef895fb464a123eff6c8bc375f23cbc5b1a30` | `cdcbd458b6508080e99f5605da139060de5b6c0c` | yes |
| 3 | #12 | `b5cbcd7f9aa120cc5f07099992a6d531b690fd71` | `cc7674206da2032eb6602c94fa760ca5a16fb60e` | `b5cbcd7f9aa120cc5f07099992a6d531b690fd71` | yes |
| 4 | #13 | `4f5322d81b0a7561cd6450f413dd88ce32fbeb4e` | `0d07288aabd5b38b4e155b2ef92c923cee8b3917` | `4f5322d81b0a7561cd6450f413dd88ce32fbeb4e` | yes |
| 5 | #14 | `fdc104fb1cf48a08bc90c5cdde7e4fe476368540` | `b7096be31c05943a91809cd698b384414b3d0be5` | `fdc104fb1cf48a08bc90c5cdde7e4fe476368540` | yes |
| 6 | #15 | `07d7889f743b8e167225c4ac338e100d1bf08a44` | `af26da9c422b5b48d47f8601ae1cb3e63aa71c42` | `07d7889f743b8e167225c4ac338e100d1bf08a44` | yes |

### Entry 1, PR #9

- Base when the checks ran: `5b7285538edb2b6213df5a3f1f35dc8d2bb3f24c`.
- Head: `558fed56f4c50fd9c899263a70f5a637885d3ac0`.
- While the required checks were still pending, `mergeStateStatus` was
  `BLOCKED`; with all seven green it became `CLEAN`.
- Tested commit, `refs/pull/9/merge`: `1588601a9b0fe4cac873f109ccf0ccc0e46ea53c`,
  tree `88c65951b350a513247338a3fdda1d470d677933`, first parent
  `5b7285538edb2b6213df5a3f1f35dc8d2bb3f24c`.
- Merge performed with `gh pr merge 9 --merge` at 2026-11-20T12:18:53Z.
- Landed commit `c9ae2648e5230f0ba79c6be4919806b20763959d`, tree
  `88c65951b350a513247338a3fdda1d470d677933`, first parent
  `5b7285538edb2b6213df5a3f1f35dc8d2bb3f24c`.

`tree(tested) == tree(landed)` and `base == parent_1(landed)` both hold. Nothing
advanced `main` between the last required check and the merge, and the strict
policy would have refused the merge if it had.

### Entry 2, PR #10

- Base when the checks ran: `c9ae2648e5230f0ba79c6be4919806b20763959d`.
- Head: `b138d1d1e0380493eb679f6a7c4fa1b903034665`.
- All seven required checks green; `mergeStateStatus` `CLEAN` at merge time.
- Tested commit, `refs/pull/10/merge`: `9baeb13df499deae63a68baca6cb921be302c1cf`,
  tree `cdcbd458b6508080e99f5605da139060de5b6c0c`, first parent
  `c9ae2648e5230f0ba79c6be4919806b20763959d`.
- Merge performed with `gh pr merge 10 --merge` at 2026-11-20T12:27:23Z.
- Landed commit `e3fef895fb464a123eff6c8bc375f23cbc5b1a30`, tree
  `cdcbd458b6508080e99f5605da139060de5b6c0c`, first parent
  `c9ae2648e5230f0ba79c6be4919806b20763959d`.

Again `tree(tested) == tree(landed)` and `base == parent_1(landed)`. The second
entry was produced by an ordinary change after the first had landed, so the
result does not depend on the ruleset having been freshly created.

### Entry 3, PR #12 — first queued merge

- Base: `01fdd50966aaed5c15c642fcf8f1a51385d3b64c`.
- Head: `41ffcf758cbc405a944829510ef3cfd6855f2aa4`.
- The seven required checks passed on the pull request, then the entry was added
  to the queue with `gh pr merge 12 --auto`.
- `merge_group` runs, both on head
  `cc7674206da2032eb6602c94fa760ca5a16fb60e`:
  `44739653651` (`gates`: document and definition gates, workspace tests, H0
  payload baseline, oracle rerun) and `44739653755` (`determinism`: ubuntu-latest,
  macos-latest, windows-latest). Both concluded `success`.
- The queue merged at 2026-11-20T13:01:19Z.
- Landed commit `cc7674206da2032eb6602c94fa760ca5a16fb60e`, tree
  `b5cbcd7f9aa120cc5f07099992a6d531b690fd71`, first parent
  `01fdd50966aaed5c15c642fcf8f1a51385d3b64c`.

For this entry the stronger form holds, not just tree equality:
`origin/main` **is** the `merge_group` head SHA, `cc76742`, because a queue entry
of one is landed by fast-forwarding the branch to the commit the queue built.
The tested commit and the landed commit are the same object.

The strict up-to-date policy from §1 is still on. With a queue it is redundant —
the queue re-tests against the current base — but it is kept so entries 1 to 4
were produced under one unchanged configuration.

### Entry 4, PR #13 — second queued merge

- Base: `cc7674206da2032eb6602c94fa760ca5a16fb60e` (entry 3's landed commit).
- Head: `664f3e104f587a4c756d826f13cc65efbd161fc3`.
- Seven required checks green on the pull request, then `gh pr merge 13 --auto`
  put it at queue position 1.
- `merge_group` runs on head `0d07288aabd5b38b4e155b2ef92c923cee8b3917`:
  `44742138161` (`gates`) and `44742138424` (`determinism`), both `success`.
- The queue merged at 2026-11-20T13:16:45Z.
- Landed commit `0d07288aabd5b38b4e155b2ef92c923cee8b3917`, tree
  `4f5322d81b0a7561cd6450f413dd88ce32fbeb4e`, first parent
  `cc7674206da2032eb6602c94fa760ca5a16fb60e`.

Again `origin/main` is exactly the `merge_group` head. Two consecutive queued
merges now show the property, and entry 4 was queued after entry 3 had landed,
so it does not depend on a freshly enabled queue.

### Entry 5, PR #14 — third queued merge

- Base: `0d07288aabd5b38b4e155b2ef92c923cee8b3917` (entry 4's landed commit).
- Head: `7f9654a228bdd30854338afc87083bdcb6eb849d`, tree
  `fdc104fb1cf48a08bc90c5cdde7e4fe476368540`.
- `merge_group` runs on head `b7096be31c05943a91809cd698b384414b3d0be5`:
  `44744114175` (`gates`) and `44744114068` (`determinism`), both `success`.
- The queue merged at 2026-11-20T13:31:31Z.
- Landed commit `b7096be31c05943a91809cd698b384414b3d0be5`, tree
  `fdc104fb1cf48a08bc90c5cdde7e4fe476368540`, first parent
  `0d07288aabd5b38b4e155b2ef92c923cee8b3917`.

### Entry 6, PR #15 — the pinning merge

- Base: `b7096be31c05943a91809cd698b384414b3d0be5` (entry 5's landed commit).
- Head: `85c8298d3f0991145f25613b03b05ed6eca858f8`, tree
  `07d7889f743b8e167225c4ac338e100d1bf08a44`.
- `merge_group` runs on head `af26da9c422b5b48d47f8601ae1cb3e63aa71c42`:
  `44746766510` (`gates`) and `44746766480` (`determinism`), both `success`.
- The queue merged at 2026-11-20T13:47:42Z.
- Landed commit `af26da9c422b5b48d47f8601ae1cb3e63aa71c42`, tree
  `07d7889f743b8e167225c4ac338e100d1bf08a44`, first parent
  `b7096be31c05943a91809cd698b384414b3d0be5`.

This is the change that pinned every `uses:` to a full commit (§8). It landed
through the queue it hardens, but it was *tested by the unpinned workflows it
replaced* — the gate logic that approved it was the old gate logic. That
ordering is unavoidable and is why the policy flag was flipped afterwards, not
before.

Entries 5 and 6 were both produced by ordinary changes after the queue had
proven itself on entries 3 and 4.

## 7. Merge queue after the organization transfer

Later on 2026-11-20 the repository was transferred from `Mr-enthalpy/MonAsm` to
`Teancher-H/MonAsm`. It stays public; the organization is on the free plan and
the actor is an organization owner. This is the change §2 said would be needed.

The transfer changed the owner and left everything else in place: `main` stayed
at `01fdd50966aaed5c15c642fcf8f1a51385d3b64c`, ruleset `27723469` kept its
existing rules and its empty bypass list, and the old URLs redirect.

Re-sending the same `PUT /repos/Teancher-H/MonAsm/rulesets/27723469` payload that
§2 recorded as rejected was accepted. `GET /rules/branches/main` now returns
`deletion, non_fast_forward, pull_request, required_status_checks, merge_queue`,
and `current_user_can_bypass` is still `never`.

The enabled rule, verbatim:

```json
{
  "type": "merge_queue",
  "parameters": {
    "check_response_timeout_minutes": 60,
    "grouping_strategy": "ALLGREEN",
    "max_entries_to_build": 5,
    "max_entries_to_merge": 5,
    "merge_method": "MERGE",
    "min_entries_to_merge": 1,
    "min_entries_to_merge_wait_minutes": 5
  }
}
```

- `merge_method` is `MERGE` and the `pull_request` rule still allows only
  `merge`, so a queued entry lands as a merge commit.
- `ALLGREEN` means every entry in a group must pass the required checks, not
  just the group head. A group of one is the case exercised first.
- The `merge_group` triggers added to `gates.yml` and `determinism.yml` by PR #8
  stop being dormant here: they are what reports the seven required contexts for
  a queued build.

### Procedure for a queued entry

1. Open the pull request and wait for the seven required checks on the pull
   request itself.
2. Enqueue with `gh pr merge <n> --merge --auto`; direct merges are refused by
   the queue rule.
3. Record the `merge_group` workflow runs: run id, `head_sha`, conclusion.
4. After the entry lands, assert `origin/main == merge_group.head_sha`. For a
   single-entry group this is the strongest form of the property: the commit the
   gates ran on *is* the commit on `main`, not merely one with the same tree.
5. Cross-check `origin/main^{tree}` against `refs/pull/<n>/merge^{tree}`.

The queued merges are entries 3 to 6; their values are recorded by the changes
that follow them, as §6 explains. All four were groups of one entry, so the
queue has still not been observed merging a combined group.

## 8. Gate-input provenance: commit pins and the pinning policy

Until entry 6 the workflows named `actions/checkout@v4` and
`actions/setup-python@v5`. A tag is a mutable name: the same workflow file can
execute different code next week, and neither the plan, the definition nor the
recorded run says which code ran. That is a hole in the *gate*, not in the
materializer, so no fixture is invalidated — but "the checks passed" was not a
statement about a fixed verifier.

Entry 6 replaced all eight `uses:` lines with full commits:

| Reference before | Reference after | Release that commit is |
|---|---|---|
| `actions/checkout@v4` (6 uses) | `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` | v4.4.0 |
| `actions/setup-python@v5` (2 uses) | `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065` | v5.6.0 |

The SHAs are what the tags resolved to at pin time — `v4` → `v4.4.0`, `v5` →
`v5.6.0`, read with `git ls-remote --tags` and cross-checked with
`GET /commits/{ref}` — so the change alters no behaviour; it only makes the
reference immutable. The newest release of each action was v7.x then; upgrading
is a separate decision and was not taken here. What the pin asserts is that the
named commit was the release at pin time, which rests on the upstream tag
object, not on an independent audit of that commit.

After entry 6 landed, `sha_pinning_required` was set to `true` on the repository
(`PUT /repos/Teancher-H/MonAsm/actions/permissions`; a later `GET` returns
`"sha_pinning_required": true`). The order is forced: with the policy on, the
pull request that introduces the pins cannot run its own checks, because its
base revision still references tags.

### Negative test of the policy

A throwaway branch `he1/pin-negative` was cut from `main` with a single workflow
file whose only content was `uses: actions/checkout@v4` followed by a step that
would print a line. Pushing a branch is not gated, so the push was accepted and
the workflow was started — and then refused. Run `44747579142` concluded
`failure` with its single job listing exactly one step, `Set up job`, and this
message:

```
##[error]The action actions/checkout@v4 is not allowed in Teancher-H/MonAsm
because all actions must be pinned to a full-length commit SHA.
```

The step after the unpinned reference never executed. The branch was then
deleted locally and on the remote, and `git ls-tree -r origin/main` contains no
`pin-negative-probe.yml`, so the file never landed. The rejection happens before
any repository code runs, which is the property that matters: an unpinned gate
step cannot execute at all.

### What is still floating

- The runner image. `ubuntu-latest` and its siblings are moving labels; the
  service, the OS packages and most of the toolchain change underneath a
  pinned workflow. Only the oracle's LLVM release is named explicitly, because
  `apt.llvm.org` tracks the newest release in the series.
- `actions`-owned dependencies of a pinned action — a pinned `checkout` still
  downloads whatever its own code asks for at run time.
- The policy is a repository setting, not an organization or enterprise one; it
  applies here because it was set here.
