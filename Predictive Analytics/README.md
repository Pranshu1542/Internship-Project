# Predictive Analytics Using Historical Data

A Python project that builds predictive models to forecast future trends from historical time-series data. It covers the full workflow: data cleaning, feature engineering, model training, evaluation, visualization and forecasting.

## Features

- **Data cleaning and preprocessing**
  - Date parsing, duplicate removal and a regular time frequency
  - Outlier detection (IQR on rolling-median residuals)
  - Missing-value handling via time interpolation
- **Feature engineering**
  - Lag features (1, 2, 3, 6, 12)
  - Rolling mean and standard deviation (3, 6, 12)
  - Trend index and calendar features (month, quarter, sin/cos encoding)
- **Models**
  - Linear Regression
  - Random Forest Regressor
  - Gradient Boosting Regressor
  - Holt-Winters Exponential Smoothing (time-series model)
- **Evaluation** on a chronological train/test split (no shuffling) using MAE, RMSE, MAPE and R²
- **Visualization**
  - Actual vs predicted values on the test period
  - Future forecast
  - RMSE comparison across models
- **Forecasting:** the best model (lowest RMSE) is refit on all data and predicts the next N periods

## Project Structure

```
.
├── predictive_analytics.py   # Main script
├── forecast_results.png      # Output plot (generated)
└── README.md
```

## Requirements

- Python 3.9+
- pandas
- numpy
- scikit-learn
- matplotlib
- statsmodels

Install dependencies:

```bash
pip install pandas numpy scikit-learn matplotlib statsmodels
```

## Usage

**Run with the built-in synthetic dataset** (monthly data with trend, seasonality, noise, missing values and outliers):

```bash
python predictive_analytics.py
```

**Run with your own CSV file:**

```bash
python predictive_analytics.py --csv sales.csv --date-col Date --value-col Sales --horizon 12
```

### Command-line Arguments

| Argument       | Default                | Description                                  |
|----------------|------------------------|----------------------------------------------|
| `--csv`        | None (synthetic data)  | Path to your CSV file                        |
| `--date-col`   | `date`                 | Name of the date column                      |
| `--value-col`  | `value`                | Name of the column to forecast               |
| `--horizon`    | `12`                   | Number of future periods to forecast         |
| `--test-size`  | `0.2`                  | Fraction of data held out for testing        |
| `--output`     | `forecast_results.png` | File name for the saved plot                 |

### Input Data Format

Your CSV needs one date column and one numeric column:

```csv
Date,Sales
2015-01-01,203.4
2015-02-01,211.9
2015-03-01,250.2
```

## Sample Results (synthetic data)

| Model              | MAE    | RMSE   | MAPE % | R²     |
|--------------------|--------|--------|--------|--------|
| Holt-Winters       | 7.74   | 10.31  | 1.34   | 0.883  |
| Linear Regression  | 8.99   | 10.61  | 1.54   | 0.876  |
| Gradient Boosting  | 36.80  | 43.38  | 6.19   | -1.066 |
| Random Forest      | 40.34  | 47.42  | 6.78   | -1.469 |

Holt-Winters and Linear Regression capture the upward trend and seasonality well. Random Forest and Gradient Boosting score poorly because tree-based models cannot extrapolate beyond the range of values seen in training, which matters when the data has a strong trend.

## Output

Running the script prints the model comparison table and the forecast values, and saves a three-panel plot (`forecast_results.png`):

1. Actual vs predicted values on the test period
2. Future forecast appended to the full history
3. RMSE by model

## Notes

- If your data is not monthly, adjust `LAGS`, `ROLL_WINDOWS` and the seasonal period at the top of the script (the seasonal period is set from the detected data frequency).
- The train/test split is chronological. Shuffling would leak future information into training.
- Regression-model forecasts are produced recursively: each predicted value is fed back in as a lag feature for the next step, so errors can accumulate over long horizons.

## Learning Outcomes

- Predictive modeling with regression and time-series methods
- Trend and seasonality analysis
- Data-driven forecasting and model evaluation
