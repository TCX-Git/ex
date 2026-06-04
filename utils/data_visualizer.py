import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# Common layout settings
def _base_layout(fig, title='', xlabel='', ylabel=''):
    fig.update_layout(
        template='plotly_white',
        hovermode='closest',
        autosize=True,
        margin=dict(l=40, r=20, t=50, b=40),
        title=title,
        xaxis_title=xlabel,
        yaxis_title=ylabel
    )
    return fig


def create_histogram(df, column, bins=30, color=None):
    """Create a histogram for a single column."""
    if column not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text=f'列 "{column}" 不存在', showarrow=False)
        return fig

    data = df[column].dropna()
    if len(data) == 0:
        fig = go.Figure()
        fig.add_annotation(text=f'列 "{column}" 无有效数据', showarrow=False)
        return fig

    marker_color = color or '#0d6efd'
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data,
        nbinsx=bins,
        marker_color=marker_color,
        marker_line_color='white',
        marker_line_width=0.5,
        name=column,
        hovertemplate='值: %{x}<br>频数: %{y}<extra></extra>'
    ))

    _base_layout(fig, title=f'{column} 分布直方图', xlabel=column, ylabel='频数')
    return fig


def create_scatter(df, x_col, y_col, color_col=None, size_col=None, trendline=False):
    """Create a scatter plot."""
    if x_col not in df.columns or y_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text='请选择有效的 X 和 Y 列', showarrow=False)
        return fig

    plot_df = df[[x_col, y_col]].dropna()

    if color_col and color_col in df.columns:
        plot_df = pd.concat([plot_df, df[color_col]], axis=1).dropna()
    if size_col and size_col in df.columns:
        plot_df = pd.concat([plot_df, df[size_col]], axis=1).dropna()

    if len(plot_df) == 0:
        fig = go.Figure()
        fig.add_annotation(text='无有效数据点', showarrow=False)
        return fig

    if trendline and color_col:
        # With color, use px for trendline support
        fig = px.scatter(
            plot_df, x=x_col, y=y_col,
            color=color_col if color_col else None,
            size=size_col if size_col else None,
            trendline='ols' if trendline else None,
            title=f'{y_col} vs {x_col}'
        )
        _base_layout(fig, title=f'{y_col} vs {x_col}', xlabel=x_col, ylabel=y_col)
        return fig

    fig = go.Figure()
    marker = dict(size=8, opacity=0.7)

    if color_col and color_col in plot_df.columns:
        # Color-code
        for name, group in plot_df.groupby(color_col):
            fig.add_trace(go.Scatter(
                x=group[x_col],
                y=group[y_col],
                mode='markers',
                name=str(name),
                marker=dict(size=8, opacity=0.7),
                hovertemplate=f'{x_col}: %{{x}}<br>{y_col}: %{{y}}<extra>{name}</extra>'
            ))
    else:
        sizes = plot_df[size_col] if size_col and size_col in plot_df.columns else None
        fig.add_trace(go.Scatter(
            x=plot_df[x_col],
            y=plot_df[y_col],
            mode='markers',
            marker=dict(
                size=sizes / sizes.max() * 20 if sizes is not None else 8,
                opacity=0.7,
                sizemode='diameter' if sizes is not None else None
            ),
            hovertemplate=f'{x_col}: %{{x}}<br>{y_col}: %{{y}}<extra></extra>'
        ))

    if trendline and not color_col:
        # Add OLS trendline manually
        from numpy.polynomial.polynomial import polyfit
        x_vals = plot_df[x_col].values
        y_vals = plot_df[y_col].values
        try:
            b, m = polyfit(x_vals, y_vals, 1)
            x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
            y_line = b + m * x_line
            fig.add_trace(go.Scatter(
                x=x_line, y=y_line,
                mode='lines',
                name='趋势线',
                line=dict(color='red', dash='dash')
            ))
        except Exception:
            pass

    _base_layout(fig, title=f'{y_col} vs {x_col}', xlabel=x_col, ylabel=y_col)
    return fig


