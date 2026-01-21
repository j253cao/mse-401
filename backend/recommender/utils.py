"""Utility functions for course recommendations."""

import pandas as pd


def export_results_to_excel(dfs, output_path, sheet_names=None):
    """Export recommendation results to Excel file."""
    with pd.ExcelWriter(output_path) as writer:
        for i, df in enumerate(dfs):
            name = sheet_names[i] if sheet_names and i < len(sheet_names) else f"Sheet{i+1}"
            df.to_excel(writer, sheet_name=name, index=False)

