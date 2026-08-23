# Repository configuration

What is set on this repository, as the `gh api` call that reads it back
and the answer that call gives today. A setting recorded as prose alone
is one nobody can check; recorded this way, a drift is one command away
from being seen.

## Required checks on main

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection \
  --jq '.required_status_checks | {strict, contexts}'
# {"contexts":["Lint and type-check","test: every job passed",
#              "Build the documentation"],
#  "strict":true}
```

`test: every job passed` is an aggregate rather than a matrix cell.
`test.yml`'s `test-passed` job runs last and demands `success` of every
job the run reports, `!cancelled()` in its `if:` being what makes a red
cell reach it rather than leave it unreported -- while a cancellation of
the run itself, superseded by a newer push under the workflow's
concurrency group, skips the gate instead of reaching it, a skip
satisfying this required check the same as a pass. Naming the aggregate
means `test.yml` can gain or lose a job without anyone editing branch
protection; naming its jobs would mean this list going stale the first
time it changed.

What it judges is therefore not what `needs` waits for, and the two sets
coincide only for as long as `test-passed` is the workflow's only other
job. So the rule is that
whatever the gate can see it has to wait for: it allows exactly one
unfinished job, which is itself, and a job of the run outside its
`needs` turns it red until it is added there. Counted rather than
excluded by name, a name being what goes stale when this job is renamed
— and refused when nothing is unfinished at all, because a listing with
no job running is not describing the run the gate is running in.

What that job must not do is decide from `needs.*.result`, which is how
it was written until an outage showed what that context can miss. With
codeload answering 503 and then 429, a cell died in "Set up job" with
the download of an action abandoned after three attempts; the job is red
in the run, the failure never reached the needs context, and the step
that fails the gate was skipped. The one required check went green over
a red matrix, twice.

It is not that every setup failure does this — a cell pointed at an
action SHA that does not exist dies in the same step and does arrive as
`failure`, which was worth measuring before writing the fix — and a cell
that fails in a step of its own always did. That is why the hole stayed
hidden until GitHub had an outage, and why the fix does not try to
enumerate the ways a job can die: the job asks the API what this run's
jobs concluded, and a conclusion is a conclusion however it was reached.

The third is `docs.yml`'s only job, and it is named directly because
there is only one — an aggregate over a single cell would be a job
whose whole purpose is to repeat another's answer. It runs the
`sphinx-build -W` command `.readthedocs.yaml` already runs, on the
interpreter that file pins, so a cross-reference this project's
`{include}`-based pages cannot resolve fails here rather than only on
Read the Docs, after the merge, on a page nobody watches. That was not
hypothetical: the pull request that filed [ISS 95][iss95] hit it twice,
and only because the build was run by hand.

[iss95]: https://github.com/btclib-org/btclib-benchmarks/issues/95

Its `if:` declines two cases, and neither is a hole this rule can fall
through. A draft pull request spends no runner, and a draft cannot merge
anyway — marking it ready fires the workflow again. A `closed` event
skips the job too, which is why the check reads as skipped on a pull
request that has just merged: the run is triggered so that the merge
cancels anything the ref's concurrency group is still holding, and it
arrives at the merge rather than before it. On an open pull request the
job runs, and there is no `paths` filter for it to sit out.

`strict` requires a branch to be up to date with main before it merges.

## Branch protection

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection \
  --jq '{
    linear: .required_linear_history.enabled,
    force: .allow_force_pushes.enabled,
    deletions: .allow_deletions.enabled,
    conversations: .required_conversation_resolution.enabled,
    reviews: .required_pull_request_reviews.required_approving_review_count,
    dismiss: .required_pull_request_reviews.dismiss_stale_reviews,
    admins: .enforce_admins.enabled}'
# {"admins":false,"conversations":true,"deletions":false,"dismiss":true,
#  "force":false,"linear":true,"reviews":1}
```

