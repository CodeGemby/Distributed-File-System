# Fault-Tolerant Distributed File System — Technical Audit

**Audit date:** 2026-10-24  
**Scope:** Supplied project files in this workspace. Source review only; no runtime tests were executed.

## 1. Architecture summary

The implementation is a single Flask master (`master/master.py`, port 5000) coordinating five Flask storage-node processes (`node1/server.py` through `node5/server.py`, ports 5001–5005). The master keeps a hard-coded list of localhost node URLs and in-memory status/manual-toggle maps. Each node saves uploaded files under a relative `../storage/nodeN` path and offers status, upload, list, download, storage-size, and delete endpoints. A React/Vite dashboard polls the master for status and file lists, uploads through the master, links to a node for downloads, and exposes a node toggle control.

This is a centralized coordinator with per-node local directories, not a replicated consensus or metadata service. Replica placement is chosen randomly at upload time. There is no durable metadata store or configuration/discovery layer in the supplied code. The dashboard's primary visible node toggle calls the master's `/toggle_node`; `NodeMonitor.jsx` contains a separate local-only toggle implementation and is not mounted by `main.jsx`.

The supplied material does not contain a top-level README, Docker Compose file, or test logs. `dfs-ui/README.md` is the unmodified React/Vite template README and does not document this DFS. Thus deployment and any claims about execution cannot be verified from the supplied files.

## 2. Feature-by-feature audit

| Feature | Assessment | Evidence and limits |
|---|---|---|
| Five storage nodes | **Implemented in source; runtime unverified** | Master defines Node-1 through Node-5 with distinct localhost ports (`master/master.py:13–19`); each corresponding `server.py` declares its port and storage path. No Compose/process orchestration or runtime log was supplied. |
| File replication | **Partial / unreliable** | Master samples up to three active nodes (`master/master.py:169–182`) and returns the nodes that replied HTTP 200 (`183–194`). It does not require three successful replicas, so success can mean one or two copies. It reuses the same incoming stream for each request without rewinding (`181–182`), so subsequent node uploads may receive an exhausted stream. No payload hash or byte-count verification is performed. No runtime evidence proves copy integrity. |
| File listing | **Implemented in source; runtime unverified** | Nodes list the storage directory (`node1/server.py:33–39`; same endpoint pattern in nodes 2–5). Master queries every node and includes a list or error string (`master/master.py:200–214`). The UI unions array-valued node listings (`dfs-ui/src/App.jsx:163–167`). |
| Uploads | **Implemented in source; outcome semantics weak** | UI sends multipart data to master (`dfs-ui/src/App.jsx:107–119`); master forwards it to random active nodes. Partial success is reported as success without enforcing a replication factor. No test log or live run was supplied. |
| Downloads | **Lookup/link flow implemented; delivery unverified** | Master searches active-node listings and returns a direct node URL (`master/master.py:220–237`); UI navigates to that URL (`dfs-ui/src/App.jsx:128–142`). There is no end-to-end byte-integrity evidence. The URL embeds the filename without explicit URL encoding. |
| Node failure simulation | **Logical exclusion only** | Master toggle flips in-memory status and checks that a backend answers before marking it active (`master/master.py:132–156`). Setting a node “down” does not stop its process. Upload/download/recovery consult manual status, while master `/list` contacts all node URLs regardless of manual status (`200–214`). `NodeMonitor.jsx` only changes its own React state and does not call the master; it is not rendered by `src/main.jsx`. |
| Recovery | **Partial source implementation; not demonstrated** | `/nodes` triggers recovery on a recorded down→active transition (`master/master.py:88–118`). Recovery unions filenames from nodes considered active and copies missing files (`28–78`). It is driven only when `/nodes` is requested, uses names alone (no version/content comparison), and has no retry queue, durable recovery state, or verification. The recovered copy endpoint call has no explicit timeout (`71`). No recovery test evidence exists. |

## 3. Specific findings

Severity describes impact if the reviewed path is used; it does not imply a runtime incident was observed.

### F-01 — Master delete route references an undefined health-check function — **High**

**Evidence:** `master/master.py:257–260` calls `check_node_health(node)`, but no definition or import of that name exists in the complete supplied `master/master.py`. It also indexes `MANUAL_TOGGLES[node]` directly, although the map starts empty at line 21. A normal delete request can therefore raise `NameError` on the first node (or `KeyError` depending on map state) rather than deleting files. The UI calls this route at `dfs-ui/src/App.jsx:146–157` and currently logs a success-looking message without checking `res.ok`.

**Impact:** The optional delete operation exposed by the dashboard is not supported by the inspected backend path as written; recovery from the raised exception is not handled by the route.

