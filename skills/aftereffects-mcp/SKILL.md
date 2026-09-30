---
name: aftereffects-mcp
description: Control Adobe After Effects through the configured @kumoproductions/mcp-aftereffects server. Use when the user asks to inspect or edit an open After Effects project, compositions, layers, text, shapes, effects, masks, keyframes, footage, render queues, project files, or preview frames, including read-only audits and safe verification workflows.
---

# After Effects MCP

Use the `aftereffects` MCP server to inspect and operate the currently open After Effects project. Prefer the server's typed operations and live catalog over guessed ExtendScript; keep every change explainable, reversible where possible, and verified in After Effects.

## Session startup

1. Confirm that After Effects is running, a project is open, and the intended composition or layer is known. If the server is unavailable, report the prerequisite instead of attempting unrelated filesystem automation.
2. Call `ae_context` at the start of a session. Use it to identify the project path, dirty state, active composition, selected layers, item IDs, stable layer-ID support, ES3 constraints, and the undo contract.
3. Check the responding instance and `instances` list before editing. If several instances are live, pass the same explicit `instance` (ID or unambiguous project filename/path) to every call, including read-back, rendering, and saving. `AE_MCP_INSTANCE` is only the server default; an empty list with `transport.mode: "push"` can still be a working single-instance session.
4. Call `ae_version_info` when the request depends on AE version, platform, renderer, or feature availability.
5. Call `ae_catalog` before using `ae_do`. Without a category it lists the current operation surface; with a category it provides exact parameters. Do not invent operation names or parameter names.

## Safety contract

- Treat project edits, overwrites, project saves, imports, renders, preference changes, and arbitrary code as state-changing operations. Follow the user's explicit request, but confirm ambiguous targets, overwrite paths, or broad destructive actions before executing them.
- Prefer stable layer references such as `{ id: n }` after inspection. Do not rely on a layer index after a reorder, duplicate, or deletion unless re-inspected.
- Use `ae_do` for one operation. Use one sequential `batch.run` operation for related mutations and verification; do not issue parallel AE mutations because the file-IPC bridge serializes work.
- Project-editing ExtendScript operations normally share one automatic undo group per call; project boundaries, undo/redo, and Node-side operations are exceptions. Never call `app.beginUndoGroup` or `app.endUndoGroup` in `eval.run`. Call `project.undo` or redo as its own operation, never inside `batch.run` or `eval.run`.
- Never open, create, close, or replace a project from `eval.run`; use the dedicated project operation because project boundaries can orphan an undo group.
- Treat `ae_save_project`, rendered files, and exported JSON as non-undoable. State clearly whether the project was saved and where output files were written.
- Treat `eval.run` as a last resort. It is disabled unless `AE_MCP_ENABLE_EVAL=1`; use a dedicated catalog operation whenever one exists, and never enable arbitrary ExtendScript merely to bypass a missing operation.
- Application-configuration operations (preferences, memory/MFR settings, default folders, tools, font policy/favorites, render templates) require `confirm: true` only when the user explicitly asked to change the AE application itself.
- Keep output paths absolute and outside the MCP IPC mailbox. Use `ae_render_frame` for previews, then check `colorPipeline` and `colorWarning`: fallback captures may not match the viewer. Normal color-managed capture can temporarily create layers/calibration comps, leave the project dirty, and consume an undo step; `AE_MCP_READONLY=1` skips those mutations and uses a color-conversion fallback.

## Inspecting a project

1. Use `ae_project_info` for the project-level overview.
2. Use `ae_comp_info` for composition summaries and `ae_layer_info` for full layer/property/keyframe details. Use `detail: "summary"` for broad layer audits to omit default-value properties while keeping group structure; request full detail when defaults matter. Use the operation twins `comp.info` and `layer.info` inside `batch.run` when a mutation must be verified in the same call.
3. Inspect before changing. Record target comp IDs, layer IDs, current values, and whether the project is dirty.
4. For an audit, prefer a server started with `AE_MCP_READONLY=1`. In read-only mode, do not work around policy restrictions; use the catalog's visible read operations.

## Editing workflow

1. Restate the intended change and its scope in one sentence, especially for multiple comps or layers.
2. Inspect the current state and resolve exact targets by ID/name.
3. Drill into the relevant `ae_catalog` category, validate required arguments, and choose the smallest dedicated operation.
4. Use a single `ae_do` for a simple edit. For a multi-step edit, use `ae_do({ operation: "batch.run", args: { ops: [...], stopOnError: true } })` so compatible steps run sequentially as one undo step. Inspect every child result: a batch is not transactional, earlier edits remain after failure, and the default without `stopOnError: true` continues executing later children. Node-side operations such as `instance.*`, as well as project open/new and undo/redo, must be separate calls. `project.merge` imports through ExtendScript and can share a batch with compatible project edits.
5. Include a read-back operation such as `comp.info`, `layer.info`, or a relevant property read as the final batch child when the operation supports it.
6. Use `ae_render_frame` when visual proof matters. For motion, pass `times` (1–32 timestamps, mutually exclusive with `time`) and optionally `contactSheet: {}` for a labelled image and `analyze: true` for margins/content bounds. Inspect the images as well as the analysis; `comp.sample` complements them with property values across times. Do not claim a visual result from metadata alone.
7. Save only when requested or clearly required by the task. If saving, use `ae_save_project` and report the exact path; otherwise state that the project remains unsaved.