`main` is the only branch, and no change reaches it except through a pull
request — no exception, and no push. `main-integrity` and
`main-self-merge` carry that beside the classic protection above, rules
aggregating across rulesets and the most restrictive combination winning
wherever they overlap — `tag-integrity`, described further down, targets
tags rather than `main`, so the command below lists it too without it
enforcing anything on `main` itself:

```shell
gh api repos/btclib-org/btclib-benchmarks/rulesets --jq '.[].id' \
  | xargs -I{} gh api repos/btclib-org/btclib-benchmarks/rulesets/{} \
    --jq '{name, rules: [.rules[].type],
           bypass: [.bypass_actors[].bypass_mode]}'
```

- `main-integrity` — required signatures, required linear history, no
  force pushes, no deletions — with **no bypass actor at all**, which is
  what makes every one of those true of an administrator too.
- `main-self-merge` — require a pull request, an approving review,
  stale reviews dismissed, conversations resolved — bypassed by the
  maintainer in **`pull_request` mode**, and naming `squash` as the only
  merge method it will accept.

**The bypass mode is the whole of the design.** `pull_request` excuses
its holder from the rule *while merging a pull request* and at no other
time, so it answers the one thing a one-maintainer repository cannot do
— produce an approving review from somebody else — and answers nothing
further. A direct push to `main` is refused for everyone, the holder
included.

`enforce_admins` is false, and that is what clears the *classic*
protection's own review requirement for the maintainer; the ruleset
bypass alone would not be enough, and turning it on would deadlock every
merge instead, that requirement having no bypass list to be named in.

What lands, therefore, is a squash GitHub composes at the button and
signs with its own web-flow key. That the signer is GitHub rather than
the maintainer costs nothing: `main-integrity` asks for a signature and
not for a particular signer, and asks it of everyone.

A third ruleset, `tag-integrity`, targets tags rather than `main` and so
sits outside the aggregation above: `target: tag`, `refs/tags/v*`,
`required_signatures`, **no bypass actor at all**. There is no
publish-on-tag workflow here to protect — RELEASING.md says as much,
"there is no release" — so the reason is consistency rather than a
publish trigger: RELEASING.md's own tagging step already says "Signed,
as every tag in this org is", and the ruleset now enforces that
uniformly rather than leaving it to be remembered by hand. It carries no
`deletion` or `non_fast_forward` rule, matching the sibling repositories
that do gate a release on the tag.

## Signed commits

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection\
/required_signatures --jq '.enabled'
# true
```

An unsigned commit is refused by the push rather than noticed later — of
everyone the protections are enforced against, which by the section above
is everyone but the maintainer. What holds for that account is reading the
commit before pushing it, `git log -1 --format='%G? %GS'`, an `N` being a
defect to fix rather than to explain.

Note what none of this can cover: a squash performed by GitHub's web button —
or by `gh pr merge`, which asks the same endpoint — is signed by GitHub's
own web-flow key, not by the maintainer's, and shows as verified by
GitHub. That is a property of the merge rather than something to paper
over, and it is why the procedure above lands a commit that already
exists instead of asking the forge to write one.

## Merge methods

```shell
gh api repos/btclib-org/btclib-benchmarks \
  --jq '{squash: .allow_squash_merge, merge: .allow_merge_commit,
         rebase: .allow_rebase_merge, auto: .allow_auto_merge,
         delete_on_merge: .delete_branch_on_merge}'
# {"auto":true,"delete_on_merge":true,"merge":false,"rebase":false,
#  "squash":true}
```

Squash only, which is what `required_linear_history` above already
implies and this makes unambiguous in the UI: one pull request is one
commit on `main`. The ruleset names the same one, so the constraint
holds even if this setting is flipped. Auto-merge is what presses it,
once the review and the checks are in.

`delete_branch_on_merge` deletes the head branch of a pull request
merged *through* the pull request, and every landing here is one, so it
fires on its own and there is nothing to delete by hand. A branch still
standing is a pull request that was closed rather than merged.

## Features that are off

```shell
gh api repos/btclib-org/btclib-benchmarks \
  --jq '{wiki: .has_wiki, projects: .has_projects, issues: .has_issues}'
