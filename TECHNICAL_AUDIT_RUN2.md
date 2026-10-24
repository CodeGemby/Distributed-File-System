# Fault-Tolerant Distributed File System — Second Technical Audit

**Audit date:** 2026-10-24  
**Method:** Static inspection of supplied files only. No services or tests were run.  
**Status terms:** *Confirmed by static inspection* means the cited structure is directly present/absent in the inspected source; it does not mean runtime execution was observed. *Partially supported* means source supports only part of the Run 1 conclusion or leaves runtime-dependent behavior open. *Unverified* means supplied evidence is insufficient to substantiate the claim.

## Executive summary

The source defines a master and five node services, plus UI paths for listing, uploading, downloading, and toggling logical node status. Source inspection does not establish that the system runs correctly or survives process failures. There are no supplied runtime logs or tests, and no top-level deployment guide or Compose file was found in the workspace.

Rechecking Run 1 confirms its main source concerns, with two refinements: the delete route first has an unconditional missing-key hazard (`MANUAL_TOGGLES[node]`) when a node has not been toggled; the undefined `check_node_health` call is reached only when that access succeeds and the earlier condition does not short circuit. The upload code definitely reuses one request stream across sequential forwarding attempts and definitely accepts any positive number of successful node responses as overall success; whether later nodes store truncated/empty bytes needs a runtime hash test. Recovery has an additional concrete defect missed in Run 1: after finding one source node that returns the file, it breaks out of the source loop even if upload to the recovering target fails.

An additional security finding is supported by the node upload code: it joins the client-provided multipart filename directly to the storage path without filename sanitization. A crafted path may escape the intended storage directory, subject to the platform and process permissions. This has not been exercised. No credentials are reproduced here.

## 1. Architecture

`master/master.py` defines five fixed node URLs on `127.0.0.1:5001` through `:5005` and a Flask master on port 5000. The master holds status and manual toggles in process memory, chooses up to three active nodes for uploads, aggregates node directory listings, locates a listed copy for download, and attempts repair when `/nodes` sees a down-to-active transition. Each `nodeN/server.py` is a Flask service with status, upload, list, download, storage-size, and delete handlers. Each sets `STORAGE_PATH` to a relative `../storage/nodeN` string.

`dfs-ui/src/App.jsx` is the mounted React app (`dfs-ui/src/main.jsx`). It polls `/nodes` and `/list`, submits uploads to master, uses the master download lookup to navigate directly to a node URL, and calls master toggle/delete routes. `NodeMonitor.jsx` implements a separate local-state toggle; it is not imported by `main.jsx`.

This is a centralized coordinator over local node directories. The supplied code has no durable file metadata or replica manifest. Replica placement is random. The workspace inventory showed no top-level README, Docker Compose/Dockerfile, project test files, or test logs. The only README found, `dfs-ui/README.md`, is a generic Vite template. Absence here is evidence only about the supplied workspace materials.

## 2. Run 1 finding traceability

