"""
Predictive Analytics Using Historical Data
------------------------------------------
- Loads a CSV (columns: date, value) or generates a synthetic monthly sales dataset
- Cleans and preprocesses data (dates, duplicates, missing values, outliers)
- Builds features (lags, rolling stats, calendar) for regression models
- Trains Linear Regression, Random Forest, Gradient Boosting + Holt-Winters (time-series)
- Evaluates with MAE, RMSE, MAPE, R2 on a chronological test split
- Visualizes predictions and forecasts future periods

Usage:
    python predictive_analytics.py                       # uses synthetic data
    python predictive_analytics.py --csv data.csv --date-col Date --value-col Sales --horizon 12

Install:
    pip install pandas numpy scikit-learn matplotlib statsmodels
"""

import argparse
import warnings

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")

LAGS = [1, 2, 3, 6, 12]
ROLL_WINDOWS = [3, 6, 12]


# ----------------------------------------------------------------------------
# 1. Load data
# ----------------------------------------------------------------------------
def generate_synthetic_data(n_months=120, seed=42):
    """Monthly data with trend + yearly seasonality + noise, plus some dirt."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-01", periods=n_months, freq="MS")
    t = np.arange(n_months)
    values = 200 + 3.5 * t + 40 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 12, n_months)
    df = pd.DataFrame({"date": dates, "value": values})

    # inject missing values and outliers to show cleaning
    df.loc[rng.choice(n_months, 4, replace=False), "value"] = np.nan
    df.loc[rng.choice(n_months, 2, replace=False), "value"] *= 3
    return df


def load_data(csv_path, date_col, value_col):
    if csv_path is None:
        print("No CSV supplied -> using synthetic dataset.")
        return generate_synthetic_data()
    df = pd.read_csv(csv_path)
    return df.rename(columns={date_col: "date", value_col: "value"})[["date", "value"]]


# ----------------------------------------------------------------------------
# 2. Clean & preprocess
# ----------------------------------------------------------------------------
def clean_data(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates(subset="date")
    df = df.sort_values("date").set_index("date")

    # enforce a regular frequency
    freq = pd.infer_freq(df.index) or "MS"
    df = df.asfreq(freq)

    # outliers: clip using IQR on rolling-median residuals (robust to trend)
    resid = df["value"] - df["value"].rolling(7, center=True, min_periods=1).median()
    q1, q3 = resid.quantile([0.25, 0.75])
    iqr = q3 - q1
    outliers = (resid < q1 - 3 * iqr) | (resid > q3 + 3 * iqr)
    print(f"Missing values: {int(df['value'].isna().sum())} | Outliers flagged: {int(outliers.sum())}")
    df.loc[outliers, "value"] = np.nan

    # fill gaps by time interpolation
    df["value"] = df["value"].interpolate(method="time").bfill().ffill()
    return df, freq


# ----------------------------------------------------------------------------
# 3. Feature engineering
# ----------------------------------------------------------------------------
def calendar_features(index):
    f = pd.DataFrame(index=index)
    f["month"] = index.month
    f["quarter"] = index.quarter
    f["month_sin"] = np.sin(2 * np.pi * index.month / 12)
    f["month_cos"] = np.cos(2 * np.pi * index.month / 12)
    return f


def build_features(series):
    """series: pd.Series with DatetimeIndex. Returns feature DataFrame (NaNs at start)."""
    f = calendar_features(series.index)
    f["trend"] = np.arange(len(series))
    for lag in LAGS:
        f[f"lag_{lag}"] = series.shift(lag)
    for w in ROLL_WINDOWS:
        f[f"roll_mean_{w}"] = series.shift(1).rolling(w).mean()
        f[f"roll_std_{w}"] = series.shift(1).rolling(w).std()
    return f


# ----------------------------------------------------------------------------
# 4. Metrics
# ----------------------------------------------------------------------------
def evaluate(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAPE%": np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
        "R2": r2_score(y_true, y_pred),
    }


# ----------------------------------------------------------------------------
# 5. Recursive future forecasting for regression models
# ----------------------------------------------------------------------------
def forecast_future(model, series, horizon, freq):
    history = series.copy()
    future_idx = pd.date_range(history.index[-1], periods=horizon + 1, freq=freq)[1:]
    preds = []
    for date in future_idx:
        extended = pd.concat([history, pd.Series([np.nan], index=[date])])
        feats = build_features(extended).iloc[[-1]]
        yhat = model.predict(feats)[0]
        preds.append(yhat)
        history = pd.concat([history, pd.Series([yhat], index=[date])])
    return pd.Series(preds, index=future_idx)


# ----------------------------------------------------------------------------
# 6. Main pipeline
# ----------------------------------------------------------------------------
def main(args):
    raw = load_data(args.csv, args.date_col, args.value_col)
    df, freq = clean_data(raw)
    series = df["value"]
    print(f"Data: {len(series)} points, {series.index[0].date()} -> {series.index[-1].date()}, freq={freq}")

    # Chronological split (never shuffle time series!)
    feats = build_features(series)
    data = feats.assign(y=series).dropna()
    split = int(len(data) * (1 - args.test_size))
    X_train, y_train = data.drop(columns="y").iloc[:split], data["y"].iloc[:split]
    X_test, y_test = data.drop(columns="y").iloc[split:], data["y"].iloc[split:]

    models = {
        "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
        "Random Forest": RandomForestRegressor(n_estimators=300, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(random_state=42),
    }

    results, test_preds = {}, {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = pd.Series(model.predict(X_test), index=X_test.index)
        test_preds[name] = pred
        results[name] = evaluate(y_test, pred)

    # Time-series model: Holt-Winters (trend + seasonality)
    train_series = series.loc[:X_train.index[-1]]
    seasonal_periods = 12 if freq.startswith("M") else (7 if freq.startswith("D") else None)
    hw = ExponentialSmoothing(
        train_series,
        trend="add",
        seasonal="add" if seasonal_periods else None,
        seasonal_periods=seasonal_periods,
    ).fit()
    hw_pred = pd.Series(hw.forecast(len(y_test)).values, index=y_test.index)
    test_preds["Holt-Winters"] = hw_pred
    results["Holt-Winters"] = evaluate(y_test, hw_pred)

    # Compare
    res_df = pd.DataFrame(results).T.sort_values("RMSE")
    print("\nModel comparison (test set):")
    print(res_df.round(3).to_string())
    best = res_df.index[0]
    print(f"\nBest model: {best}")

    # Refit best model on ALL data and forecast the future
    if best == "Holt-Winters":
        final = ExponentialSmoothing(
            series, trend="add",
            seasonal="add" if seasonal_periods else None,
            seasonal_periods=seasonal_periods,
        ).fit()
        future = pd.Series(
            final.forecast(args.horizon).values,
            index=pd.date_range(series.index[-1], periods=args.horizon + 1, freq=freq)[1:],
        )
    else:
        final = models[best]
        final.fit(data.drop(columns="y"), data["y"])
        future = forecast_future(final, series, args.horizon, freq)

    print(f"\nForecast for next {args.horizon} periods:")
    print(future.round(2).to_string())

    # ---- Visualizations (original 3-panel layout, cleaned up) ----
    colors = {"Linear Regression": "#1f77b4", "Random Forest": "#ff7f0e",
              "Gradient Boosting": "#2ca02c", "Holt-Winters": "#d62728"}
    fig, axes = plt.subplots(3, 1, figsize=(13, 13), constrained_layout=True)
    fig.set_constrained_layout_pads(h_pad=0.15, hspace=0.08)

    def style(ax, title, ylabel="Value"):
        ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)

    # (a) full history + test predictions
    axes[0].plot(series.index, series, color="black", lw=1.8, label="Actual")
    axes[0].axvspan(X_test.index[0], X_test.index[-1], color="gray", alpha=0.10, label="Test period")
    for name, pred in test_preds.items():
        axes[0].plot(pred.index, pred, "--", lw=1.6, color=colors[name], label=name)
    axes[0].axvline(X_test.index[0], color="gray", ls=":", lw=1.2)
    axes[0].legend(loc="upper left", fontsize=9, ncol=2, framealpha=0.9)
    style(axes[0], "Actual vs Predicted (test period)")

    # (b) full history + future forecast
    axes[1].plot(series.index, series, color="black", lw=1.8, label="History")
    axes[1].plot(future.index, future, color="#d62728", lw=2.2, marker="o", ms=5,
                 label=f"Forecast ({best})")
    axes[1].axvspan(future.index[0], future.index[-1], color="#d62728", alpha=0.08)
    axes[1].legend(loc="upper left", fontsize=9, framealpha=0.9)
    style(axes[1], f"Forecast: next {args.horizon} periods")

    # (c) error comparison with value labels
    rmse = res_df["RMSE"]
    bars = axes[2].bar(rmse.index, rmse.values, color=[colors[m] for m in rmse.index], width=0.55)
    axes[2].bar_label(bars, fmt="%.1f", padding=3, fontsize=10, fontweight="bold")
    axes[2].set_ylim(0, rmse.max() * 1.15)
    axes[2].grid(axis="y", alpha=0.25)
    axes[2].set_axisbelow(True)
    style(axes[2], "RMSE by model (lower is better)", ylabel="RMSE")
    axes[2].grid(axis="x", visible=False)

    plt.savefig(args.output, dpi=150)
    print(f"\nPlot saved to {args.output}")
    if matplotlib.get_backend().lower() != "agg":
        plt.show()

    # Feature importance (tree models)
    if best in ("Random Forest", "Gradient Boosting"):
        imp = pd.Series(final.feature_importances_, index=X_train.columns).sort_values(ascending=False)
        print("\nTop features:")
        print(imp.head(8).round(3).to_string())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Predictive analytics on historical data")
    p.add_argument("--csv", default=None, help="Path to CSV file (optional)")
    p.add_argument("--date-col", default="date")
    p.add_argument("--value-col", default="value")
    p.add_argument("--horizon", type=int, default=12, help="Periods to forecast")
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--output", default="forecast_results.png")
    main(p.parse_args())