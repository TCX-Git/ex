import os
import io
import json
import traceback
from flask import Flask, render_template, request, redirect, url_for, \
    session, flash, jsonify, send_file

from utils.session_manager import (
    _get_session_id, save_uploaded_file, load_dataframe, save_dataframe,
    allowed_file, reset_to_original, cleanup_old_sessions, get_session_info
)
from utils.data_cleaner import (
    get_column_info, get_preview_data, drop_missing, fill_missing,
    drop_duplicates, detect_outliers, handle_outliers, convert_column_type
)
from utils.data_analyzer import (
    basic_statistics, correlation_matrix, kmeans_clustering, linear_regression
)
from utils.data_visualizer import (
    create_histogram, create_scatter, create_bar_chart, create_line_chart,
    create_cluster_scatter, create_regression_scatter
)


def create_app():
    app = Flask(__name__)
    app.config.from_object('config')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- Page Routes ---

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/upload', methods=['POST'])
    def upload():
        if 'file' not in request.files:
            flash('Please select a file.', 'danger')
            return redirect(url_for('index'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('index'))

        if not allowed_file(file.filename):
            flash('Unsupported file type. Please upload CSV or Excel files.', 'danger')
            return redirect(url_for('index'))

        try:
            save_uploaded_file(file)
            flash('File uploaded successfully! Proceed to preview your data.', 'success')
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            return redirect(url_for('index'))

        return redirect(url_for('preview'))

    @app.route('/preview')
    def preview():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            flash('No data available. Please upload a file first.', 'warning')
            return redirect(url_for('index'))

        col_info = get_column_info(df)
        preview_data = get_preview_data(df)
        session_info = get_session_info()

        return render_template('preview.html',
                               column_info=col_info,
                               preview_data=preview_data,
                               session_info=session_info)

    @app.route('/clean')
    def clean_page():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            flash('No data available. Please upload a file first.', 'warning')
            return redirect(url_for('index'))
        return render_template('clean.html')

    @app.route('/analyze')
    def analyze_page():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            flash('No data available. Please upload a file first.', 'warning')
            return redirect(url_for('index'))
        return render_template('analyze.html')

    @app.route('/visualize')
    def visualize_page():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            flash('No data available. Please upload a file first.', 'warning')
            return redirect(url_for('index'))
        return render_template('visualize.html')

    @app.route('/export')
    def export_page():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            flash('No data available. Please upload a file first.', 'warning')
            return redirect(url_for('index'))
        return render_template('export.html')

    # --- API Routes: Cleaning ---

    @app.route('/api/clean/info', methods=['GET'])
    def api_clean_info():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'error': 'No data available'}), 404

        col_info = get_column_info(df)
        preview_data = get_preview_data(df)
        return jsonify({
            'column_info': col_info,
            'preview_data': preview_data,
            'numeric_cols': [c['name'] for c in col_info['columns'] if c['dtype_str'] == 'numeric'],
            'categorical_cols': [c['name'] for c in col_info['columns'] if c['dtype_str'] == 'categorical'],
            'all_cols': [c['name'] for c in col_info['columns']]
        })

    @app.route('/api/clean/apply', methods=['POST'])
    def api_clean_apply():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'success': False, 'error': 'No data available'}), 404

        data = request.get_json()
        operation = data.get('operation')
        params = data.get('params', {})

        try:
            result_metadata = {}
            if operation == 'drop_missing':
                columns = params.get('columns', None)
                how = params.get('how', 'any')
                if columns and len(columns) == 0:
                    columns = None
                df, result_metadata = drop_missing(df, columns=columns, how=how)
            elif operation == 'fill_missing':
                columns = params.get('columns', [])
                method = params.get('method', 'mean')
                fill_value = params.get('fill_value', None)
                df, result_metadata = fill_missing(df, columns=columns, method=method, fill_value=fill_value)
            elif operation == 'drop_duplicates':
                subset = params.get('subset', None)
                if subset and len(subset) == 0:
                    subset = None
                df, result_metadata = drop_duplicates(df, subset=subset)
            elif operation == 'detect_outliers':
                columns = params.get('columns', [])
                method = params.get('method', 'iqr')
                threshold = params.get('threshold', 1.5)
                result_metadata = detect_outliers(df, columns=columns, method=method, threshold=threshold)
                # detection doesn't modify df
                return jsonify({'success': True, 'result_metadata': result_metadata})
            elif operation == 'handle_outliers':
                columns = params.get('columns', [])
                method = params.get('method', 'remove')
                threshold = params.get('threshold', 1.5)
                df, result_metadata = handle_outliers(df, columns=columns, method=method, threshold=threshold)
            elif operation == 'convert_type':
                column = params.get('column')
                new_type = params.get('new_type', 'float')
                df, result_metadata = convert_column_type(df, column=column, new_type=new_type)
            else:
                return jsonify({'success': False, 'error': f'Unknown operation: {operation}'}), 400

            save_dataframe(df)

            col_info = get_column_info(df)
            preview_data = get_preview_data(df)
            return jsonify({
                'success': True,
                'column_info': col_info,
                'preview_data': preview_data,
                'result_metadata': result_metadata
            })
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/clean/reset', methods=['POST'])
    def api_clean_reset():
        try:
            reset_to_original()
            df = load_dataframe(use_cleaned=True)
            col_info = get_column_info(df)
            preview_data = get_preview_data(df)
            return jsonify({
                'success': True,
                'message': 'Data reset to original.',
                'column_info': col_info,
                'preview_data': preview_data
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # --- API Routes: Analysis ---

    @app.route('/api/analyze/statistics')
    def api_statistics():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'error': 'No data available'}), 404

        try:
            stats = basic_statistics(df)
            corr = correlation_matrix(df)
            col_info = get_column_info(df)
            return jsonify({
                'statistics': stats,
                'correlation': corr,
                'numeric_cols': [c['name'] for c in col_info['columns'] if c['dtype_str'] == 'numeric'],
                'categorical_cols': [c['name'] for c in col_info['columns'] if c['dtype_str'] == 'categorical'],
                'all_cols': [c['name'] for c in col_info['columns']]
            })
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analyze/kmeans', methods=['POST'])
    def api_kmeans():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'error': 'No data available'}), 404

        data = request.get_json()
        columns = data.get('columns', [])
        n_clusters = data.get('n_clusters', 3)

        try:
            n_clusters = int(n_clusters)
            result = kmeans_clustering(df, columns=columns, n_clusters=n_clusters)

            if 'error' in result:
                return jsonify(result), 400

            # Generate cluster scatter plot
            pca_data = result.get('data_points', [])
            labels = result.get('labels', [])
            centroids = result.get('centroids_pca', None)
            fig = create_cluster_scatter(pca_data, labels, centroids)

            result['plot'] = fig.to_json()
            return jsonify(result)
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analyze/linear-regression', methods=['POST'])
    def api_linear_regression():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'error': 'No data available'}), 404

        data = request.get_json()
        x_columns = data.get('x_columns', [])
        y_column = data.get('y_column', '')
        test_size = data.get('test_size', 0.2)

        try:
            test_size = float(test_size)
            result = linear_regression(df, x_columns=x_columns, y_column=y_column, test_size=test_size)

            if 'error' in result:
                return jsonify(result), 400

            # Generate regression scatter plot
            actuals = result.get('actuals', [])
            predictions = result.get('predictions', [])
            y_name = result.get('y_column', 'Target')
            fig = create_regression_scatter(actuals, predictions, y_column=y_name)

            result['plot'] = fig.to_json()
            return jsonify(result)
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    # --- API Routes: Visualization ---

    @app.route('/api/visualize/columns')
    def api_visualize_columns():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'error': 'No data available'}), 404

        col_info = get_column_info(df)
        return jsonify({
            'columns': col_info['columns'],
            'numeric_cols': [c['name'] for c in col_info['columns'] if c['dtype_str'] == 'numeric'],
            'categorical_cols': [c['name'] for c in col_info['columns'] if c['dtype_str'] == 'categorical'],
            'all_cols': [c['name'] for c in col_info['columns']]
        })

    @app.route('/api/visualize/chart', methods=['POST'])
    def api_visualize_chart():
        df = load_dataframe(use_cleaned=True)
        if df is None:
            return jsonify({'error': 'No data available'}), 404

        data = request.get_json()
        chart_type = data.get('chart_type', 'histogram')

        try:
            fig = None
            if chart_type == 'histogram':
                column = data.get('column', '')
                bins = int(data.get('bins', 30))
                color = data.get('color', None)
                fig = create_histogram(df, column=column, bins=bins, color=color)
            elif chart_type == 'scatter':
                x_col = data.get('x_col', '')
                y_col = data.get('y_col', '')
                color_col = data.get('color_col', None)
                size_col = data.get('size_col', None)
                trendline = data.get('trendline', False)
                fig = create_scatter(df, x_col=x_col, y_col=y_col,
                                    color_col=color_col, size_col=size_col,
                                    trendline=trendline)
            elif chart_type == 'bar':
                x_col = data.get('x_col', '')
                y_col = data.get('y_col', '')
                agg_func = data.get('agg_func', 'mean')
                top_n = data.get('top_n', None)
                if top_n:
                    top_n = int(top_n)
                fig = create_bar_chart(df, x_col=x_col, y_col=y_col,
                                      agg_func=agg_func, top_n=top_n)
            elif chart_type == 'line':
                x_col = data.get('x_col', '')
                y_cols = data.get('y_cols', [])
                fig = create_line_chart(df, x_col=x_col, y_cols=y_cols)
            else:
                return jsonify({'error': f'Unknown chart type: {chart_type}'}), 400

            if fig is None:
                return jsonify({'error': 'Failed to generate chart'}), 500

            return jsonify({'figure': fig.to_json()})
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    # --- API Routes: Export ---

    @app.route('/api/export/download/<export_type>')
    def api_export_download(export_type):
        df = load_dataframe(use_cleaned=True)
        if df is None:
            flash('No data available.', 'danger')
            return redirect(url_for('index'))

        try:
            buf = io.BytesIO()

            if export_type == 'cleaned_csv':
                df.to_csv(buf, index=False, encoding='utf-8-sig')
                buf.seek(0)
                return send_file(buf, mimetype='text/csv',
                                 as_attachment=True,
                                 download_name='cleaned_data.csv')
            elif export_type == 'cleaned_excel':
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Cleaned Data')
                buf.seek(0)
                return send_file(buf,
                                 mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                 as_attachment=True,
                                 download_name='cleaned_data.xlsx')
            elif export_type == 'stats_csv':
                stats = basic_statistics(df)
                # Build a simplified flat version for export
                rows = []
                for s in stats.get('numeric_stats', []):
                    rows.append(s)
                for s in stats.get('categorical_stats', []):
                    rows.append(s)
                stats_df = pd.DataFrame(rows)
                stats_df.to_csv(buf, index=False, encoding='utf-8-sig')
                buf.seek(0)
                return send_file(buf, mimetype='text/csv',
                                 as_attachment=True,
                                 download_name='statistics.csv')
            elif export_type == 'stats_excel':
                stats = basic_statistics(df)
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    if stats.get('numeric_stats'):
                        pd.DataFrame(stats['numeric_stats']).to_excel(
                            writer, index=False, sheet_name='Numeric Statistics')
                    if stats.get('categorical_stats'):
                        pd.DataFrame(stats['categorical_stats']).to_excel(
                            writer, index=False, sheet_name='Categorical Statistics')
                buf.seek(0)
                return send_file(buf,
                                 mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                 as_attachment=True,
                                 download_name='statistics.xlsx')
            else:
                return jsonify({'error': f'Unknown export type: {export_type}'}), 400
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    # --- Error Handlers ---
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'error': 'File too large. Maximum 100MB.'}), 413

    @app.errorhandler(Exception)
    def handle_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': str(e)}), 500
        return render_template('error.html', error=str(e)), 500

    # Cleanup old sessions on startup
    cleanup_old_sessions()

    return app


if __name__ == '__main__':
    import pandas as pd  # ensure import is available for export routes
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
