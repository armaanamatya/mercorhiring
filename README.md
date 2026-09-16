# Benchmark

Mercor Research Engineers build the benchmarking and
failure-analysis systems that determine how frontier models are trained. Your goal here is to derive defensible conclusions from messy evaluation data without mistaking noise for signal. 

This package holds 54 completed runs from one evaluation campaign, including three tables and their harness trajectories.

**Your primary deliverable is `SUBMISSION.ipynb`.** Open it first. It contains fifteen
questions in five sections: data interpretation, performance analysis, trajectories
and runs, cost analysis, and modelling. Each question includes space for your code and conclusion; Question 15 asks you to implement a function.

## The walkthrough

After submitting, you'll record a short video answering questions about your work. **Your demonstrated understanding in this walkthrough is central in your evaluation.**

You must be able to explain every answer you submitted and will be severely penalized if you are unable to. If you're short on time, submit partial work you understand rather than answers you don't understand. 

## Important data distinctions

Two fields in this data are easy to conflate, and several questions turn on the
difference: the **harness** (`harness_name`) is how the agent is organised, and the
**runner** (`runner_version`) is the software version that executed the run. They vary
independently.

Passing is a property of a **task**, not of a run. `tasks.csv` carries `passed` per
task; `runs.csv` carries counts — `tasks_expected`, `tasks_executed`, `tasks_passed` —
and no pass or score column of its own. Where a question asks about a run's score or
pass rate, it is asking for something you compute from tasks.

- **Time expectation: 60 minutes**
- Answer inside the notebook. Everything you need is in this folder.
- Save with your cell outputs intact. Do not clear outputs, and do not rename the file.

## Files

| file | contents |
|---|---|
| `SUBMISSION.ipynb` | **your deliverable**, the fifteen questions and your working |
| `runs.csv` | one row per run |
| `tasks.csv` | one row per (run, task) |
| `model_calls.csv` | one row per model call |
| `data_dictionary.md` | table and column reference |
| `trajectories/trajectory_index.csv` | maps run and task to a trajectory record |
| `trajectories/selected/` | ten traces, readable directly |
| `trajectories/archive.jsonl.zst` | all traces, compressed |
| `get_trajectory` | `python3 get_trajectory <run_id> <task_id>` |
| `regression_diagnostics.py` | the diagnostic plots Q15 asks you to produce; imported, not edited |
| `requirements.txt` | the Python dependencies, installed into `venv/` by `litmus init` |

## Getting started

Activate the environment created by `litmus init`, then open the notebook:  

```
source venv/bin/activate      # Windows: venv\Scripts\activate
jupyter lab SUBMISSION.ipynb
```

If `jupyter` isn't found, the install didn't run, so do it yourself:

```
python3 -m venv venv && venv/bin/pip install -r requirements.txt
```

An IDE works just as well. In VS Code or Cursor, install the Python and Jupyter
extensions, open `SUBMISSION.ipynb` directly, and select `venv` as the kernel.
Do not convert the
notebook to a `.py` and back, because the round trip drops your figures.

To read trajectories:

```
python3 get_trajectory run_0000 art-001     # one trace
python3 get_trajectory --list-runs          # runs that have trajectories
```

## Working in the notebook

**Use one editor at a time.** JupyterLab and your IDE keep separate in-memory copies and kernels. Each keeps its own copy in memory and the last
one to save wins and variables do not carry over between them. 

**Edit answer cells in place.** Clearing a cell and typing into it is fine. Deleting
one and adding a fresh cell is not, because the cells are tagged and that is how your
answers are found. Keep the `**Answer to Qn**` heading as well.

**Restart and run everything before you finish.** Cells run out of order leave you with
a notebook that works on your screen and is broken on disk. Restart the kernel, run all
cells top to bottom, then save.

## Question 15

Your `fit_and_predict` is re-run on unseen data. Only that cell is extracted so imports are preserved but variables and helper functions defined in other cells are not:

- Define helper functions inside the Question 15 cell.
- Don't rely on a variable you set up earlier. 
- Use only packages listed in `requirements.txt`.

The cell's docstring gives the signature and output columns. 
## Before you submit

1. Restart the kernel and run all cells, top to bottom.
2. Save the notebook.
3. Run the last cell. It reads `SUBMISSION.ipynb` back **from disk** and reports how
   many answers it can find, so it catches both a broken answer cell and edits you have
   not saved. Expect `14/14` — Question 15 is code and has no answer cell, so the check
   reports on it separately, saying whether `fit_and_predict` is still the unmodified
   template.
4. Check your plots are still visible in the saved notebook.
5. Submit:

```
litmus submit
```

6. After you submit, you record your walkthrough. Be prepared to explain the reasoning, code, and conclusions behind every answer you submitted.