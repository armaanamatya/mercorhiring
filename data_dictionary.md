# Data dictionary

Loss-analysis dataset · `v1.0.0`

Three CSV tables plus a trajectory archive. Everything loads with standard tooling; no
network access, GPU, or special formats are required.

---

## `runs.csv` — one row per run

A *run* is one evaluation of one model running under one harness configuration, against
one benchmark's task set. **54 rows.**

A run has no pass/fail or score column. It records how many tasks were expected,
executed and passed; a rate is derived, not stored.

| column | type | null | description |
|---|---|---|---|
| `run_id` | string | no | Primary key. |
| `benchmark_id` | enum | no | `artifact_hard` (45 tasks) or `service_ops` (50 tasks). |
| `model_name` | string | no | Model name the run was launched with. |
| `harness_name` | string | no | The harness the run was launched with — the software that drives the model. |
| `repeat_group_id` | string | yes | Identifier shared by a set of related runs. |
| `runner_version` | string | yes | Runner build. |
| `price_catalog_version` | string | yes | Version of the pricing metadata. |
| `run_status` | enum | no | `finished` or `partial`. |
| `token_budget_per_task` | int | no | Assigned tier: 8000, 16000, or 32000. |
| `tasks_expected` | int | no | The benchmark's task count. |
| `tasks_executed` | int | no | Tasks with a recorded outcome. |
| `tasks_passed` | int | no | Tasks with `passed = True`. |
| `total_cost_usd` | decimal(6) | yes | Cost, summed from this run's tasks. |
| `prompt_tokens` | int | yes | Uncached input tokens, summed from tasks. |
| `completion_tokens` | int | yes | Output tokens, summed from tasks. |
| `cached_tokens` | int | yes | Cached input tokens, summed from tasks. |

---

## `tasks.csv` — one row per (run, task)

The complete grid: every run has a row for every task its benchmark defines, including
tasks that did not run. **2,550 rows.** Primary key is `(run_id, task_id)`.

| column | type | null | description |
|---|---|---|---|
| `run_id` | string | no | Foreign key to `runs.csv`. |
| `task_id` | string | no | Benchmark-local task identifier, stable across runs. |
| `task_family` | enum | no | `manifest`, `checksum`, `dependency`, `changelog` on artifact_hard; `billing`, `booking`, `account`, `policy` on service_ops. |
| `difficulty_band` | enum | no | `easy`, `medium`, or `hard`. |
| `task_status` | enum | no | `completed` or `not_executed`. |
| `passed` | bool | yes | Empty where the task was not executed. |
| `exception_count` | int | no | Exceptions recorded for this task. |
| `call_count` | int | yes | Model calls recorded for this task. |
| `prompt_tokens` | int | yes | Uncached input tokens. |
| `cached_tokens` | int | yes | Cached input tokens. |
| `completion_tokens` | int | yes | Output tokens. |
| `cost_usd` | decimal(6) | yes | Cost, summed from this task's calls. |
| `latency_seconds` | decimal | yes | Task duration. |
| `error` | string | yes | Exception text, where one was recorded. |

---

## `model_calls.csv` — one row per model call

**67,529 rows.** Message and tool payload text is not in this table; see
trajectories.

| column | type | null | description |
|---|---|---|---|
| `call_id` | string | no | Primary key. |
| `run_id` | string | no | Foreign key to `runs.csv`. |
| `task_id` | string | no | With `run_id`, foreign key to `tasks.csv`. |
| `call_index` | int | no | Zero-based order within the run. |
| `harness_phase` | enum | no | `planning`, `execution`, `recovery`, or `finalization`. |
| `prompt_tokens` | int | no | Uncached input tokens. |
| `cached_tokens` | int | no | Cached input tokens. |
| `completion_tokens` | int | no | Output tokens. |
| `latency_seconds` | decimal | no | Call duration. |
| `exception_type` | string | yes | Exception family, where the call raised one. |
| `total_cost_usd` | decimal(6) | no | Cost for this call. |

---

## How the tables relate

```
runs.csv  1 ──< tasks.csv  1 ──< model_calls.csv
  run_id        (run_id, task_id)     call_id
```

- Every task row resolves to exactly one run; every call resolves to exactly one task row.
- Call costs sum to the task's `cost_usd`; task costs sum to the run's `total_cost_usd`.
- `prompt_tokens` excludes cached tokens, which are counted separately at every level.

---

## Units and precision

| quantity | unit | precision |
|---|---|---|
| money | USD | 6 decimal places, fixed notation |
| tokens | count | integer |
| latency | seconds | 3 decimal places |

---

## Trajectories

Step-by-step traces of what each harness did. Each trace has one step per row in
`model_calls.csv` for that task — same order, same phase, same usage — followed by a
closing step that carries no usage. Coverage is 2,493 of 2,550 task rows.

| path | contents |
|---|---|
| `trajectories/selected/*.json` | 10 traces, readable directly, no tooling |
| `trajectories/archive.jsonl.zst` | all traces, zstd-compressed JSON Lines (~23 MB decompressed) |
| `trajectories/trajectory_index.csv` | `run_id`, `task_id`, `benchmark_id`, `n_steps`, `record_index`, `record_offset` |
| `get_trajectory` | `python3 get_trajectory <run_id> <task_id>`, or `--list-runs` |

`get_trajectory` needs the `zstandard` package and works entirely offline.

Each step carries:

| field | meaning |
|---|---|
| `step`, `harness_phase` | Position and phase, matching `model_calls.csv`. |
| `tool`, `tool_input` | The tool invoked and its arguments, where one was called. |
| `tool_output` | What the tool returned. |
| `reasoning` | The harness's stated reasoning at that step. |
| `raw_response` | Raw response text, where recorded. |
| token counts, `latency_seconds`, `exception_type` | As in `model_calls.csv`. |