# {"issues":true,"projects":false,"wiki":false}
```

A wiki is a second place for documentation to go stale, and this
repository's documentation is in the tree beside what it describes.
Issues stay on: they are where a benchmark that has stopped measuring
what it claims gets reported, and where a finding noticed while writing or
reviewing a pull request is parked so that the pull request stays one
subject.

## Token permissions

Every workflow declares `permissions: contents: read` at the top level,
and some jobs elevate it: `test.yml`'s `test-passed` adds `actions:
read`, which is what lets it ask the run what its own jobs concluded
rather than trust the needs context — the reason is under *Required
checks on main* above; `claude-review.yml`'s `review` and `mention` jobs
add `pull-requests: write`, which is what posting a review or a reply
takes. Nothing in this repository publishes, attests, or writes to the
repository's contents, so no job holds a scope wider than commenting on
a pull request — which is a smaller surface than the other btclib-org
repositories have, and the reason there is no `publishing` section here.

What those declarations sit on top of is a repository setting, and it is
read back rather than assumed:

```shell
gh api repos/btclib-org/btclib-benchmarks/actions/permissions/workflow
# {"default_workflow_permissions":"read",
#  "can_approve_pull_request_reviews":false}
```

`read`, so a job that declares nothing gets nothing beyond reading the
tree, and the workflow-level blocks above are the braces rather than the
belt. `can_approve_pull_request_reviews` is false, which matters as much:
a run that can approve a pull request is a way around the rule that
somebody other than the author approves.

What the call cannot say is whether either value is this repository's own
or the organization's, no endpoint reporting an override and none
clearing one: [the standard's tokens
section](https://github.com/btclib-org/.github/blob/main/README.md#tokens-publishing-scanning)
is where that is argued, and what this file adds is which of the two
states this repository is in.

It is **untested**, and the date is what makes it so: this repository
already held `read` when the organization default moved there on
21 August 2026, so it was not among the ones that could be *seen*
following the move, and an override set before that day reads back
exactly like an inheritance does. Nobody has recorded setting one here,
which is weaker than knowing there is none — `bitcoin-core-rpc` is the
repository where one was found, by that same move, and its
`REPOSITORY.md` records it as pinned.

So whoever moves the organization default reads this repository back
afterwards rather than assuming it followed, and moves it by hand where
it did not:

```shell
gh api -X PUT \
  repos/btclib-org/btclib-benchmarks/actions/permissions/workflow \
  -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=false
```

## Security and analysis

```shell
gh api repos/btclib-org/btclib-benchmarks --jq '.security_and_analysis'
# {"dependabot_security_updates":{"status":"enabled"},
#  "secret_scanning":{"status":"enabled"},
#  "secret_scanning_non_provider_patterns":{"status":"disabled"},
#  "secret_scanning_push_protection":{"status":"enabled"},
#  "secret_scanning_validity_checks":{"status":"disabled"}}
```

Three settings, all free on a public repository, off by default, and
now on: secret scanning, its push protection, and Dependabot security
updates. Push protection is the one that matters most — it refuses the
push rather than reporting a secret that already reached the remote —
and this repository has no `detect-secrets` hook standing in the way it
does on `btclib`, `btclib-secp256k1` and `bitcoin-core-rpc`, so nothing
local caught a leaked fixture before this did.

`secret_scanning_non_provider_patterns` and
`secret_scanning_validity_checks` are a different pair: a `PATCH`
answers them with 200 while leaving them `disabled`, paid Secret
Protection being what they need. They are not the three above and stay
off deliberately — read back, not merely patched, which is what the
command above is for.

Dependabot security updates is a separate `PUT`, to
`vulnerability-alerts` and then `automated-security-fixes`, neither of
which `security_and_analysis` itself accepts:

```shell
gh api -X PUT repos/btclib-org/btclib-benchmarks/vulnerability-alerts
gh api -X PUT \
  repos/btclib-org/btclib-benchmarks/automated-security-fixes
```

Read back with no existing secret-scanning alert on this repository:

```shell
gh api repos/btclib-org/btclib-benchmarks/secret-scanning/alerts \
  --jq 'length'
