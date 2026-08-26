import os
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def analyze_spreadsheet(file_path, sheet_name=None):
    """
    Reads an Excel or CSV file and performs comprehensive automated data analysis.
    Returns:
    {
        "filename": str,
        "sheet_names": list,
        "active_sheet": str,
        "row_count": int,
        "column_count": int,
        "columns": list,
        "dtypes": dict,
        "missing_values": dict,
        "total_missing": int,
        "duplicate_rows": int,
        "summary_statistics": dict,
        "categorical_summary": dict,
        "sample_data": list of dicts,
        "suggested_charts": list
    }
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    sheet_names = []
    if ext in [".xlsx", ".xls"]:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        target_sheet = sheet_name if sheet_name in sheet_names else sheet_names[0]
        df = pd.read_excel(file_path, sheet_name=target_sheet)
    else:
        target_sheet = "Sheet1"
        try:
            df = pd.read_csv(file_path)
        except Exception:
            df = pd.read_csv(file_path, encoding="latin-1")

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    row_count, col_count = df.shape
    duplicate_rows = int(df.duplicated().sum())

    # Missing values
    missing_dict = df.isnull().sum().to_dict()
    total_missing = int(df.isnull().sum().sum())

    # Data types
    dtypes_dict = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # Numerical statistics
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()

    stats_summary = {}
    if num_cols:
        desc = df[num_cols].describe().to_dict()
        for col in num_cols:
            stats_summary[col] = {
                "mean": round(float(desc[col].get("mean", 0)), 2) if not np.isnan(desc[col].get("mean", 0)) else 0,
                "min": round(float(desc[col].get("min", 0)), 2) if not np.isnan(desc[col].get("min", 0)) else 0,
                "max": round(float(desc[col].get("max", 0)), 2) if not np.isnan(desc[col].get("max", 0)) else 0,
                "median": round(float(df[col].median()), 2) if not df[col].empty else 0,
                "std": round(float(desc[col].get("std", 0)), 2) if not np.isnan(desc[col].get("std", 0)) else 0
            }

    # Categorical summary
    cat_summary = {}
    for col in cat_cols[:8]:
        top_vals = df[col].value_counts().head(5).to_dict()
        cat_summary[col] = {
            "unique_count": int(df[col].nunique()),
            "top_values": {str(k): int(v) for k, v in top_vals.items()}
        }

    # Sample rows
    sample_df = df.head(15).replace({np.nan: None})
    sample_data = sample_df.to_dict(orient="records")

    # Suggested charts
    suggested_charts = _generate_suggested_charts(df, num_cols, cat_cols)

    return {
        "filename": os.path.basename(file_path),
        "sheet_names": sheet_names,
        "active_sheet": target_sheet,
        "row_count": row_count,
        "column_count": col_count,
        "columns": list(df.columns),
        "dtypes": dtypes_dict,
        "missing_values": {k: int(v) for k, v in missing_dict.items()},
        "total_missing": total_missing,
        "duplicate_rows": duplicate_rows,
        "summary_statistics": stats_summary,
        "categorical_summary": cat_summary,
        "sample_data": sample_data,
        "suggested_charts": suggested_charts
    }


def query_spreadsheet_data(file_path, query_type="summary", params=None):
    """
    Executes specific safe analytical queries on spreadsheet data.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    df.columns = [str(c).strip() for c in df.columns]

    if query_type == "top_n":
        col = params.get("column")
        n = int(params.get("n", 10))
        if col in df.columns:
            sorted_df = df.sort_values(by=col, ascending=False).head(n)
            return sorted_df.replace({np.nan: None}).to_dict(orient="records")

    elif query_type == "group_by":
        group_col = params.get("group_column")
        agg_col = params.get("agg_column")
        agg_func = params.get("function", "sum")
        if group_col in df.columns and agg_col in df.columns:
            grouped = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
            return grouped.replace({np.nan: None}).to_dict(orient="records")

    return df.head(10).replace({np.nan: None}).to_dict(orient="records")


def _generate_suggested_charts(df, num_cols, cat_cols):
    """Creates Chart.js compatible configuration for the dataset."""
    charts = []

    # Chart 1: If we have categorical + numerical, create Bar Chart
    if cat_cols and num_cols:
        cat = cat_cols[0]
        num = num_cols[0]
        grouped = df.groupby(cat)[num].sum().reset_index().sort_values(by=num, ascending=False).head(8)
        
        charts.append({
            "title": f"Total {num} by {cat}",
            "type": "bar",
            "data": {
                "labels": [str(x) for x in grouped[cat].tolist()],
                "datasets": [{
                    "label": num,
                    "data": [float(x) for x in grouped[num].tolist()],
                    "backgroundColor": [
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(239, 68, 68, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(20, 184, 166, 0.8)",
                        "rgba(107, 114, 128, 0.8)"
                    ]
                }]
            }
        })

    # Chart 2: Categorical Distribution Pie Chart
    if cat_cols:
        cat = cat_cols[0]
        top_cats = df[cat].value_counts().head(6)
        charts.append({
            "title": f"Distribution of {cat}",
            "type": "doughnut",
            "data": {
                "labels": [str(x) for x in top_cats.index.tolist()],
                "datasets": [{
                    "data": [int(x) for x in top_cats.values.tolist()],
                    "backgroundColor": [
                        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"
                    ]
                }]
            }
        })

    # Chart 3: Numerical trend / distribution Line or Bar
    if len(num_cols) >= 2:
        col1, col2 = num_cols[0], num_cols[1]
        sample = df[[col1, col2]].dropna().head(12)
        charts.append({
            "title": f"{col1} vs {col2} Trend",
            "type": "line",
            "data": {
                "labels": [f"Row {i+1}" for i in range(len(sample))],
                "datasets": [
                    {
                        "label": col1,
                        "data": [float(x) for x in sample[col1].tolist()],
                        "borderColor": "#3b82f6",
                        "backgroundColor": "rgba(59, 130, 246, 0.2)",
                        "fill": True,
                        "tension": 0.3
                    },
                    {
                        "label": col2,
                        "data": [float(x) for x in sample[col2].tolist()],
                        "borderColor": "#10b981",
                        "backgroundColor": "rgba(16, 185, 129, 0.2)",
                        "fill": True,
                        "tension": 0.3
                    }
                ]
            }
        })

    return charts