| Finding ID | Run 1 conclusion | Evidence rechecked | Run 2 conclusion | Change and reason |
|---|---|---|---|---|
| F-01 | Delete path calls undefined `check_node_health` and directly indexes an initially empty toggle map; UI may misreport result. | `master/master.py`, `MANUAL_TOGGLES` line 21; `delete_from_dfs()` lines 247–278, especially 259; no definition/import exists in the full supplied file. UI `handleDelete()` in `dfs-ui/src/App.jsx` lines 146–161. | **Confirmed by static inspection** that both hazards exist; runtime outcome is unverified. | Refined ordering: direct dictionary indexing can raise `KeyError` for the first untoggled node before the undefined helper is evaluated. `NameError` occurs only if evaluation reaches `check_node_health`. UI logs “Deleted …” only after JSON parsing succeeds and regardless of JSON HTTP error status; a non-JSON error instead reaches `catch`. |
| F-02 | Stream reused; success can mean fewer than three replicas; no content verification. | `upload_file()` in `master/master.py` lines 162–194: sample at 175, same `file.stream` passed at 181 for each sequential `requests.post`, exceptions swallowed at 185–186, success if any at 188–194. Node `upload_file()` e.g. `node1/server.py` lines 21–28 saves and returns 200. | **Confirmed by static inspection** for stream reuse and permissive success condition; byte-level impact is **unverified** without execution. | Clarified the distinction between certain control flow and probable stream exhaustion. A hash/size test is needed to determine actual bytes received by each node under installed library/runtime versions. |
| F-03 | UI toggle is logical exclusion, not process/network failure; `/list` still contacts marked-down nodes. | `toggle_node()` in `master/master.py` lines 132–156 only changes in-memory values (activation also probes `/status`); `list_all_files()` lines 200–214 calls every configured URL. `get_nodes()` lines 88–124 reports manual down without probing. `NodeMonitor.jsx` `toggleNode()` lines 27–44 changes local React state only; `main.jsx` mounts `App`, not `NodeMonitor`. | **Confirmed by static inspection.** Actual failure tolerance remains **unverified**. | No conclusion change; direct code references added. The master toggle is useful for policy exclusion but is not a physical failure injection. |
| F-04 | Recovery compares names only, copies a source copy, is poll-triggered, and lacks content verification/retry durability. | `get_global_unique_files()` lines 28–43; `get_missing_files_for()` lines 46–55; `recover_node()` lines 58–78; trigger in `get_nodes()` lines 112–118. Recovery destination POST at line 71 has no explicit timeout. UI polls `/nodes` every five seconds (`App.jsx` lines 81–88). | **Partially supported.** Those limitations are confirmed in source; successful recovery is **unverified**. | Added a missed control-flow issue: within `recover_node`, once a source download returns 200, `break` at line 75 exits the peer loop after the target POST attempt even if that POST was non-200. Source does not provide another source attempt for that filename in this invocation. |
| F-05 | Relative storage paths depend on working directory. | Each `nodeN/server.py` lines 6–9 defines `STORAGE_PATH = "../storage/nodeN"` and immediately calls `os.makedirs`; file operations reuse it (e.g. node1 lines 24–25, 36, 47). No launch config was found. | **Confirmed by static inspection** that paths are relative; the actual runtime location is **unverified**. | Kept and narrowed the conclusion: Python resolves this relative path from process working directory, but absent launch instructions mean we cannot state which directory a deployed process uses. |
| F-06 | UI does not check response status for upload/delete and may show misleading events. | `handleUpload()` `App.jsx` lines 107–125 parses JSON and appends `data.message` without `res.ok`; master upload errors use `error` keys (`master.py` lines 164–194). `handleDelete()` lines 146–161 parses JSON, then appends `Deleted …` without checking `res.ok`. | **Confirmed by static inspection**, with a narrower impact statement. | Upload errors may append an undefined message if the error response is JSON. Delete JSON error responses can be logged as deleted; non-JSON errors are caught during JSON parsing and do not append that line. No runtime UI behavior was tested. |
| F-07 | No deployment/test evidence in supplied workspace. | Rechecked workspace-owned inventory: no root README, compose/Docker config, test source, or logs; `dfs-ui/README.md` is template text. | **Confirmed as an evidence gap in the inspected workspace; broader absence unverified.** | No substantive change. Avoid interpreting the workspace inventory as proof that external files or test runs do not exist. |

## 3. Findings

Severity reflects potential impact to the requested features, not a measured incident. The classification immediately below each heading is about evidence status, not severity.

### F-01 — Delete handler has two server-side failure hazards — **High**

**Evidence status: Confirmed by static inspection.** In `master/master.py`, `MANUAL_TOGGLES` is initialized as `{}` at line 21. In `delete_from_dfs()` lines 247–278, line 259 evaluates `MANUAL_TOGGLES[node]` for each configured node. If that key is absent, direct indexing raises `KeyError`. If it is present and equals `active`, evaluation continues to `check_node_health(node)`, which has no definition or import anywhere in the supplied file and raises `NameError`. Either condition can prevent the route from reaching its request/delete handling. The UI invokes this endpoint in `dfs-ui/src/App.jsx`, `handleDelete()` lines 146–161.

**Unresolved:** No deletion request was run. To resolve runtime details, add a route-level test for initially empty toggles, then one with an `active` toggle and mocked node health; inspect response status/body and confirm behavior across all nodes.

### F-02 — Upload reports success below the selected replication count and reuses the upload stream — **High**

**Evidence status: Confirmed by static inspection for code structure; byte outcome unverified.** `upload_file()` in `master/master.py` selects up to three active nodes at lines 169–175, uses `file.stream` for every sequential request at lines 178–182, catches all node exceptions at lines 185–186, and returns success whenever `uploaded_to` is nonempty at lines 188–194. Thus code explicitly permits success with one or two acknowledged nodes, and also with one selected node when fewer than three are active. Each node upload handler, e.g. `node1/server.py` `upload_file()` lines 21–28, saves the received upload and returns HTTP 200 without verifying expected bytes/hash.

