# Recurring movement pulse adapters

`vcs-tree history pulse` is a read-only observation step. A host may run it
interactively, from a background process, or on a schedule, but the package
owns snapshot selection, comparison, warning semantics, task-path evidence,
and exit meanings. Hosts consume the result; they do not reinterpret it.

The examples below use explicit roots so a cloud-synchronized repository tree
does not accidentally receive machine-local control state. The source tree is
read-only. The state root is authoritative, machine-local, and single-writer;
do not put it on a shared/cloud drive or run overlapping writers. A lock in the
host is still useful to prevent two scheduled invocations from racing.

Initialize a new state root once on the machine that will own the writer:

```sh
vcs-tree history init --state-root "$HOME/.local/state/vcs-tree"
```

The pulse command does not repair an uninitialized or corrupt store.

## Invocation shapes

### Foreground summary

```sh
uv run vcs-tree history pulse "$HOME/Documents" \
  --state-root "$HOME/.local/state/vcs-tree" \
  --format summary
```

The default summary is for a person. Exit `0` covers a complete baseline,
movement, or empty result; movement is not a process failure.

### Consumer JSON with a separate log

```sh
set +e
uv run vcs-tree history pulse "$HOME/Documents" \
  --state-root "$HOME/.local/state/vcs-tree" \
  --format json \
  >"$HOME/.local/state/vcs-tree/latest.json" \
  2>"$HOME/.local/state/vcs-tree/latest.stderr"
status=$?
set -e
case "$status" in
  0|3) jq '.outcome, .movement' "$HOME/.local/state/vcs-tree/latest.json" ;;
  4) printf '%s\n' "pulse failed; inspect latest.stderr and history inspect" >&2 ;;
  *) printf 'unexpected vcs-tree exit: %s\n' "$status" >&2 ;;
esac
exit "$status"
```

The JSON document is the machine contract. Inspect `outcome.state` and
`movement.state` instead of treating observed movement as failure. Exit `3`
means usable facts exist but the result is partial and includes uncertainty.
Exit `4` means no trustworthy pulse completed. Exit `2` is command-line usage
error and has no pulse contract.

### Argument contract

| Concern | Argument or host choice | Meaning |
| --- | --- | --- |
| Scan root | positional `path` | Read-only directory tree to inspect |
| State root | `--state-root PATH` | Machine-local authoritative ledger/index |
| Comparison source | `--from SNAPSHOT` | Explicit baseline; otherwise the exact predecessor is selected |
| Human output | `--format summary` | Signal-first operator view |
| Review output | `--format audit` | Includes no-op repositories and evidence details |
| Consumer output | `--format json` | Complete canonical pulse document |
| Enrichment bound | `--max-enrichment-objects N` | Caps immutable-object descriptions |
| Path bound | `--max-changed-paths N` | Caps changed-path evidence per object |

Limits make a result partial when evidence is suppressed; they do not change
the underlying snapshot or delete retained facts.

## Thin scheduler examples

These are host examples only. They add no scheduler dependency and do not
define retry, notification, priority, or health policy.

### Cron

```cron
17 * * * * flock -n "$HOME/.cache/vcs-tree/pulse.lock" \
  sh -c 'vcs-tree history pulse "$HOME/Documents" \
    --state-root "$HOME/.local/state/vcs-tree" --format json \
    >"$HOME/.local/state/vcs-tree/latest.json" \
    2>"$HOME/.local/state/vcs-tree/latest.stderr"'
```

`flock` is optional host-side serialization. The command's exit status and
JSON remain unchanged.

### launchd

```xml
<key>ProgramArguments</key>
<array>
  <string>/usr/local/bin/vcs-tree</string>
  <string>history</string><string>pulse</string>
  <string>/Users/me/Documents</string>
  <string>--state-root</string><string>/Users/me/.local/state/vcs-tree</string>
  <string>--format</string><string>json</string>
</array>
<key>StandardOutPath</key>
<string>/Users/me/.local/state/vcs-tree/latest.json</string>
<key>StandardErrorPath</key>
<string>/Users/me/.local/state/vcs-tree/latest.stderr</string>
```

Use a host lock or launchd policy if overlapping invocations are possible.

## Recovery and inspection

Do not delete or repair retained state as a first response. First inspect the
resolved store and its integrity, then inspect the retained index:

```sh
vcs-tree history inspect --state-root "$HOME/.local/state/vcs-tree"
vcs-tree history list --state-root "$HOME/.local/state/vcs-tree"
```

If automatic predecessor selection is ambiguous or a run was interrupted,
choose the known retained snapshot explicitly:

```sh
vcs-tree history pulse "$HOME/Documents" \
  --state-root "$HOME/.local/state/vcs-tree" \
  --from snapshot-<known-id> --format audit
```

An operational failure (`4`) should be recorded and investigated by the host;
it must not trigger source-repository writes. A partial result (`3`) is still
usable evidence and should remain available to its consumer. Hosts may decide
what to do next, but this guide intentionally does not prescribe progress,
health, priority, notification, or retry judgments.