### F-02 — Replication success does not guarantee three valid replicas — **High**

**Evidence:** The master selects `min(3, len(active_nodes))` (`master/master.py:169–175`), forwards the same `file.stream` repeatedly (`181–182`), suppresses all per-node exceptions (`185–186`), and returns normal success whenever at least one node returns 200 (`188–194`). Node handlers save whatever multipart body they receive and return 200 (`node1/server.py:21–28`; same pattern in other node files). There is no content length/hash verification or cleanup of partial writes.

**Impact:** With a forward-only stream, later forwarding attempts can observe the stream at EOF. Even without that failure, a one-copy upload is reported as a successful replicated upload. The implementation does not provide an enforced replication-factor guarantee.

### F-03 — Dashboard failure toggle does not simulate a process or network failure — **Medium**

**Evidence:** `/toggle_node` only changes `MANUAL_TOGGLES` and `NODES[node]['status']` (`master/master.py:140–156`). It never stops a node process or blocks its endpoint. Master `/list` still requests every node (`200–214`), and each node's `/status` continues to return 200 while its process is running (`node1/server.py:14–16`, repeated for nodes 2–5).

**Impact:** This can exercise master-side policy that excludes a manually disabled node from certain operations, but it cannot establish behavior under a real process, host, or network failure. It also yields a listing that can still show files from a node marked down.

### F-04 — Recovery is a best-effort filename copy, not verified replica repair — **Medium**

**Evidence:** Recovery compares only filename sets (`master/master.py:46–55`), copies the first available matching name (`58–78`), and reports success based only on the destination HTTP status (`70–74`). It does not compare file contents or sizes and does not reconcile conflicting versions. The trigger is a `/nodes` poll transition (`112–118`), and the UI polls every five seconds (`dfs-ui/src/App.jsx:81–88`).

**Impact:** Same-name corruption or stale versions are invisible; a failed copy can be retried only indirectly by a later status transition, and no recovery completion/integrity report is persisted. Concurrent or interrupted recovery is not shown to be safe.

### F-05 — Storage paths depend on the process working directory — **Medium**

**Evidence:** All node servers set `STORAGE_PATH` to a relative string such as `../storage/node1` (`node1/server.py:6–9`; corresponding declarations are in nodes 2–5). The path is resolved relative to the process current working directory, not the source file's directory. No Compose configuration or launch script is supplied to define that working directory.

**Impact:** Starting a server from the repository root resolves storage outside the repository's `storage` directory; starting from a node directory resolves it elsewhere. The checked-in `storage/nodeN` sample files do not prove which location the service uses at runtime.

### F-06 — Dashboard can present an error response as a successful upload/delete event — **Low**

**Evidence:** Upload and delete handlers parse JSON and append `data.message` or a locally composed “Deleted” line without checking `res.ok` (`dfs-ui/src/App.jsx:113–120`, `149–157`). The upload error response uses an `error` property in the master (`master/master.py:164–194`), so an error can appear as an undefined/empty event rather than a visible failure.

**Impact:** User-visible status is not reliable for failed requests. This weakens manual verification of the core paths.

### F-07 — Deployment and test evidence are absent from supplied files — **Low (evidence gap)**

**Evidence:** The project-owned inventory includes the six Python source files and frontend files but no root README, Docker Compose YAML, Dockerfiles, test files, or `*.log` files. The only README found is `dfs-ui/README.md`, which describes a generic Vite template. The workspace has no root Git repository metadata available for this audit.

**Impact:** The audit cannot establish how five services are started together, whether container networking is configured, or whether any stated scenario has passed. This is a limitation in the evidence, not proof that no external deployment material exists.

## 4. Prioritized recommendations

1. **Make upload success match the durability promise.** Define the required replica count and fail the request when it is not met. Rewind or buffer the request body for every node, verify each stored object's size and cryptographic hash, and clean up incomplete/extra replicas on failure.
2. **Repair the delete path before relying on the UI.** Implement a defined health/status helper or remove the call, use `.get()` for absent manual state, return per-node outcomes, and make the UI check the HTTP response before displaying success.
3. **Make node state observable and test real failures separately.** Keep health state distinct from manual administrative state. Ensure listings clearly mark administratively excluded nodes, and use process/container termination or network isolation for genuine failure tests.
4. **Make recovery content-aware and durable.** Store file metadata (size, hash, version) and replica locations; compare replicas on return, verify writes, use explicit timeouts/retries, and expose recovery progress and failures. Avoid triggering long synchronous repair work from a dashboard GET request.
5. **Anchor storage paths to each source/configuration.** Resolve paths from a configured absolute data directory or the module location; document and test the chosen path under the intended launch method.
6. **Add deployment and repeatable test evidence.** Supply the requested Compose configuration or another reproducible launcher, a project README, automated integration tests, and captured logs/results that include expected replica counts and hash comparisons.
7. **Improve request/result reporting.** Check HTTP status in the dashboard for uploads, deletes, node toggles, and downloads; display structured error responses and the actual successful replica count.