Passing the same stream without seeking/rebuffering is a concrete source defect. The exact bytes observed by later requests are not established by source review alone; verify by uploading a multi-node binary payload, then compare each stored object's length and SHA-256.

**Unresolved:** There is no stated policy whether the required factor is always three or may degrade with availability. Needed: product requirement/configuration and an integration test asserting expected behavior when fewer than three replicas succeed.

### F-03 — “Down” toggle changes coordinator state, not node availability — **Medium**

**Evidence status: Confirmed by static inspection.** `toggle_node()` in `master/master.py` lines 132–156 changes `MANUAL_TOGGLES` and `NODES` state. On activation only, it checks `/status` lines 143–150. It does not stop a process or alter node networking. `/list` in `list_all_files()` lines 200–214 still requests every node regardless of manual state. `/nodes` reports a manual-down node as down at lines 92–95 without probing it. Separately, `NodeMonitor.jsx` `toggleNode()` lines 27–44 updates only its own state, and `main.jsx` mounts `App`, not `NodeMonitor`.

**Unresolved:** Whether an external launcher or network layer is used for real fault injection is unknown because no deployment files were supplied. Needed: launcher/Compose config and tests that kill or isolate a node, distinct from exercising the administrative toggle.

### F-04 — Recovery is filename-based and stops trying peers after a failed target upload — **High**

**Evidence status: Partially supported.** The recovery helper set in `master/master.py` is present: `get_global_unique_files()` lines 28–43 collects names; `get_missing_files_for()` lines 46–55 compares names; `recover_node()` lines 58–78 downloads a source and posts its bytes to the target. The `/nodes` handler invokes it on a prior `down` to current `active` status transition at lines 112–118. Recovery does not compare content, size, or version. In `recover_node()`, after any source responds 200, the upload is attempted at line 71; line 75 then breaks from the source loop whether or not the target upload returned 200. Therefore an unsuccessful target POST does not lead to trying another source in that pass. The target POST also has no explicit timeout.

**Unresolved:** No return-to-service recovery has been run. Need an integration test with multiple source replicas, a failing target upload on first attempt, then a successful later-source possibility; record recovery result and verify bytes/hash. Concurrent transitions and interrupted copies also need tests.

### F-05 — Storage location is launch-directory dependent — **Medium**

**Evidence status: Confirmed by static inspection for relative path; actual location unverified.** Every node sets a relative path, e.g. `node1/server.py` module-level lines 6–9 (`../storage/node1`), with equivalent declarations in `node2/server.py` through `node5/server.py`. Operations use that path (node1 upload lines 21–28; listing 33–39; download 44–49). Relative paths resolve from process working directory. No supplied launch configuration documents or fixes that directory.

**Unresolved:** Need the actual launch command/container working directory and an integration check that writes a test file and confirms its resolved absolute path matches the intended persistent volume.

### F-06 — UI does not validate HTTP success before reporting upload/delete outcomes — **Low**

**Evidence status: Confirmed by static inspection.** In `dfs-ui/src/App.jsx`, `handleUpload()` lines 107–125 reads JSON and logs `data.message` without checking `res.ok`; master failure bodies use `error`, not `message` (`master/master.py` lines 164–194). `handleDelete()` lines 146–161 logs `Deleted ${fname}` after any JSON response, without checking the status or `data.error`. A non-JSON response would fail `res.json()` and reach `catch` instead. Node toggle similarly logs `data.message` without checking status (`App.jsx` lines 91–105). Download does check `res.status !== 200` before following the returned URL (`App.jsx` lines 128–142), but the actual direct node transfer is not verified here.

**Unresolved:** Exact user-visible rendering for each response depends on browser execution. Needed: frontend tests with JSON 4xx/5xx and non-JSON responses; verify error display and no false success log.

### F-07 — Deployment and execution claims lack supplied evidence — **Low, evidence gap**

**Evidence status: Confirmed within the inspected workspace; external evidence unverified.** Inventory inspection found `master/master.py`, five node servers, frontend source, and sample storage files, but no top-level README, Compose/Docker files, project test files, or test logs. `dfs-ui/README.md` is a Vite template. This prevents validation of startup wiring, container networking, mounts, and prior test claims; it does not prove such materials do not exist elsewhere.

