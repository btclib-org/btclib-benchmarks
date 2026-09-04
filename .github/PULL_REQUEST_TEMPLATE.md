<!-- markdownlint-disable-next-line first-line-heading -->
## What this changes

<!-- What the code does now that it did not do before, and why.
     Link the issue it closes, if there is one: "Closes #123". -->

## How it was verified

<!-- The test that covers it, the vector it reproduces, the command you
     ran. New behaviour without a test is the usual reason a pull request
     waits. -->

## Checks

<!-- CI runs all of this and rejects the pull request if any of it fails:
     the point of running it locally is not to wait for CI to say so. -->

- [ ] the lint gate is clean: `uv run pre-commit run --all-files`
- [ ] the suite passes, with its coverage gate: `uv run pytest`
- [ ] the documentation builds: `uv run --locked --only-group docs
      sphinx-build -W -n -b html docs/source docs/build/html`
- [ ] `CHANGELOG.md` has an entry, if a user would notice the change
- [ ] every commit carries a verified signature

## Anything the reviewer should know

<!-- A decision you are unsure of, an alternative you rejected, a
     specification that is ambiguous, a follow-up you left out on
     purpose. Delete the section if there is none. -->
