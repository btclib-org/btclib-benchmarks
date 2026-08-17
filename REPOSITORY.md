# Repository configuration

What is set on this repository, as the `gh api` call that reads it back
and the answer that call gives today. A setting recorded as prose alone
is one nobody can check; recorded this way, a drift is one command away
from being seen.

## Required checks on main

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection \
  --jq '.required_status_checks | {strict, contexts}'
# {"contexts":["Lint and type-check","test: every job passed"],
#  "strict":true}
```

Two contexts, and the second is an aggregate rather than a matrix cell.
`test.yml`'s `test-passed` job runs last and demands `success` of every
job the run reports, `always()` in its `if:` being what makes a red cell
reach it rather than leave it unreported. Naming the aggregate means the
matrix can gain or lose a cell without anyone editing branch protection;
naming the cells would mean this list going stale the first time it
changed.

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

`main` is the only branch, and nothing is pushed to it directly.

`enforce_admins` is false, and that is the one entry here that is a
compromise rather than a rule: this repository has one maintainer, so a
required review cannot be satisfied in the ordinary way. The rule stays
on — it is what a second contributor would meet — and the maintainer
merges their own pull request with `gh pr merge --squash --admin`, after
the checks above have gone green. What that buys over simply turning the
requirement off is that the checks are still required of everyone,
including him.

## Signed commits

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection\
/required_signatures --jq '.enabled'
# true
```

An unsigned commit is refused by the push rather than noticed later.
Note what this cannot cover: a squash performed by GitHub's web button is
signed by GitHub's own web-flow key, not by the maintainer's, and shows
as verified by GitHub. That is a property of the merge, not something to
paper over.

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
commit on main. The head branch is deleted by the merge, so a branch
still present after one is a merge that did not happen.

## Features that are off

```shell
gh api repos/btclib-org/btclib-benchmarks \
  --jq '{wiki: .has_wiki, projects: .has_projects, issues: .has_issues}'
# {"issues":true,"projects":false,"wiki":false}
```

A wiki is a second place for documentation to go stale, and this
repository's documentation is in the tree beside what it describes.
Issues stay on: they are where a benchmark that has stopped measuring
what it claims gets reported.

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
  what is here is five scripts that time other people's packages, and
  the packages they time are analysed where they live.
- **No scheduled workflow.** Nothing here should run without someone
  asking: a benchmark on a shared runner is a number produced under
  conditions nobody recorded.
