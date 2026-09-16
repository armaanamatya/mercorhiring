import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


def plot_regression_diagnostics(
    regression_output,
    evaluation_tasks_with_outcomes,
):
    """
    Validate the candidate's regression output, join it to the actual
    task outcomes, and generate three standardized diagnostic plots.

    Required regression_output columns:
      run_id
      task_id
      predicted_probability
      model
      harness
      benchmark
      assigned_token_budget
      actual_token_consumption

    Required evaluation_tasks_with_outcomes columns:
      run_id
      task_id
      passed

    This function does not normalize, transform, or reconstruct any of
    the candidate's feature values.
    """

    required_output_columns = [
        "run_id",
        "task_id",
        "predicted_probability",
        "model",
        "harness",
        "benchmark",
        "assigned_token_budget",
        "actual_token_consumption",
    ]

    required_outcome_columns = [
        "run_id",
        "task_id",
        "passed",
    ]

    # ------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------

    if not isinstance(regression_output, pd.DataFrame):
        raise TypeError("fit_and_predict must return a pandas DataFrame.")

    if not isinstance(evaluation_tasks_with_outcomes, pd.DataFrame):
        raise TypeError(
            "evaluation_tasks_with_outcomes must be a pandas DataFrame."
        )

    missing_output_columns = [
        column
        for column in required_output_columns
        if column not in regression_output.columns
    ]

    if missing_output_columns:
        raise ValueError(
            "regression_output is missing required columns: "
            f"{missing_output_columns}"
        )

    missing_outcome_columns = [
        column
        for column in required_outcome_columns
        if column not in evaluation_tasks_with_outcomes.columns
    ]

    if missing_outcome_columns:
        raise ValueError(
            "evaluation_tasks_with_outcomes is missing required columns: "
            f"{missing_outcome_columns}"
        )

    output = regression_output[required_output_columns].copy()

    outcomes = evaluation_tasks_with_outcomes[
        required_outcome_columns
    ].copy()

    # Tasks without an observed pass/fail outcome cannot be evaluated.
    outcomes = outcomes[outcomes["passed"].notna()].copy()

    if output.duplicated(["run_id", "task_id"]).any():
        raise ValueError(
            "regression_output contains duplicate run_id/task_id pairs."
        )

    if outcomes.duplicated(["run_id", "task_id"]).any():
        raise ValueError(
            "evaluation_tasks_with_outcomes contains duplicate "
            "run_id/task_id pairs."
        )

    expected_pairs = pd.MultiIndex.from_frame(
        outcomes[["run_id", "task_id"]]
    )

    returned_pairs = pd.MultiIndex.from_frame(
        output[["run_id", "task_id"]]
    )

    missing_pairs = expected_pairs.difference(returned_pairs)
    extra_pairs = returned_pairs.difference(expected_pairs)

    if len(missing_pairs):
        raise ValueError(
            f"regression_output is missing {len(missing_pairs)} "
            "evaluation tasks."
        )

    if len(extra_pairs):
        raise ValueError(
            f"regression_output contains {len(extra_pairs)} unexpected tasks."
        )

    numeric_columns = [
        "predicted_probability",
        "assigned_token_budget",
        "actual_token_consumption",
    ]

    for column in numeric_columns:
        output[column] = pd.to_numeric(output[column], errors="coerce")

        if output[column].isna().any():
            raise ValueError(
                f"{column} contains missing or nonnumeric values."
            )

        if not np.isfinite(output[column]).all():
            raise ValueError(f"{column} contains non-finite values.")

    if (
        (output["predicted_probability"] < 0)
        | (output["predicted_probability"] > 1)
    ).any():
        raise ValueError(
            "predicted_probability values must fall between zero and one."
        )

    grouping_columns = [
        "model",
        "harness",
        "benchmark",
    ]

    for column in grouping_columns:
        if output[column].isna().any():
            raise ValueError(f"{column} contains missing values.")

        output[column] = output[column].astype(str)

    # ------------------------------------------------------------
    # Join the candidate's output to the outcomes
    # ------------------------------------------------------------

    scored = output.merge(
        outcomes,
        on=["run_id", "task_id"],
        how="inner",
        validate="one_to_one",
    )

    if pd.api.types.is_bool_dtype(scored["passed"]):
        scored["passed_numeric"] = scored["passed"].astype(float)
    elif pd.api.types.is_numeric_dtype(scored["passed"]):
        scored["passed_numeric"] = pd.to_numeric(
            scored["passed"],
            errors="coerce",
        )
    else:
        scored["passed_numeric"] = (
            scored["passed"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": 1.0,
                    "false": 0.0,
                    "1": 1.0,
                    "0": 0.0,
                }
            )
        )

    if scored["passed_numeric"].isna().any():
        raise ValueError("passed contains values other than true/false.")

    if not scored["passed_numeric"].isin([0.0, 1.0]).all():
        raise ValueError("passed must contain only binary outcomes.")

    scored["residual"] = (
        scored["passed_numeric"]
        - scored["predicted_probability"]
    )

    scored["squared_error"] = scored["residual"] ** 2

    overall_brier = scored["squared_error"].mean()

    # ============================================================
    # Plot A: Calibration
    # ============================================================

    calibration_data = scored.copy()

    number_of_unique_predictions = (
        calibration_data["predicted_probability"].nunique()
    )

    if number_of_unique_predictions == 1:
        calibration_data["probability_bin"] = 1
    else:
        calibration_data["probability_bin"] = pd.qcut(
            calibration_data["predicted_probability"],
            q=min(5, number_of_unique_predictions),
            labels=False,
            duplicates="drop",
        ) + 1

    calibration = (
        calibration_data.groupby("probability_bin", observed=True)
        .agg(
            mean_prediction=("predicted_probability", "mean"),
            observed_success=("passed_numeric", "mean"),
            n=("passed_numeric", "size"),
        )
        .reset_index()
    )

    calibration_figure, calibration_axis = plt.subplots(
        figsize=(7, 6)
    )

    calibration_axis.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        color="#8A8A8A",
        label="Perfect calibration",
    )

    calibration_axis.plot(
        calibration["mean_prediction"],
        calibration["observed_success"],
        marker="o",
        linewidth=2,
        color="#2457C5",
        label="Regression",
    )

    for row in calibration.itertuples():
        calibration_axis.annotate(
            f"n={row.n}",
            (row.mean_prediction, row.observed_success),
            xytext=(5, 6),
            textcoords="offset points",
            fontsize=8,
        )

    calibration_axis.set(
        title=(
            "Plot A — Calibration\n"
            f"Overall Brier loss: {overall_brier:.3f}"
        ),
        xlabel="Mean predicted probability",
        ylabel="Observed success rate",
        xlim=(0, 1),
        ylim=(0, 1),
    )

    calibration_axis.legend()
    calibration_axis.grid(alpha=0.2)
    calibration_figure.tight_layout()

    # ============================================================
    # Plot B: Predictive performance by candidate-defined group
    # ============================================================

    group_definitions = [
        ("Model", "model"),
        ("Harness", "harness"),
        ("Benchmark", "benchmark"),
        ("Budget", "assigned_token_budget"),
    ]

    group_rows = []

    for dimension, column in group_definitions:
        grouped = (
            scored.groupby(column, observed=True)
            .agg(
                brier_loss=("squared_error", "mean"),
                mean_prediction=("predicted_probability", "mean"),
                observed_success=("passed_numeric", "mean"),
                n=("passed_numeric", "size"),
            )
            .reset_index()
        )

        for row in grouped.to_dict("records"):
            group_rows.append(
                {
                    "dimension": dimension,
                    "group": str(row[column]),
                    "label": f"{dimension} · {row[column]}",
                    "brier_loss": row["brier_loss"],
                    "calibration_gap": (
                        row["observed_success"]
                        - row["mean_prediction"]
                    ),
                    "n": row["n"],
                }
            )

    group_performance = pd.DataFrame(group_rows)

    dimension_colors = {
        "Model": "#2457C5",
        "Harness": "#7A4CC2",
        "Benchmark": "#D66B2C",
        "Budget": "#23856D",
    }

    group_figure_height = max(
        6,
        0.45 * len(group_performance),
    )

    group_figure, group_axis = plt.subplots(
        figsize=(11, group_figure_height)
    )

    positions = np.arange(len(group_performance))

    group_axis.scatter(
        group_performance["brier_loss"],
        positions,
        color=[
            dimension_colors[dimension]
            for dimension in group_performance["dimension"]
        ],
        s=60,
        zorder=3,
    )

    group_axis.axvline(
        overall_brier,
        linestyle="--",
        color="#777777",
        label=f"Overall Brier loss: {overall_brier:.3f}",
    )

    annotation_offset = max(
        group_performance["brier_loss"].max() * 0.025,
        0.002,
    )

    for position, row in enumerate(group_performance.itertuples()):
        group_axis.text(
            row.brier_loss + annotation_offset,
            position,
            (
                f"n={row.n}, "
                f"calibration gap={row.calibration_gap:+.3f}"
            ),
            va="center",
            fontsize=8,
        )

    group_axis.set_yticks(positions)
    group_axis.set_yticklabels(group_performance["label"])
    group_axis.invert_yaxis()

    group_axis.set(
        title="Plot B — Predictive performance by group",
        xlabel="Brier loss — lower is better",
        ylabel="",
    )

    group_axis.legend()
    group_axis.grid(axis="x", alpha=0.2)

    largest_x_value = max(
        group_performance["brier_loss"].max(),
        overall_brier,
    )

    group_axis.set_xlim(
        left=0,
        right=max(largest_x_value * 1.45, 0.05),
    )

    group_figure.tight_layout()

    # ============================================================
    # Plot C: Residuals by consumption, budget, and harness
    # ============================================================

    def assign_consumption_bands(values):
        unique_values = values.nunique()

        if unique_values == 1:
            return pd.Series(
                1,
                index=values.index,
                dtype=int,
            )

        return (
            pd.qcut(
                values,
                q=min(5, unique_values),
                labels=False,
                duplicates="drop",
            )
            + 1
        )

    scored["consumption_band"] = (
        scored.groupby(
            "assigned_token_budget",
            group_keys=False,
        )["actual_token_consumption"]
        .transform(assign_consumption_bands)
        .astype(int)
    )

    residual_summary = (
        scored.groupby(
            [
                "assigned_token_budget",
                "harness",
                "consumption_band",
            ],
            observed=True,
        )
        .agg(
            mean_residual=("residual", "mean"),
            n=("residual", "size"),
        )
        .reset_index()
    )

    budgets = sorted(
        residual_summary["assigned_token_budget"].unique()
    )

    residual_figure, residual_axes = plt.subplots(
        1,
        len(budgets),
        figsize=(5 * len(budgets), 5),
        sharey=True,
        squeeze=False,
    )

    harnesses = sorted(residual_summary["harness"].unique())
    color_map = plt.get_cmap("tab10")

    harness_colors = {
        harness: color_map(index)
        for index, harness in enumerate(harnesses)
    }

    for axis, budget in zip(residual_axes[0], budgets):
        budget_data = residual_summary[
            residual_summary["assigned_token_budget"] == budget
        ]

        for harness, harness_data in budget_data.groupby(
            "harness",
            observed=True,
        ):
            harness_data = harness_data.sort_values(
                "consumption_band"
            )

            axis.plot(
                harness_data["consumption_band"],
                harness_data["mean_residual"],
                marker="o",
                linewidth=2,
                label=harness,
                color=harness_colors[harness],
            )

        axis.axhline(
            0,
            linestyle="--",
            color="#777777",
        )

        axis.set(
            title=f"Assigned budget: {budget:g}",
            xlabel="Actual token-consumption band",
        )

        axis.set_xticks(range(1, 6))
        axis.set_xticklabels(
            ["Lowest", "Low", "Middle", "High", "Highest"],
            rotation=30,
            ha="right",
        )

        axis.grid(alpha=0.2)

    residual_axes[0][0].set_ylabel(
        "Mean residual\n"
        "(actual outcome − predicted probability)"
    )

    residual_figure.suptitle(
        "Plot C — Residual patterns by actual token consumption",
        y=0.98,
    )

    # Build the legend from every harness in the scored data rather than
    # from one budget panel. This keeps harnesses that are absent from the
    # final panel visible in the figure-wide legend.
    legend_handles = [
        Line2D(
            [0],
            [0],
            color=harness_colors[harness],
            marker="o",
            linewidth=2,
            label=harness,
        )
        for harness in harnesses
    ]

    if legend_handles:
        residual_figure.legend(
            handles=legend_handles,
            labels=harnesses,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.01),
            ncol=min(4, len(harnesses)),
            fontsize=8,
            frameon=False,
        )

    residual_figure.tight_layout(
        rect=(0, 0.09 if legend_handles else 0, 1, 0.94)
    )

    plt.show()

    return {
        "calibration": calibration_figure,
        "group_performance": group_figure,
        "residual_patterns": residual_figure,
    }