## 5. Proposed test plan (not executed)

Record each request, response code, node state, object size, and SHA-256 digest. Run against a clean, disposable data directory.

### A. Baseline and five-node visibility

1. Start master and all five nodes using the documented deployment method (currently missing from the supplied files).
2. Confirm `/nodes` reports five active nodes and that each distinct node responds on its configured port.
3. Confirm `/list` returns a separate entry for all five nodes and that each entry has an expected list/error type.

### B. Normal upload, replication, listing, download

1. Upload a small text file and a binary file with known SHA-256 values.
2. Verify the API's `replicated_nodes` count equals the configured required replication factor; inspect each listed node's stored bytes and digest.
3. Verify listing shows the file on exactly those replicas and that the UI displays the same set.
4. Download through the UI/API and compare output bytes and digest with the original. Repeat after making one replica unavailable to confirm lookup uses another live copy.
5. Test no-file, duplicate-name, zero-byte, large-file, and filename-with-spaces cases; confirm errors are surfaced accurately.

### C. One-node failure during and after upload

1. With a healthy file replicated, stop one node process/container (a UI “down” toggle alone is insufficient for this test).
2. Confirm health/listing behavior, then download the file and verify its digest.
3. Upload a new file while one node is down. Confirm the chosen active-node count, actual successful copies, failure response semantics, and digests on every claimed replica.
4. Restore the node. Poll health and verify whether recovery runs, how long it takes, and whether the returned node has the correct bytes and digest.

### D. Two-node failure and recovery

1. With three known replicas, stop two storage-node processes. Verify a read succeeds from the remaining replica and matches the original digest.
2. Attempt an upload with only three nodes available, then with fewer than the configured target. Verify the system rejects or clearly reports under-replication according to policy.
3. Restore the two nodes one at a time. Confirm repair of missing replicas, no duplicate corruption, and byte/hash equality after each recovery.
4. Repeat a recovery after interrupting a copy and after making a same-name replica contain altered bytes; verify the repair policy detects and resolves both cases.

### E. Control-path checks

1. Exercise node toggle with the manual-state map initially empty, then repeat active/down cycles; check actual health separately from administrative exclusion.
2. Exercise deletion when all nodes are active, a node is down, and the filename is absent; confirm API and UI outcome agree.

**Pass criteria:** All claimed replicas exist with matching size/hash; reads return exact bytes while at least one replica survives; the defined failure policy is applied consistently; returning nodes are repaired and verified; user-facing status matches server responses.

## 6. Execution log

### Files inspected

- `master/master.py` — coordinator routes, placement, status, recovery, deletion.
- `node1/server.py` through `node5/server.py` — node routes, storage paths, file I/O. Node 1 was read with line numbers; all five source files were inspected for their full route implementations.
- `dfs-ui/src/App.jsx` — rendered dashboard, upload/list/download/toggle/delete flows.
- `dfs-ui/src/NodeMonitor.jsx` and `dfs-ui/src/main.jsx` — secondary monitor component and app mounting.
- `dfs-ui/README.md` — supplied README; generic Vite template documentation.
- `dfs-ui/package.json` — UI scripts and dependencies.
- Project inventory and `storage/node1` through `storage/node5` — checked for Compose/Docker files, test files, logs, and sample stored files. No test log was present.

### Decisions

- Treated code presence as evidence that a path is implemented, not proof that it works at runtime.
- Distinguished the master's logical down toggle from an actual node process/network failure.
- Marked replication and recovery partial because response status/file names alone do not verify replica count or byte integrity.
- Used severity based on likely impact to the requested core behavior. Findings are static-review findings; none are claims of observed production failures.

### Uncertainties and limitations

- No root README, Docker Compose configuration, deployment instructions, test source, or test log was supplied; orchestration and execution history are therefore unverified.
- No service was started and no test was run, in accordance with the instruction not to claim unperformed testing.
- Relative storage-path resolution depends on the launch working directory, which is not specified in supplied material.
- The upload-stream exhaustion concern follows from repeated forwarding of one stream without a rewind; actual stored bytes should be confirmed with the proposed hash-based test.
- Existing sample files in `storage/` show files present in the workspace only; they do not establish which directories a running process uses or whether the copies are consistent.
- No secrets or credential values were included in this report.
