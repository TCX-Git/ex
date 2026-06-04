import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, silhouette_score


def basic_statistics(df):
    """Compute basic statistics for all columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number, 'datetime', 'datetimetz']).columns.tolist()

    numeric_stats = []
    for col in numeric_cols:
        col_data = df[col].dropna()
        numeric_stats.append({
            'column': col,
            'count': int(len(col_data)),
            'mean': round(float(col_data.mean()), 4),
            'std': round(float(col_data.std()), 4),
            'min': round(float(col_data.min()), 4),
            '25%': round(float(col_data.quantile(0.25)), 4),
            '50%': round(float(col_data.quantile(0.50)), 4),
            '75%': round(float(col_data.quantile(0.75)), 4),
            'max': round(float(col_data.max()), 4),
            'skewness': round(float(col_data.skew()), 4),
            'kurtosis': round(float(col_data.kurtosis()), 4)
        })

    categorical_stats = []
    for col in categorical_cols:
        col_data = df[col].dropna()
        top_val = col_data.mode().iloc[0] if len(col_data.mode()) > 0 else None
        freq = int(col_data.value_counts().iloc[0]) if len(col_data) > 0 else 0
        categorical_stats.append({
            'column': col,
            'count': int(len(col_data)),
            'unique': int(col_data.nunique()),
            'top': str(top_val) if top_val is not None else None,
            'freq': freq
        })

    return {
        'numeric_stats': numeric_stats,
        'categorical_stats': categorical_stats
    }


def correlation_matrix(df):
    """Compute correlation matrix for numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return {'columns': numeric_df.columns.tolist(), 'matrix': []}

    corr = numeric_df.corr()
    columns = corr.columns.tolist()
    matrix = []
    for i, row_col in enumerate(columns):
        row = []
        for j, col_col in enumerate(columns):
            val = corr.iloc[i, j]
            row.append(round(float(val), 4) if not np.isnan(val) else None)
        matrix.append(row)

    return {
        'columns': [str(c) for c in columns],
        'matrix': matrix
    }


def kmeans_clustering(df, columns, n_clusters=3, random_state=42):
    """Run K-Means clustering on selected numeric columns."""
    if not columns or len(columns) < 2:
        return {'error': '请至少选择 2 个数值列进行 K-Means 聚类。'}

    valid_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(valid_cols) < 2:
        return {'error': '需要至少 2 个有效数值列。'}

    data = df[valid_cols].dropna()
    if len(data) < n_clusters:
        return {'error': f'有效数据行数 ({len(data)}) 少于聚类数 ({n_clusters})。请减少聚类数。'}
    if len(data) < 5:
        return {'error': f'有效数据行数不足 (当前 {len(data)} 行，需要至少 5 行)。'}

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data)

    # Clustering
    n_clusters = min(n_clusters, len(data) - 1)
    n_clusters = max(2, n_clusters)
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init='auto')
    labels = kmeans.fit_predict(X_scaled)

    # Centroids in original scale
    centroids_scaled = kmeans.cluster_centers_
    centroids_original = scaler.inverse_transform(centroids_scaled)

    # PCA for 2D visualization
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    centroids_pca = pca.transform(centroids_scaled)

    # Silhouette score
    sil_score = None
    if n_clusters >= 2 and n_clusters < len(data):
        try:
            sil_score = round(float(silhouette_score(X_scaled, labels)), 4)
        except Exception:
            sil_score = None

    # Cluster sizes
    unique, counts = np.unique(labels, return_counts=True)
    cluster_sizes = {int(k): int(v) for k, v in zip(unique, counts)}

    return {
        'labels': labels.tolist(),
        'centroids': [[round(float(v), 4) for v in c] for c in centroids_original],
        'centroids_pca': [[round(float(v), 4) for v in c] for c in centroids_pca],
        'inertia': round(float(kmeans.inertia_), 4),
        'silhouette_score': sil_score,
        'data_points': [[round(float(p[0]), 4), round(float(p[1]), 4)] for p in X_pca],
        'explained_variance': [round(float(v), 4) for v in pca.explained_variance_ratio_],
        'n_samples': len(data),
        'columns_used': valid_cols,
        'cluster_sizes': cluster_sizes,
        'n_clusters': n_clusters
    }


def linear_regression(df, x_columns, y_column, test_size=0.2, random_state=42):
    """Run Linear Regression with train/test split."""
    if not y_column or y_column not in df.columns:
        return {'error': '请选择目标变量 (Y)。'}
    if not x_columns or len(x_columns) == 0:
        return {'error': '请至少选择一个特征变量 (X)。'}

    if not pd.api.types.is_numeric_dtype(df[y_column]):
        return {'error': f'目标变量 "{y_column}" 必须是数值类型。'}

    # Prepare feature columns
    valid_x = []
    for c in x_columns:
        if c not in df.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            valid_x.append(c)

    if not valid_x:
        return {'error': '没有有效的数值特征列。请选择数值列作为特征。'}

    # Build feature matrix
    X = df[valid_x].copy()

    # Handle categorical columns if selected (not purely numeric)
    cat_cols = [c for c in x_columns if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])]
    for c in cat_cols:
        dummies = pd.get_dummies(df[c], prefix=c, drop_first=True)
        X = pd.concat([X, dummies], axis=1)

    # Drop rows with NaN
    combined = pd.concat([X, df[y_column].rename('__target__')], axis=1)
    combined = combined.dropna()

    if len(combined) < 10:
        return {'error': f'有效数据行数不足 (当前 {len(combined)} 行，需要至少 10 行)。'}

    y = combined['__target__']
    X = combined.drop(columns=['__target__'])

    feature_names = X.columns.tolist()

    # Split
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
    except ValueError as e:
        return {'error': f'数据划分失败: {str(e)}'}

    if len(X_train) < 2:
        return {'error': '训练集样本不足。请减少特征列或调整测试集比例。'}

    # Standardize
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Fit model
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)

    # Predict
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)

    # Metrics
    train_r2 = round(float(r2_score(y_train, y_pred_train)), 4)
    test_r2 = round(float(r2_score(y_test, y_pred_test)), 4)
    test_mse = round(float(mean_squared_error(y_test, y_pred_test)), 4)
    test_mae = round(float(mean_absolute_error(y_test, y_pred_test)), 4)

    # Coefficients
    coefficients = {}
    for name, coef in zip(feature_names, model.coef_):
        coefficients[str(name)] = round(float(coef), 6)

    return {
        'coefficients': coefficients,
        'intercept': round(float(model.intercept_), 6),
        'r2_score': test_r2,
        'train_r2': train_r2,
        'mse': test_mse,
        'mae': test_mae,
        'train_size': len(X_train),
        'test_size': len(X_test),
        'predictions': [round(float(p), 4) for p in y_pred_test],
        'actuals': [round(float(a), 4) for a in y_test.values],
        'feature_names': [str(f) for f in feature_names],
        'y_column': y_column
    }