## Common task routing

- Text and shapes: inspect the target layer, then use the catalog's `text.*` or `shape.*` operations. Preserve existing styling unless the user asks for a reset.
- Keyframes and expressions: inspect the property and existing keys first. Use `keyframe.apply` for whole key lists with per-key easing. Its `interp: "hold"` holds only the outgoing segment; `keyframe.set_easing` with the hold preset holds both sides and can freeze the preceding fade. Typed writes handle separated Position followers. Prefer typed keyframe/expression operations; use `eval.run` only for a genuinely unsupported case.
- Layout and vector artwork: prefer `layer.set_anchor` (Position compensated), `layer.set_timing`, `layer.set_visibility_schedule`, `comp.resize`, and `comp.set_layer_order`. Use `layer.convert_to_shapes`, `shape.group_bounds`, `layer.split_groups`, `shape.recolor`, or `shape.signature` for Illustrator/shape tasks. Inspect catalog arguments before use; these operations avoid custom eval scripts. Operations whose layer target accepts `"all"` also accept arrays of names, indices, stable IDs, or `"selected"`.
- Effects and masks: identify the target by stable layer ID and use typed `effect.*` or `mask.*` operations. Verify the effect/property after mutation.
- Footage and project structure: inspect usages and missing items before replacement or deletion. Confirm any path change and preserve a backup when the request is broad.
- Render queue: inspect current queue state and settings first. Use longer `timeoutMs` for long renders and report whether the result was queued, completed, or failed.
- Export/import: choose explicit absolute paths, verify the destination before writing, and never write into the MCP runtime directory.

## Multiple instances (only when needed)

- Discover targets with `ae_context` or `instance.list`; route tools with their top-level `instance` argument, not an invented operation argument.
- Ordinary single-instance use needs no AE-side installation. Multiple instances require the resident startup agent: inspect with `npx -y @kumoproductions/mcp-aftereffects@latest agent-status`; install/update with `install-agent` when needed for the authorized task. The agent loads on the next AE launch, and installation should be repeated after an AE update. Do not restart an AE session with unsaved work merely to load it.
- For an authorized worker workflow, use standalone `instance.start` with `copyFrom` and a verified `copyTo` destination, edit/save the copy through its explicit instance, then `project.merge` on the intended main instance and `instance.stop` on the worker. A copy uses the saved file, not the main instance's unsaved changes; resolve that difference before starting. Never let two instances save to the same file. Do not pass `discardChanges` or overwrite a copy unless authorized.

## Recovery and troubleshooting

When a call times out or returns a stale/error result:

1. For `DIALOG_OPEN`, inspect the reported dialog text/`details.dialogs` or use standalone `instance.dialogs`. Do not keep retrying scripts behind a modal dialog. Use `instance.dismiss_dialog { id }` only when its cancel action is appropriate for the authorized task: it sends Escape, acknowledges warnings, and cancels save prompts without saving or closing the project. On macOS, dismissal requires Accessibility permission; `accessibility: false` permits limited detection but no dismissal. Report that prerequisite when needed.
2. For `NO_INSTANCE`, inspect live instances and agent status and resolve the intended target; do not edit a newly launched empty project as a substitute.
3. Check that After Effects is open, the project is open, and the scripting preference `Allow Scripts to Write Files and Access Network` is enabled.
4. On macOS, check Automation permission for the MCP client or terminal.
5. Call `ae_context` and `ae_version_info` again; do not repeat a mutation blindly.
6. Re-inspect the target and only retry when the request has not already taken effect.
7. If undo is broken or an `UndoGroup Mismatch` appears, stop editing, report it, and use the dedicated project undo/recovery path rather than more `eval.run` calls.

## Response format

- Summarize what was inspected or changed, using comp/layer names and IDs when useful.
- State verification evidence: read-back values, render path, or the exact error.
- State save status and output paths separately.
- If the request was read-only, explicitly say that no project mutation was performed.

## Maintained API source

This skill follows the published 0.3.1 API. The live `ae_catalog` remains authoritative for available operations and arguments. When updating the server, compare the [upstream changelog](https://github.com/kumoproductions/mcp-aftereffects/blob/main/CHANGELOG.md) and published tool schemas before changing these instructions.
