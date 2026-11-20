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

- **The queue closes the tested/landed gap; approval and provenance do not.**
  Entries 1 and 2 predate the queue and establish only that under strict
  up-to-date the landed tree equals the tested tree. Entry 3 is a queued merge
  where the landed commit *is* the tested commit, so on that path the two cannot
  diverge. What remains is independent authorization:
  `required_approving_review_count` is 0, and the same account writes, merges
  and administers, so the merge is enforced but not independently approved.
  `AuthorizedMerge(B,T,e,M)` is therefore still not satisfied.
- **Gate logic provenance is still weak.** The workflows reference
  `actions/checkout@v4` and `actions/setup-python@v5` by mutable tag, and
  `sha_pinning_required` is still `false`. The ruleset makes the workflow files
  change-controlled (they can only land through a PR whose checks pass, and now
  through the queue) but does not pin what the actions resolve to.
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
entry when one is added. Four consecutive entries show this is not a single-run
accident: two merges under strict up-to-date and two through the queue. Every
merge after entry 1 went through this channel.

| Entry | PR | Tested tree | Landed commit | Landed tree | Equal |
|---|---|---|---|---|---|
| 1 | #9 | `88c65951b350a513247338a3fdda1d470d677933` | `c9ae2648e5230f0ba79c6be4919806b20763959d` | `88c65951b350a513247338a3fdda1d470d677933` | yes |
| 2 | #10 | `cdcbd458b6508080e99f5605da139060de5b6c0c` | `e3fef895fb464a123eff6c8bc375f23cbc5b1a30` | `cdcbd458b6508080e99f5605da139060de5b6c0c` | yes |
| 3 | #12 | `b5cbcd7f9aa120cc5f07099992a6d531b690fd71` | `cc7674206da2032eb6602c94fa760ca5a16fb60e` | `b5cbcd7f9aa120cc5f07099992a6d531b690fd71` | yes |
| 4 | #13 | `4f5322d81b0a7561cd6450f413dd88ce32fbeb4e` | `0d07288aabd5b38b4e155b2ef92c923cee8b3917` | `4f5322d81b0a7561cd6450f413dd88ce32fbeb4e` | yes |

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

The first two queued merges are entries 3 and 4; their values are recorded by the
changes that follow them, as §6 explains.
