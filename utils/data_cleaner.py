import pandas as pd
import numpy as np
from config import MAX_PREVIEW_ROWS


def get_column_info(df):
    """Get column metadata and summary statistics."""
    columns = []
    total_nulls = 0
    numeric_cols = 0
    categorical_cols = 0

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = round((null_count / len(df)) * 100, 2) if len(df) > 0 else 0
        unique_count = int(df[col].nunique())
        dtype_str = str(df[col].dtype)

        # Categorize dtype
        if pd.api.types.is_numeric_dtype(df[col].dtype):
            dtype_label = 'numeric'
            numeric_cols += 1
        elif pd.api.types.is_datetime64_any_dtype(df[col].dtype):
            dtype_label = 'datetime'
        elif pd.api.types.is_bool_dtype(df[col].dtype):
            dtype_label = 'boolean'
        else:
            dtype_label = 'categorical'
            categorical_cols += 1

        # Sample values (non-null)
        sample = df[col].dropna().head(5).tolist()
        # Convert numpy types to native Python types
        sample = [v.item() if hasattr(v, 'item') else v for v in sample]

        columns.append({
            'name': str(col),
            'dtype': dtype_str,
            'dtype_str': dtype_label,
            'null_count': null_count,
            'null_pct': null_pct,
            'unique_count': unique_count,
            'sample_values': sample
        })
        total_nulls += null_count

    summary = {
        'rows': len(df),
        'columns': len(df.columns),
        'total_nulls': total_nulls,
        'duplicates': int(df.duplicated().sum()),
        'numeric_cols': numeric_cols,
        'categorical_cols': categorical_cols + (len(columns) - numeric_cols - categorical_cols)
    }

    return {'columns': columns, 'summary': summary}


def get_preview_data(df, max_rows=None):
    """Get first N rows as list of dicts for JSON serialization."""
    if max_rows is None:
        max_rows = MAX_PREVIEW_ROWS
    preview = df.head(max_rows).copy()
    # Replace NaN with None for JSON
    preview = preview.where(pd.notnull(preview), None)
    records = preview.to_dict(orient='records')
    # Convert any remaining numpy types
    for rec in records:
        for k, v in rec.items():
            if hasattr(v, 'item'):
                rec[k] = v.item()
            elif isinstance(v, float) and np.isnan(v):
                rec[k] = None
    return records


def drop_missing(df, columns=None, how='any'):
    """Drop rows with missing values."""
    rows_before = len(df)
    if columns and len(columns) > 0:
        valid_cols = [c for c in columns if c in df.columns]
        if not valid_cols:
            return df, {'rows_before': rows_before, 'rows_after': rows_before, 'rows_removed': 0}
        df = df.dropna(subset=valid_cols, how=how)
    else:
        df = df.dropna(how=how)
    rows_after = len(df)
    return df, {
        'rows_before': rows_before,
        'rows_after': rows_after,
        'rows_removed': rows_before - rows_after
    }


def fill_missing(df, columns, method='mean', fill_value=None):
    """Fill missing values."""
    if not columns or len(columns) == 0:
        return df, {'columns_filled': [], 'nulls_filled_per_col': {}}

    valid_cols = [c for c in columns if c in df.columns]
    if not valid_cols:
        return df, {'columns_filled': [], 'nulls_filled_per_col': {}}

    nulls_before = {c: int(df[c].isna().sum()) for c in valid_cols}
    df = df.copy()

    for col in valid_cols:
        if method == 'mean':
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].mean())
        elif method == 'median':
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
        elif method == 'mode':
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
        elif method == 'constant':
            if fill_value is not None:
                df[col] = df[col].fillna(fill_value)
        elif method == 'ffill':
            df[col] = df[col].ffill()
        elif method == 'bfill':
            df[col] = df[col].bfill()

    nulls_after = {c: int(df[c].isna().sum()) for c in valid_cols}
    nulls_filled = {c: nulls_before[c] - nulls_after[c] for c in valid_cols}

    return df, {
        'columns_filled': valid_cols,
        'nulls_filled_per_col': nulls_filled,
        'total_filled': sum(nulls_filled.values())
    }


