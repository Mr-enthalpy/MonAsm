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

- **N5a is still unsatisfied.** `AuthorizedMerge(B,T,e,M)` needs a merge path
  whose tested and landed objects cannot diverge. Without a queue there is a
  residual window; with no second reviewer there is no independent approval.
- **Gate logic provenance is still weak.** The workflows reference
  `actions/checkout@v4` and `actions/setup-python@v5` by mutable tag, and
  `sha_pinning_required` is still `false`. The ruleset makes the workflow files
  change-controlled (they can only land through a PR whose checks pass) but does
  not pin what the actions resolve to. Pinning is a separate change.
- **A workflow change is still judged by the workflow it introduces.** For
  `pull_request` events the checks come from the PR head's own workflow files.
  The ruleset makes such a change reviewable and recorded; it does not make the
  change self-verifying.
- **No stale-CI counterexample is recorded here.** Demonstrating that an
  out-of-date PR is refused requires a controlled base advance during a run and
  belongs to the N5a evidence set, not to this log.
- **No claim about other branches, tags, organization policy, or audit logs.**

## 6. Log

Entries are appended by the change that merges *after* the one being described,
because a commit cannot contain its own merge SHAs. Entry 1 is recorded in the
next change to this file.

| Entry | PR | Tested tree | Landed commit | Landed tree | Equal |
|---|---|---|---|---|---|
| 1 | this PR | pending next entry | pending next entry | pending next entry | pending |
