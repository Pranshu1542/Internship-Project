# Data Cleaning & Reporting Automation

A Python project that automates the cleaning of raw data and generates a ready-to-share summary report, removing repetitive manual work in Excel.

> Built as part of my Thiranex internship (Internship-Project repository).

## Overview

Raw datasets are often messy: missing values, duplicates, inconsistent formats and wrong data types. This project loads a raw dataset, cleans it with a repeatable pipeline, and produces a report with key statistics in one run.

## Features

- Loads raw data from `<CSV / Excel>` files
- Removes duplicate records
- Handles missing values (`<fill / drop strategy>`)
- Standardizes column names, text case and date formats
- Fixes data types
- Generates a summary report (`<Excel / CSV / PDF / text>`)
- Saves the cleaned dataset separately from the raw data

## Tech Stack

- Python 3
- `<pandas>`
- `<numpy>`
- `<openpyxl / matplotlib / other libraries you used>`

## Project Structure

```
Data Cleaning & Reporting Automation/
├── <main_script>.py        # Main cleaning + reporting script
├── <raw_data_file>         # Input: raw dataset
├── <cleaned_data_file>     # Output: cleaned dataset
├── <report_file>           # Output: generated report
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.8 or higher

### Installation

```bash
git clone https://github.com/Pranshu1542/Internship-Project.git
cd "Internship-Project/Data Cleaning & Reporting Automation"
pip install pandas openpyxl
```

### Usage

```bash
python <main_script>.py
```

The script will read the raw data, clean it, and write the cleaned file and report to the output location.

## How It Works

1. **Load**: reads the raw dataset into a DataFrame.
2. **Clean**: removes duplicates, handles nulls, standardizes formats.
3. **Analyze**: computes summary statistics (`<e.g. totals, averages, counts by category>`).
4. **Report**: exports the cleaned data and a summary report.

## Sample Output

`<Add a screenshot or a few rows of the cleaned data / report here>`

## Future Improvements

- Add a command-line interface for choosing input and output files
- Add charts to the report
- Schedule the script to run automatically
- Add unit tests for the cleaning functions

## Author

**Pranshu**
B.Tech (AI & ML), GGSIPU, Delhi
GitHub: [Pranshu1542](https://github.com/Pranshu1542)