def drop_duplicates(df, subset=None):
    """Remove duplicate rows."""
    rows_before = len(df)
    if subset and len(subset) > 0:
        valid_cols = [c for c in subset if c in df.columns]
        df = df.drop_duplicates(subset=valid_cols if valid_cols else None)
    else:
        df = df.drop_duplicates()
    rows_after = len(df)
    return df, {
        'rows_before': rows_before,
        'rows_after': rows_after,
        'duplicates_removed': rows_before - rows_after
    }


def detect_outliers(df, columns, method='iqr', threshold=1.5):
    """Detect outliers (does not modify data)."""
    if not columns:
        return {'outlier_indices': {}, 'outlier_counts': {}, 'outlier_pct': {}}

    valid_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not valid_cols:
        return {'outlier_indices': {}, 'outlier_counts': {}, 'outlier_pct': {}}

    outlier_indices = {}
    outlier_counts = {}
    outlier_pct = {}

    for col in valid_cols:
        col_data = df[col].dropna()
        if method == 'iqr':
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            mask = (df[col] < lower) | (df[col] > upper)
        else:  # zscore
            from scipy import stats as sp_stats
            z_scores = np.abs(sp_stats.zscore(col_data))
            # Reindex to original df
            mask = pd.Series(False, index=df.index)
            mask.loc[col_data.index] = z_scores > threshold

        indices = df.index[mask].tolist()
        outlier_indices[col] = indices
        outlier_counts[col] = len(indices)
        outlier_pct[col] = round(len(indices) / len(df) * 100, 2) if len(df) > 0 else 0

    return {
        'outlier_indices': {k: v[:50] for k, v in outlier_indices.items()},  # limit to 50
        'outlier_counts': outlier_counts,
        'outlier_pct': outlier_pct
    }


def handle_outliers(df, columns, method='remove', threshold=1.5):
    """Handle outliers (remove or cap)."""
    if not columns:
        return df, {'rows_before': len(df), 'rows_after': len(df), 'action': method}

    rows_before = len(df)
    df = df.copy()

    valid_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not valid_cols:
        return df, {'rows_before': rows_before, 'rows_after': len(df), 'action': method}

    if method == 'remove':
        mask = pd.Series(False, index=df.index)
        for col in valid_cols:
            col_data = df[col].dropna()
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            mask = mask | (df[col] < lower) | (df[col] > upper)
        df = df[~mask]

    elif method == 'cap':
        for col in valid_cols:
            col_data = df[col].dropna()
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            df[col] = df[col].clip(lower=lower, upper=upper)

    rows_after = len(df)
    return df, {
        'rows_before': rows_before,
        'rows_after': rows_after,
        'action': method,
        'rows_affected': rows_before - rows_after if method == 'remove' else 'capped'
    }


def convert_column_type(df, column, new_type='float'):
    """Convert a column to a new data type."""
    if column not in df.columns:
        return df, {'error': f'Column "{column}" not found'}

    old_type = str(df[column].dtype)
    na_before = int(df[column].isna().sum())

    try:
        if new_type == 'int':
            df[column] = pd.to_numeric(df[column], errors='coerce').astype('Int64')
        elif new_type == 'float':
            df[column] = pd.to_numeric(df[column], errors='coerce')
        elif new_type == 'str':
            df[column] = df[column].astype(str)
        elif new_type == 'datetime':
            df[column] = pd.to_datetime(df[column], errors='coerce')
        elif new_type == 'category':
            df[column] = df[column].astype('category')
    except Exception as e:
        return df, {'error': str(e)}

    na_after = int(df[column].isna().sum())
    return df, {
        'column': column,
        'old_type': old_type,
        'new_type': new_type,
        'na_introduced': na_after - na_before
    }