# 0
```

From the alignment audit of 21 August 2026,
[btclib-org/.github#5](https://github.com/btclib-org/.github/issues/5).

## Code scanning, and which setup performs it

```shell
gh api repos/btclib-org/btclib-benchmarks/code-scanning/default-setup \
  --jq '{state, languages, query_suite}'
# {"languages":["actions","python"],"query_suite":"default",
#  "state":"not-configured"}
```

`state: not-configured` is what has to stay true, and it is the one
setting `codeql.yml` depends on: default setup and an advanced workflow
are exclusive, and the collision is at the upload rather than at the
start — a run would build its database, be refused the SARIF, and report
failure. The `languages` and `query_suite` fields are what the setting
*would* analyse if it were turned on, which is why `codeql.yml` matches
them: turning it on and off again then changes nothing but which file
the configuration is read from.

The alerts, once there are runs to produce them:

```shell
gh api repos/btclib-org/btclib-benchmarks/code-scanning/alerts \
  --jq 'length'
```

## The concurrent-job ceiling

```shell
gh api orgs/btclib-org --jq '{plan: .plan.name}'
# {"plan":"free"}
```

Twenty concurrent jobs is what GitHub's documented usage limits give
that plan, and they belong to the organization rather than to this
repository: every repository in it draws on the same twenty. So a matrix
on every commit here is a slot a reviewer in a sibling repository waits
behind, which is the whole argument for a merge that waits on one cell
and a sweep that runs weekly
([btclib-org/.github#85](https://github.com/btclib-org/.github/issues/85)).
Every workflow and document that spends against the ceiling points here
rather than repeating the number, `claude-review.yml` excepted while
btclib-org/.github#91 is open: a pull request that edits that file is
refused a review by it, so its copy of the number cannot be taken out
here.

## What is not configured, and why

- **No PyPI publishing, and no release workflow.** Nothing is installed
  from this project: `[tool.setuptools] packages = []`, and the scripts
  are run from a checkout. The `build` dependency group exists so that
  `check-manifest`, `pyroma` and `twine` can still inspect the metadata,
  which is a lint of the packaging rather than a step toward a release.
- **No Read the Docs.** `.readthedocs.yaml` is present and the `docs`
  group builds, so the sphinx gate is runnable, but no service is
  subscribed to this repository.
- **No benchmark on a schedule.** Several workflows here run weekly and
  none of them times anything; `CONTRIBUTING.md`'s "What the suite can
  and cannot check" is where that rule and its reason are written down.
- **No `windows.yml`, where the other repositories have one.** Two
  comparands cannot be installed on a Windows runner at all, so every
  cell of that matrix would be red on `uv sync` and the workflow could
  never go green. `secp256k1` publishes no Windows wheel, and its sdist
  refuses outright without `pkg-config` before running libsecp256k1's
  `configure`, an autotools shell script; `electrum-ecc` publishes no
  wheel anywhere and skips compiling libsecp256k1 on `win32`, so it
  installs and then fails to import for want of the library it wraps.
  The two halves of the first, re-derived:

  ```shell
  curl -s https://pypi.org/pypi/secp256k1/json |
    jq '[.urls[].filename | select(test("win"))] | length'
  # 0
  gh api -X GET search/code --jq .total_count \
    -f q='pkgconf repo:actions/runner-images path:images/windows'
  # 0
  ```

  The day both answers stop being zero, this workflow is `os-macos.yml`
  with the images and the schedule swapped.
- **No `mutation.yml`, and no mutation configuration.** The subject
  exists — the helper modules under `scripts/` are what the 100%
  ratchet in `[tool.coverage.report]` holds, and mutation testing is
  exactly the question coverage does not answer of them — but a
  workflow whose configuration is not in the tree is a workflow with
  nothing to run. Adding the `cosmic-ray` dependency group and the
  scope, the test command and the operator filters that go with it is a
  decision about what to mutate, made with the survivor list in front of
  whoever makes it.
