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

Three contexts, and the second is an aggregate rather than a matrix cell.
`test.yml`'s `test-passed` job runs last and demands `success` of every
job the run reports, `!cancelled()` in its `if:` being what makes a red
cell reach it rather than leave it unreported -- while a cancellation of
the run itself, superseded by a newer push under the workflow's
concurrency group, skips the gate instead of reaching it, a skip
satisfying this required check the same as a pass. Naming the aggregate
means the matrix can gain or lose a cell without anyone editing branch
protection; naming the cells would mean this list going stale the first
time it changed.

What it judges is therefore not what `needs` waits for, and the two are
the same set only while that workflow has two jobs. So the rule is that
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
request — no exception, and no push. Two rulesets carry that beside the
classic protection above, rules aggregating across the two and the most
restrictive combination winning wherever they overlap — a third,
`tag-integrity`, is described further down and targets tags rather than
`main`, so the command below lists it too without it being one of these
two:

```shell
gh api repos/btclib-org/btclib-benchmarks/rulesets --jq '.[].id' \
  | xargs -I{} gh api repos/btclib-org/btclib-benchmarks/rulesets/{} \
    --jq '{name, rules: [.rules[].type],
           bypass: [.bypass_actors[].bypass_mode]}'
```

- `main-integrity` — required signatures, required linear history, no
  force pushes, no deletions — with **no bypass actor at all**, which is
  what makes those four true of an administrator too.
- `main-self-merge` — require a pull request, one approving review,
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
and one job elevates it: `test.yml`'s `test-passed` adds `actions:
read`, which is what lets it ask the run what its own jobs concluded
rather than trust the needs context — the reason is under *Required
checks on main* above. Nothing in this repository publishes, attests, or
writes to the repository itself, so no job holds a write scope of any
kind — which is a smaller surface than the other btclib-org repositories
have, and the reason there is no `publishing` section here.

## What is not configured, and why

- **No PyPI publishing, and no release workflow.** Nothing is installed
  from this project: `[tool.setuptools] packages = []`, and the scripts
  are run from a checkout. The `build` dependency group exists so that
  `check-manifest`, `pyroma` and `twine` can still inspect the metadata,
  which is a lint of the packaging rather than a step toward a release.
- **No Read the Docs.** `.readthedocs.yaml` is present and the `docs`
  group builds, so the sphinx gate is runnable, but no service is
  subscribed to this repository.
- **No CodeQL.** It analyses a library's own code for vulnerabilities;
  what is here is six scripts that time other people's packages, and
  the packages they time are analysed where they live.
- **No scheduled workflow.** Nothing here should run without someone
  asking: a benchmark on a shared runner is a number produced under
  conditions nobody recorded.
