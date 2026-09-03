# Repository configuration

What is set on this repository, as the `gh api` call that reads it back
and the answer that call gives today. A setting recorded as prose alone
is one nobody can check; recorded this way, a drift is one command away
from being seen.

What is recorded is the settings [section 11 of the repository
standard](https://github.com/btclib-org/.github/blob/main/README.md#11-github-settings)
asks about — the ones [section 16's
checklist](https://github.com/btclib-org/.github/blob/main/README.md#16-checklists)
sets on a new repository, the ones a section of the standard states a
rule for, and the ones a behaviour it describes rests on — together with
whatever a call quoted for one of those answers alongside it. The
perimeter is section 11's rather than this file's, so a setting inside
it that no section below reads back is a gap rather than a decision, and
*What this file passes over* at the foot is what falls outside it.

## Required checks on main

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection \
  --jq '.required_status_checks | {strict, contexts}'
# {"contexts":["Lint and type-check","test: every job passed",
#              "Build the documentation"],
#  "strict":true}
```

`test: every job passed` is an aggregate rather than a matrix cell.
`test.yml`'s `test-passed` job runs last and demands `success` or
`skipped` of every job the run reports, `!cancelled()` in its `if:`
being what makes a red cell reach it rather than leave it unreported --
while a cancellation of the run itself, superseded by a newer push under
the workflow's concurrency group, skips the gate instead of reaching it,
a skip satisfying this required check the same as a pass. A `skipped`
row is a job the run declined to start rather than one that did not
pass, and section 10 of the standard is where the cases it is legitimate
on are named. Naming the aggregate means `test.yml` can gain or lose a
job without anyone editing branch protection; naming its jobs would mean
this list going stale the first time it changed.

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

One context this repository produces is not in that list, and is meant to
be produced anyway: `codeql.yml`'s `codeql: every job passed`, which
btclib-org/.github#459 asks every code analysis in the organization to
carry. A matrix reports one context per cell, so a rule could only ever
name the cells, and a language added later would fall outside a rule
naming the ones there today; an aggregate is what makes requiring that
analysis an edit to the list above rather than to a workflow. Whether to
make it is branch protection's to answer, and the command above is what
would show it answered.

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

`main` is the repository's default branch and its only one:

```shell
gh api repos/btclib-org/btclib-benchmarks --jq '.default_branch'
# main
```

No change reaches it except through a pull request — no exception, and
no push. `main-integrity` and `main-self-merge` carry that beside the
classic protection above, rules
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
publish-on-tag workflow here to protect — there is no release, as
`CONTRIBUTING.md`'s *A version, and no release* says — so the reason is
consistency rather than a publish trigger: that section's tagging step
says "Signed, as every tag in this organization is", and the ruleset
enforces that rather than leaving it to be remembered by hand. It carries no
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
         delete_on_merge: .delete_branch_on_merge,
         title: .squash_merge_commit_title,
         message: .squash_merge_commit_message}'
# {"auto":true,"delete_on_merge":true,"merge":false,
#  "message":"COMMIT_MESSAGES","rebase":false,"squash":true,
#  "title":"COMMIT_OR_PR_TITLE"}
```

Squash only, which is what `required_linear_history` above already
implies and this makes unambiguous in the UI: one pull request is one
commit on `main`. The ruleset names the same one, so the constraint
holds even if this setting is flipped. Auto-merge is what presses it,
once the review and the checks are in.

`COMMIT_OR_PR_TITLE` with `COMMIT_MESSAGES` is the pair section 11 asks
for: a single-commit branch lands under its own subject and a longer one
under the pull request's title, with the branch's commit messages as the
body — never the pull request's description, which `PR_BODY` would take
with nothing here to show the flip.

`delete_branch_on_merge` deletes the head branch of a pull request
merged *through* the pull request, and every landing here is one, so it
fires on its own and there is nothing to delete by hand. A branch still
standing is a pull request that was closed rather than merged.

## Features

```shell
gh api repos/btclib-org/btclib-benchmarks \
  --jq '{issues: .has_issues, visibility: .visibility}'
# {"issues":true,"visibility":"public"}
```

Issues are on: they are where a benchmark that has stopped measuring
what it claims gets reported, and where a finding noticed while writing or
reviewing a pull request is parked so that the pull request stays one
subject. `CONTRIBUTING.md`'s *The issue tracker* rests on the setting.

Public is the half of section 10's `scorecard` bar a copy reads back,
and this tree runs no `scorecard` sentinel: *What is not configured,
and why* below is that decision, and the answer above is what keeps it
a decision rather than an impediment.

## Topics

```shell
diff <(gh api repos/btclib-org/btclib-benchmarks --jq '.topics[]' | sort) \
     <(sed -n '/^keywords = \[/,/^]/s/^ *"\(.*\)",$/\1/p' pyproject.toml \
       | sort)
```

Section 3 makes a package's `keywords` its
[topics](https://github.com/btclib-org/.github/blob/main/README.md#3-pyprojecttoml-is-the-configuration)
entry for entry, and this `pyproject.toml` declares a `[project]` table, so
`topics_test.py` holds this repository to that comparison. The diff above
is empty: the two lists already agree, sorted because GitHub returns
topics in an order of its own rather than `pyproject.toml`'s relevance
order.

## Token permissions

Every workflow declares `permissions: contents: read` at the top level,
and a job that needs more declares it on itself, so a write is held by
one job for the length of one job rather than by the file around it.
Which jobs those are is read back rather than listed here, a list of them
being wrong from the next workflow that elevates and saying nothing about
it:

```shell
git grep -nE '^ +[a-z-]+: write' -- .github/workflows/
```

Why a particular scope is held is written beside the job that spends it,
where whoever changes that job can see it, rather than here. What this
section adds is the bound those lines are kept under: each of them is one
job's own work — posting a review or a reply, filing a code-scanning
alert, an OIDC token an action asks for at its own startup, opening the
issue a weekly drift check reports through. `actions: read` is the
elevation that is not a write, and what distinguishes it is where a job
reads from — the API rather than the tree — which is the bound, and not
a list of what each one asks the API for.

The bound is what the same command says is absent: no job holds
`contents: write` or `packages: write`. Nothing a run does reaches the
tree or an index — a version is a signed tag a person pushes — and that
is why there is no `publishing` section in this file for a job to sit
under.

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

## Private vulnerability reporting

```shell
gh api repos/btclib-org/btclib-benchmarks/private-vulnerability-reporting
# {"enabled":true}
```

On, [as the standard asks of every
tier](https://github.com/btclib-org/.github/blob/main/README.md#root-files):
it is what puts the *Report a vulnerability* button on the Security tab,
ahead of a `SECURITY.md` this repository does not carry, that file being
tier 1's row.

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

## Plan-gated settings

The ceiling on concurrent jobs is a number the plan decides rather than
anything this repository configures, and this section is its one home
in the tree:

```shell
gh api orgs/btclib-org --jq '{plan: .plan.name}'
# {"plan":"free"}
```

[GitHub's own table](https://docs.github.com/en/actions/reference/limits)
turns that answer into a number, twenty concurrent jobs on the free
plan, and they belong to the organization rather than to this
repository: every repository in it draws on the same twenty. So a matrix
on every commit here is a slot a reviewer in a sibling repository waits
behind, which is the whole argument for a merge that waits on one cell
and a sweep that runs weekly
([btclib-org/.github#85](https://github.com/btclib-org/.github/issues/85)).
Every workflow and document that spends against the ceiling points here
rather than repeating the number. The other plan-gated pair, secret
scanning's non-provider patterns and validity checks, is read back under
*Security and analysis* above.

## What is not configured, and why

- **No PyPI publishing, and no release workflow.** `CONTRIBUTING.md`'s
  *A version, and no release* is the whole of that answer. The `check`
  dependency group exists so that `check-sdist`, `pyroma` and `twine`
  can still inspect the distribution and its metadata, which is a lint
  of the packaging rather than a step toward a release.
- **No GitHub Pages.** `gh api repos/btclib-org/btclib-benchmarks/pages`
  answers `404`: the pages under `results/` are read in the tree, and
  nothing deploys a site from it.
- **No Read the Docs.** `.readthedocs.yaml` is present and the `docs`
  group builds, so the sphinx gate is runnable, but no service is
  subscribed to this repository.
- **No benchmark on a schedule.** Several workflows here run weekly and
  none of them times anything; `CONTRIBUTING.md`'s "What the suite can
  and cannot check" is where that rule and its reason are written down.
- **No `scorecard.yml`, and no OpenSSF Scorecard badge.** The two are
  one membership in section 10 of the repository standard, whose *Which
  trees carry which sentinel* does not name this repository for
  `scorecard`: what the run buys is an opinion of the tree's
  supply-chain posture formed outside the organization, and a reading
  nobody displays is not worth the run
  ([btclib-org/.github#490](https://github.com/btclib-org/.github/issues/490)).
  The half of the bar a copy reads back, `.visibility` under *Features*
  above, answers `public`, so the absence is a decision rather than an
  impediment.
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

## What this file passes over

*What is not configured, and why* above is what this repository decided
against. This section is the other edge of the scope at the top: what an
endpoint answers for this repository and no section here asks about.

**Most of the repository document is not a setting.** `gh api
repos/btclib-org/btclib-benchmarks` answers it whole, and the greater
part of what comes back is URLs, counts, timestamps and state GitHub
derives from the tree. No call here reads any of that back, a scope of
the settings the standard asks about reaching none of it.

**A field of that document no rule reaches.** `allow_forking`,
`allow_update_branch`, `has_discussions`, `has_downloads`, `is_template`
and `web_commit_signoff_required` are in it, in none of this file's
`--jq` objects, and named nowhere in the standard:

```shell
std=$(gh api repos/btclib-org/.github/contents/README.md \
        -H 'Accept: application/vnd.github.raw')
for f in allow_forking allow_update_branch has_discussions has_downloads \
         is_template web_commit_signoff_required; do
  printf '%s %s %s\n' "$f" \
    "$(printf '%s' "$std" | grep -c "$f")" "$(grep -c "\.$f" REPOSITORY.md)"
done
# every line reads "<field> 0 0"
printf '%s' "$std" | grep -c squash_merge_commit_title   # 1
grep -c '\.allow_squash[_]merge' REPOSITORY.md           # 1
```

The two counts under the loop are what make its zeros absences: a field
the standard does state a rule about, and a field this file does quote
in a `--jq` object, the bracket in the second keeping that line from
matching itself. Recording a field on no rule grows this file with
GitHub's API rather than with the standard.

`has_wiki` and `has_projects` are outside the perimeter by section 11's
own sentence, which states no rule about either, so this file neither
reads them back nor explains an answer to them; that sentence is what
the loop above would count, which is why the pair is not in its list.

**A field the standard scopes to a releasing tree.** `.homepage` is the
*About* link on this repository's page and `pyproject.toml`'s
`[project.urls] homepage` is the same URL, so what is checkable here is
that the two surfaces still agree:

```shell
diff <(gh api repos/btclib-org/btclib-benchmarks --jq '.homepage') \
     <(sed -n '/^\[project.urls\]/,/^\[/p' pyproject.toml \
       | sed -n 's/^homepage = "\(.*\)"$/\1/p')
```

The diff above is empty. Which URL it is, and why it is the
organization site rather than something of this tree's, is at that key
in `pyproject.toml` and nowhere here: no limb of the scope at the top
reaches the field in a tree that releases nothing, so this file holds it
to no value. Section 3 of the standard states its rule of "a releasing
tree's `homepage`" and says of a tree that releases nothing that it
"publishes no URL that outlives a correction, so this asks it nothing";
section 16's checklist sets the field "where the tree releases"; and
section 11 calls it "a releasing tree's" where it names what a copy
records that has another form in the tree. *What is not configured, and
why* above is this repository's answer to releasing.

**A credential this repository does not hold.** `claude-review.yml` reads
`secrets.CLAUDE_CODE_OAUTH_TOKEN` and `vars.CLAUDE_REVIEW_ENABLED`, and
section 11 of the standard makes both the organization's rather than each
repository's:

```shell
gh api repos/btclib-org/btclib-benchmarks/actions/secrets \
  --jq '.total_count'
# 0
gh api repos/btclib-org/btclib-benchmarks/actions/variables \
  --jq '.total_count'
# 0
gh api orgs/btclib-org/actions/secrets \
  --jq '.secrets[] | "\(.name) \(.visibility)"'
# CLAUDE_CODE_OAUTH_TOKEN all
gh api orgs/btclib-org/actions/variables --jq '.variables[].name'
# (nothing)
gh api orgs/btclib-org/actions/variables --jq '.total_count'
# 0
```

The organization's secret store answering with a name is what makes this
repository's two zeros an absence rather than an endpoint that answers
empty for everyone. The variable store prints nothing at all when it
answers, so its own `total_count` of `0` is what shows the call reached
it: one that does not reach it prints an error and exits non-zero.
Section 11 reads that empty name list as `vars.CLAUDE_REVIEW_ENABLED`'s
off state, an undefined `vars.X` being the empty string. Both stores are
read because a variable set here would take precedence over one of the
same name set on the organization, so the organization's answer alone
would not show the switch off for this tree.

**A facility nothing here uses.** Environments, self-hosted runners,
webhooks, deploy keys, autolinks and custom property values each answer
empty, and an empty answer records no decision. Whichever of them a
workflow needs one day arrives with the section that uses it.

What the scope costs is that a change to any of the above fails no
command here: what finds one is somebody reading the repository document
and the stores above against this file.