**Unresolved:** Supply the project-level README, deployment configuration, and test logs/CI artifacts to establish intended startup procedure and prior execution evidence.

### F-08 — Node upload joins an unsanitized client filename to the storage directory — **High**

**Evidence status: Confirmed by static inspection; exploitability/runtime impact unverified.** In every `nodeN/server.py`, `upload_file()` receives `request.files['file']` and calls `file.save(os.path.join(STORAGE_PATH, file.filename))` (e.g. `node1/server.py` lines 21–28). The filename comes from the multipart request; no `secure_filename` or containment validation is present. Depending on supplied path separators, platform path semantics, and process permissions, a crafted filename may write outside the intended node directory or overwrite an accessible file. Node upload endpoints are directly reachable at their configured service ports; no authentication check appears in the supplied node handlers.

**Unresolved:** Do not infer successful traversal from source alone. Needed: safe isolated security test using a disposable directory, platform-specific crafted filenames, and checks that resolved output stays under the node storage root. Also define authentication/network exposure requirements. Mitigation should sanitize names and enforce resolved-path containment before saving.

## 4. Revised prioritized action plan

1. **Fix correctness and security at upload boundaries.** Sanitize and contain multipart filenames in each node handler. Buffer/rewind bytes for each replica request. Enforce an explicit replication policy and only report success when the required number of nodes stored bytes matching the expected length/hash; report partial replicas distinctly and clean up incomplete writes.
2. **Make delete route safe and deterministic.** Replace direct dictionary indexing with a defined state default and implement/remove `check_node_health`; add route tests for initial and toggled state. Have UI validate HTTP status and display the server's structured error/result.
3. **Make recovery retryable and content-aware.** Persist metadata sufficient to detect missing, corrupt, and stale replicas. Continue to another source when a target copy fails; set finite timeouts, record per-node outcomes, and expose repair status. Avoid doing unbounded repair work inside a polling GET handler.
4. **Separate administrative exclusion from physical health.** Make status API report both concepts. For failure testing, stop/partition node processes and confirm master operations behave correctly. Ensure the list UI clearly distinguishes reachable files from administratively excluded nodes.
5. **Make node storage paths deterministic.** Resolve a configured absolute data root or anchor paths to module location and document volume/working-directory behavior. Verify persisted data across restarts.
6. **Add reproducible deployment and evidence.** Provide project README and orchestration configuration, integration tests, and logs/CI results. Test content digests, not just HTTP status or filenames.
7. **Correct UI result handling.** Check `res.ok` for upload, delete, and toggle; render API errors; refresh displayed state after confirmed success. Keep download's direct transfer outcome observable or proxy the bytes through a response whose completion can be checked.

## 5. Repeatable test checklist (proposed; not executed)

Run only in a disposable environment with a clean data root. Capture timestamp, command/request, response code/body, node process state, replica list, object length, and SHA-256. Expected outcomes below are acceptance criteria, not reported results.

### A. Startup and node inventory

- [ ] Start master and all five nodes using the documented deployment setup. **Expected:** all five configured endpoints answer status; `/nodes` reports five active nodes.
- [ ] Query master `/list` with all nodes running. **Expected:** one entry per configured node; every successful entry contains a file array.
- [ ] Confirm each process's resolved storage directory. **Expected:** paths are distinct, inside the intended data root, and persist across restart.

### B. Normal upload, listing, download

- [ ] Upload known text and binary payloads; record original byte length and SHA-256. **Expected:** response reports the explicit replication policy result, not generic success on partial copies.
- [ ] Inspect every claimed replica. **Expected:** each exists with exact original length and digest; no unclaimed partial artifact remains.
- [ ] Query `/list` and refresh dashboard. **Expected:** files appear on exactly the nodes that hold them; error nodes are distinguishable from empty nodes.
- [ ] Download each file through the UI path. **Expected:** saved bytes and digest equal the originals; a missing file yields a clear error.
- [ ] Try zero-byte, large, duplicate-name, spaces/unicode, and path-like multipart filenames in isolation. **Expected:** normal names follow documented policy; traversal names are rejected or safely reduced and never create files outside node storage.

### C. Replication fault and policy boundaries