def create_bar_chart(df, x_col, y_col, agg_func='mean', top_n=None):
    """Create a bar chart with optional aggregation."""
    if x_col not in df.columns or y_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text='请选择有效的列', showarrow=False)
        return fig

    # Aggregate
    grouped = df.groupby(x_col)[y_col].agg(agg_func).dropna().sort_values(ascending=False)
    if top_n:
        grouped = grouped.head(int(top_n))

    if len(grouped) == 0:
        fig = go.Figure()
        fig.add_annotation(text='无有效聚合数据', showarrow=False)
        return fig

    agg_labels = {'mean': '均值', 'sum': '求和', 'count': '计数', 'median': '中位数'}
    agg_label = agg_labels.get(agg_func, agg_func)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grouped.index.astype(str),
        y=grouped.values,
        marker_color='#0d6efd',
        hovertemplate=f'{x_col}: %{{x}}<br>{agg_label} {y_col}: %{{y:,.2f}}<extra></extra>'
    ))

    title = f'{y_col} {agg_label} 按 {x_col} 分组'
    if top_n:
        title += f' (Top {top_n})'

    _base_layout(fig, title=title, xlabel=x_col, ylabel=f'{agg_label} of {y_col}')
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def create_line_chart(df, x_col, y_cols):
    """Create a line chart with optional multiple Y columns."""
    if x_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text='请选择有效的 X 轴列', showarrow=False)
        return fig

    if not y_cols:
        fig = go.Figure()
        fig.add_annotation(text='请至少选择一个 Y 轴列', showarrow=False)
        return fig

    valid_y = [c for c in y_cols if c in df.columns]
    if not valid_y:
        fig = go.Figure()
        fig.add_annotation(text='没有有效的 Y 轴列', showarrow=False)
        return fig

    plot_df = df[[x_col] + valid_y].copy()

    # If x is not numeric, try to convert datetime
    if not pd.api.types.is_numeric_dtype(plot_df[x_col]):
        try:
            plot_df[x_col] = pd.to_datetime(plot_df[x_col])
        except Exception:
            pass

    plot_df = plot_df.sort_values(x_col).dropna(subset=[x_col])

    fig = go.Figure()
    colors = ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#6f42c1', '#fd7e14']

    for i, col in enumerate(valid_y):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=plot_df[x_col],
            y=plot_df[col],
            mode='lines+markers',
            name=col,
            line=dict(color=color, width=2),
            marker=dict(size=5),
            hovertemplate=f'{x_col}: %{{x}}<br>{col}: %{{y}}<extra></extra>'
        ))

    title = ' 与 '.join(valid_y) if len(valid_y) <= 2 else f'{len(valid_y)} 个指标趋势'
    _base_layout(fig, title=title, xlabel=x_col, ylabel='值')
    return fig


def create_cluster_scatter(pca_data, labels, centroids_pca):
    """Create a 2D scatter plot for K-Means clustering results."""
    fig = go.Figure()

    if not pca_data or not labels:
        fig.add_annotation(text='无聚类数据', showarrow=False)
        return fig

    pca_data = np.array(pca_data)
    labels = np.array(labels)

    unique_labels = sorted(set(labels))
    colors = px.colors.qualitative.Set1

    for i, label in enumerate(unique_labels):
        mask = labels == label
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=pca_data[mask, 0],
            y=pca_data[mask, 1],
            mode='markers',
            name=f'聚类 {label}',
            marker=dict(size=6, opacity=0.6, color=color),
            hovertemplate=f'PC1: %{{x}}<br>PC2: %{{y}}<br>聚类: {label}<extra></extra>'
        ))

    # Centroids
    if centroids_pca:
        centroids = np.array(centroids_pca)
        fig.add_trace(go.Scatter(
            x=centroids[:, 0],
            y=centroids[:, 1],
            mode='markers',
            name='质心',
            marker=dict(symbol='x', size=15, color='black', line=dict(width=2)),
            hovertemplate='质心<br>PC1: %{x}<br>PC2: %{y}<extra></extra>'
        ))

    _base_layout(fig, title='K-Means 聚类结果 (PCA 2D)', xlabel='主成分 1', ylabel='主成分 2')
    return fig


def create_regression_scatter(actuals, predictions, y_column='Target'):
    """Create an actual vs predicted scatter plot for regression results."""
    fig = go.Figure()

    if not actuals or not predictions:
        fig.add_annotation(text='无回归数据', showarrow=False)
        return fig

    fig.add_trace(go.Scatter(
        x=actuals,
        y=predictions,
        mode='markers',
        name='预测值',
        marker=dict(size=8, opacity=0.6, color='#0d6efd'),
        hovertemplate='实际: %{x}<br>预测: %{y}<extra></extra>'
    ))

    # Diagonal line (perfect prediction)
    all_vals = actuals + predictions
    min_val = min(all_vals)
    max_val = max(all_vals)
    fig.add_trace(go.Scatter(
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode='lines',
        name='完美预测',
        line=dict(color='red', dash='dash', width=1),
        hovertemplate='y = x<extra></extra>'
    ))

    _base_layout(
        fig,
        title=f'线性回归: 实际值 vs 预测值 ({y_column})',
        xlabel='实际值',
        ylabel='预测值'
    )
    return fig
