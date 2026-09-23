# Maintaining this list

## Checks

```bash
make check        # rules, table of contents, and the list's own tests
make links        # lychee over every entry
make toc          # regenerate the Contents section
```

The pre-commit hook runs the fast checks, the pre-push hook runs all of them.

## Weekly link check

`jobs/links.sh` checks every entry, writes `.state/links-report.md`, and with
`--open-issue` opens or updates one issue when something breaks, then closes it
when the list is clean again.

To run it weekly without a hosted runner:

```bash
mkdir -p ~/Library/LaunchAgents
sed "s|__REPO__|$PWD|g" schedule/launchd/links.plist \
  > ~/Library/LaunchAgents/nz.olitreadwell.awesome-kiwi-data.links.plist
launchctl load ~/Library/LaunchAgents/nz.olitreadwell.awesome-kiwi-data.links.plist
```

A laptop that is asleep at the scheduled hour runs the job on the next wake.

## Adding an entry

1. Add the bullet in the shape the Legend describes.
2. `make check`.
3. Open `README.md` in a branch and let the pre-push hook do its job.