- [ ] Arrange deterministic node failures during forwarding, one at a time. **Expected:** returned replica count matches nodes that hold complete verified copies; request success/failure follows the configured minimum.
- [ ] Repeat with only two and then fewer than the minimum active nodes. **Expected:** no false full-replication success; API states actual count and required count.
- [ ] Compare stored length/hash on all selected nodes. **Expected:** all reported replicas match, including the second and third sequential uploads.

### D. One-node physical failure

- [ ] Upload a file, then stop one node process (do not rely only on the dashboard toggle). **Expected:** status marks it unreachable; downloads work from another replica and match digest.
- [ ] Upload another file during the outage. **Expected:** behavior follows documented minimum-replica policy and accurately reports under-replication if applicable.
- [ ] Restore node and poll status. **Expected:** recovery is triggered once, missing data is copied and verified, and failures remain visible/retryable.

### E. Two-node failure and recovery retry

- [ ] Start with a file replicated to at least three nodes; stop two processes. **Expected:** read succeeds from surviving replica with matching digest.
- [ ] Restore one failed node at a time. **Expected:** each returning target converges to the correct replica set and content hash.
- [ ] Inject target upload failure from the first candidate source while another source remains healthy. **Expected:** repair tries the next source or reports a retryable failure; it does not silently stop after first source.
- [ ] Corrupt a same-name replica and interrupt a repair. **Expected:** hash metadata identifies corruption and interrupted repair is retried safely without declaring completion prematurely.

### F. API/UI error handling and delete

- [ ] Call delete before any node toggle; repeat after marking nodes active/down. **Expected:** no uncaught exception; API returns accurate per-node outcome and UI never logs deletion on error.
- [ ] Return JSON and non-JSON errors for upload/delete/toggle. **Expected:** UI renders a clear failure and does not show false success.
- [ ] Test admin “down” toggle and separately stop a node. **Expected:** UI/API distinguishes administrative exclusion from real reachability; `/list` labeling is consistent.

## 6. Execution log

### Files re-inspected

- `TECHNICAL_AUDIT.md` — Run 1 conclusions and references.
- `master/master.py` — all master functions and routes, including `get_global_unique_files`, `get_missing_files_for`, `recover_node`, `get_nodes`, `toggle_node`, `upload_file`, `list_all_files`, `download_file`, and `delete_from_dfs`.
- `node1/server.py` through `node5/server.py` — storage-path declarations and upload/list/download/delete handlers. Node 1 code was re-read line-numbered; other nodes were cross-checked for corresponding declarations and route patterns.
- `dfs-ui/src/App.jsx` — upload, delete, download, node toggle, and polling behavior.
- `dfs-ui/src/NodeMonitor.jsx`, `dfs-ui/src/main.jsx` — local toggle and which component is mounted.
- `dfs-ui/README.md`, `dfs-ui/package.json` — README content and available UI scripts.
- Workspace file inventory and `storage/` — checked for deployment/test artifacts and sample data.

### Conclusions changed or refined

- **F-01:** Refined exception ordering. Empty toggles can raise `KeyError` before the missing helper is reached; `NameError` remains confirmed if control reaches that expression.
- **F-02:** Kept the stream-reuse concern but explicitly separated source fact from byte-level runtime effect. Replication success below three is directly confirmed by source.
- **F-04:** Added the peer-loop `break` after an attempted target upload, which prevents trying another source if that upload fails.
- **F-06:** Narrowed UI consequence: a JSON error can be logged as deleted, while non-JSON error parsing reaches `catch`; upload errors may append an undefined message. No browser behavior was run.
- **F-07:** Scoped missing deployment/test material claim to the inspected workspace rather than universal absence.
- **F-08:** Added unsanitized upload filename path handling as a source-supported security concern; exploitability was not tested.

### Uncertainties and limits

- No runtime services, tests, browser flows, or fault injections were executed. Every runtime outcome remains unverified.
- No project-level README, Compose/Docker configuration, tests, or logs were present in the inspected workspace; external documentation or CI artifacts may exist elsewhere.
- Actual upload bytes per replica depend on runtime/library behavior and must be verified by length/hash comparison.
- The process working directory and deployment mounts are unknown, so the resolved storage location cannot be asserted.
- Recovery success, retry behavior, and fault tolerance require integration tests with controlled failures and content verification.
- Filename traversal impact depends on platform, path syntax, and service permissions; the unsafe join is visible, but no exploit attempt was made.
- No secret or credential values were copied into this report.
