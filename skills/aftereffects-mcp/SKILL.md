---
name: aftereffects-mcp
description: Control Adobe After Effects through the configured @kumoproductions/mcp-aftereffects server. Use when the user asks to inspect or edit an open After Effects project, compositions, layers, text, shapes, effects, masks, keyframes, footage, render queues, project files, or preview frames, including read-only audits and safe verification workflows.
---

# After Effects MCP

Use the `aftereffects` MCP server to inspect and operate the currently open After Effects project. Prefer the server's typed operations and live catalog over guessed ExtendScript; keep every change explainable, reversible where possible, and verified in After Effects.

## Session startup

1. Confirm that After Effects is running, a project is open, and the intended composition or layer is known. If the server is unavailable, report the prerequisite instead of attempting unrelated filesystem automation.
2. Call `ae_context` at the start of a session. Use it to identify the project path, dirty state, active composition, selected layers, item IDs, stable layer-ID support, ES3 constraints, and the undo contract.
3. Call `ae_version_info` when the request depends on AE version, platform, renderer, or feature availability.
4. Call `ae_catalog` before using `ae_do`. Without a category it lists the current operation surface; with a category it provides exact parameters. Do not invent operation names or parameter names.

## Safety contract

- Treat project edits, overwrites, project saves, imports, renders, preference changes, and arbitrary code as state-changing operations. Follow the user's explicit request, but confirm ambiguous targets, overwrite paths, or broad destructive actions before executing them.
- Prefer stable layer references such as `{ id: n }` after inspection. Do not rely on a layer index after a reorder, duplicate, or deletion unless re-inspected.
- Use `ae_do` for one operation. Use one sequential `batch.run` operation for related mutations and verification; do not issue parallel AE mutations because the file-IPC bridge serializes work.
- Every `ae_do` call is automatically one undo group. Never call `app.beginUndoGroup` or `app.endUndoGroup` in `eval.run`. Call `project.undo` or redo as its own operation, never inside `batch.run` or `eval.run`.
- Never open, create, close, or replace a project from `eval.run`; use the dedicated project operation because project boundaries can orphan an undo group.
- Treat `ae_save_project`, rendered files, and exported JSON as non-undoable. State clearly whether the project was saved and where output files were written.
- Treat `eval.run` as a last resort. It is disabled unless `AE_MCP_ENABLE_EVAL=1`; use a dedicated catalog operation whenever one exists, and never enable arbitrary ExtendScript merely to bypass a missing operation.
- Application-configuration operations (preferences, memory/MFR settings, default folders, tools, font policy/favorites, render templates) require `confirm: true` only when the user explicitly asked to change the AE application itself.
- Keep output paths absolute and outside the MCP IPC mailbox. Use `ae_render_frame` for display-correct preview PNGs in color-managed projects.

## Inspecting a project

1. Use `ae_project_info` for the project-level overview.
2. Use `ae_comp_info` for composition summaries and `ae_layer_info` for full layer/property/keyframe details. Use the operation twins `comp.info` and `layer.info` inside `batch.run` when a mutation must be verified in the same call.
3. Inspect before changing. Record target comp IDs, layer IDs, current values, and whether the project is dirty.
4. For an audit, prefer a server started with `AE_MCP_READONLY=1`. In read-only mode, do not work around policy restrictions; use the catalog's visible read operations.

## Editing workflow

1. Restate the intended change and its scope in one sentence, especially for multiple comps or layers.
2. Inspect the current state and resolve exact targets by ID/name.
3. Drill into the relevant `ae_catalog` category, validate required arguments, and choose the smallest dedicated operation.
4. Use a single `ae_do` for a simple edit. For a multi-step edit, use `ae_do({ operation: "batch.run", args: { ops: [...] } })` so the steps run sequentially as one undo step.
5. Include a read-back operation such as `comp.info`, `layer.info`, or a relevant property read as the final batch child when the operation supports it.
6. Use `ae_render_frame` when visual proof matters. Do not claim a visual result from metadata alone.
7. Save only when requested or clearly required by the task. If saving, use `ae_save_project` and report the exact path; otherwise state that the project remains unsaved.

## Common task routing

- Text and shapes: inspect the target layer, then use the catalog's `text.*` or `shape.*` operations. Preserve existing styling unless the user asks for a reset.
- Keyframes and expressions: inspect the property and existing keys first. Prefer typed keyframe/expression operations; use `eval.run` only for a genuinely unsupported case.
- Effects and masks: identify the target by stable layer ID and use typed `effect.*` or `mask.*` operations. Verify the effect/property after mutation.
- Footage and project structure: inspect usages and missing items before replacement or deletion. Confirm any path change and preserve a backup when the request is broad.
- Render queue: inspect current queue state and settings first. Use longer `timeoutMs` for long renders and report whether the result was queued, completed, or failed.
- Export/import: choose explicit absolute paths, verify the destination before writing, and never write into the MCP runtime directory.

## Recovery and troubleshooting

When a call times out or returns a stale/error result:

1. Check that After Effects is open, the project is open, and the scripting preference `Allow Scripts to Write Files and Access Network` is enabled.
2. On macOS, check Automation permission for the MCP client or terminal.
3. Call `ae_context` and `ae_version_info` again; do not repeat a mutation blindly.
4. Re-inspect the target and only retry when the request has not already taken effect.
5. If undo is broken or an `UndoGroup Mismatch` appears, stop editing, report it, and use the dedicated project undo/recovery path rather than more `eval.run` calls.

## Response format

- Summarize what was inspected or changed, using comp/layer names and IDs when useful.
- State verification evidence: read-back values, render path, or the exact error.
- State save status and output paths separately.
- If the request was read-only, explicitly say that no project mutation was performed.
