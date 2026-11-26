import argparse
import base64
import difflib
import logging
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

PLACEHOLDERS = {"", "n/a", "na", "none", "null", "-", "nan", "unknown", "?"}
EMAIL_RE = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

log = logging.getLogger("pipeline")


# =============================================================================
# 1. SAMPLE DATA (deliberately messy)
# =============================================================================
def generate_messy_data(n=600, seed=7):
    rng = np.random.default_rng(seed)
    regions = ["North", "South", "East", "West"]
    cats = {"Electronics": (150, 900), "Clothing": (15, 120), "Home": (30, 300),
            "Sports": (20, 200), "Books": (5, 40)}
    names = ["Aarav Sharma", "Priya Singh", "Rohan Gupta", "Neha Verma", "Karan Mehta",
             "Anjali Jain", "Vikram Rao", "Sneha Iyer", "Rahul Khanna", "Pooja Nair"]

    month_w = np.array([5, 5, 6, 6, 7, 7, 6, 7, 8, 9, 12, 14], dtype=float)
    month = rng.choice(12, n, p=month_w / month_w.sum()) + 1
    day = rng.integers(1, 28, n)
    dates = pd.to_datetime({"year": 2024, "month": month, "day": day})

    cat = rng.choice(list(cats), n, p=[.2, .25, .2, .2, .15])
    price = np.array([round(rng.uniform(*cats[c]), 2) for c in cat], dtype=object)
    qty = rng.integers(1, 10, n).astype(object)
    disc = rng.choice([0, 0.05, 0.1, 0.15, 0.2], n, p=[.4, .2, .2, .1, .1]).astype(object)
    cust = rng.choice(names, n).astype(object)
    email = np.array([f"{c.lower().replace(' ', '.')}{rng.integers(1, 99)}@example.com" for c in cust], dtype=object)
    region = rng.choice(regions, n).astype(object)
    status = rng.choice(["Completed", "Pending", "Cancelled", "Returned"], n, p=[.7, .1, .12, .08]).astype(object)

    def pick(frac):
        return rng.choice(n, int(n * frac), replace=False)

    # mixed date formats
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"]
    date_str = np.array([d.strftime(fmts[rng.integers(0, 3)]) for d in dates], dtype=object)

    # inconsistent text
    for arr in (region, cat.astype(object), status):
        for i in pick(0.25):
            v = str(arr[i])
            arr[i] = [v.lower(), v.upper(), f"  {v} ", v + " "][rng.integers(0, 4)]
    for i in pick(0.04):                                   # spelling mistakes
        cat[i] = {"Electronics": "Electronic", "Clothing": "Clothng", "Sports": "Sprts",
                  "Home": "Hom", "Books": "Bookz"}[str(cat[i]).strip().title()] if str(cat[i]).strip().title() in cats else cat[i]

    # currency strings, percent strings, invalid values, outliers
    for i in pick(0.10):
        price[i] = f"${price[i]:,.2f}"
    for i in pick(0.08):
        disc[i] = f"{int(float(disc[i]) * 100)}%"
    for i in pick(0.03):
        qty[i] = -int(qty[i])
    for i in pick(0.01):
        qty[i] = 999
    for i in pick(0.01):
        if not isinstance(price[i], str):
            price[i] = round(float(price[i]) * 50, 2)
    for i in pick(0.03):
        email[i] = email[i].replace("@", "")

    df = pd.DataFrame({
        "Order ID": [f"ORD-{1000 + i}" for i in range(n)], "Customer Name": cust, "Email": email,
        "Region": region, "Category": cat.astype(object), "Order Date": date_str,
        "Quantity": qty, "Unit Price": price, "Discount": disc, "Status": status,
    }).astype(object)

    # missing values / placeholders
    for col, frac in [("Customer Name", .05), ("Email", .06), ("Region", .04), ("Order Date", .02),
                      ("Quantity", .05), ("Unit Price", .05), ("Discount", .08), ("Category", .02)]:
        for i in pick(frac):
            df.at[i, col] = rng.choice([np.nan, "", "N/A", "na", "-", "None"])

    # duplicates: exact copies + messy copies of the same order
    exact = df.sample(35, random_state=1)
    messy = df.sample(10, random_state=2).copy()
    messy["Customer Name"] = messy["Customer Name"].astype(str).str.upper()
    messy["Region"] = messy["Region"].astype(str).str.lower()
    df = pd.concat([df, exact, messy], ignore_index=True).sample(frac=1, random_state=3).reset_index(drop=True)
    return df


# =============================================================================
# 2. CLEANING
# =============================================================================
def snake(name):
    return "_".join("".join(c.lower() if c.isalnum() else " " for c in str(name)).split())


def missing_counts(df):
    out = {}
    for c in df.columns:
        m = df[c].isna()
        if df[c].dtype == object:
            m |= df[c].astype(str).str.strip().str.lower().isin(PLACEHOLDERS)
        out[c] = int(m.sum())
    return pd.Series(out)


def standardize_categories(s, cutoff=0.8):
    """Title-case, strip, then map rare spellings onto the closest frequent value."""
    s = s.str.title()
    counts = s.value_counts()
    canon = list(counts[counts >= max(3, 0.02 * len(s))].index)

    def fix(v):
        if pd.isna(v) or v in canon:
            return v
        m = difflib.get_close_matches(v, canon, n=1, cutoff=cutoff)
        return m[0] if m else v
    return s.map(fix)


def parse_dates(s):
    try:
        return pd.to_datetime(s, format="mixed", dayfirst=True, errors="coerce")
    except (TypeError, ValueError):                         # older pandas
        return s.apply(lambda x: pd.to_datetime(x, dayfirst=True, errors="coerce"))


def clean_data(raw):
    steps = []

    def record(step, n, detail=""):
        steps.append({"Step": step, "Affected": int(n), "Detail": detail})
        log.info("%-34s %6d  %s", step, n, detail)

    df = raw.copy()
    df.columns = [snake(c) for c in df.columns]
    record("Standardise column names", len(df.columns), "snake_case")

    # -- whitespace + placeholder text -> NaN
    placeholders = 0
    for c in df.select_dtypes(include="object").columns:
        had_value = df[c].notna()
        s = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        bad = s.str.lower().isin(PLACEHOLDERS)
        placeholders += int((bad & had_value).sum())
        df[c] = s.where(~bad, np.nan)
    record("Placeholders -> missing", placeholders, "'N/A', '-', 'none', blank, ...")

    # -- numeric columns
    for c in ("quantity", "unit_price"):
        text = df[c].astype(str)
        formatted = text.str.contains(r"[$,]", regex=True) & df[c].notna()
        df[c] = pd.to_numeric(text.str.replace(r"[$,\s]", "", regex=True), errors="coerce")
        record(f"Convert {c} to number", formatted.sum(), "removed '$' and ',' from text values")
    s = df["discount"].astype(str).str.replace(r"\s", "", regex=True)
    pct = s.str.endswith("%")
    df["discount"] = pd.to_numeric(s.str.rstrip("%"), errors="coerce")
    df.loc[pct, "discount"] /= 100
    record("Normalise discount", int(pct.sum()), "'10%' -> 0.10")

    # -- dates
    before_na = df["order_date"].isna().sum()
    df["order_date"] = parse_dates(df["order_date"])
    record("Parse mixed date formats", df["order_date"].notna().sum(),
           f"{int(df['order_date'].isna().sum() - before_na)} unparseable -> missing")

    # -- text standardisation
    for c in ("region", "category", "status"):
        before = df[c].copy()
        df[c] = standardize_categories(df[c].str.strip())
        changed = int(((before != df[c]) & before.notna()).sum())
        record(f"Standardise {c}", changed, f"{before.nunique()} -> {df[c].nunique()} unique values")
    df["customer_name"] = df["customer_name"].str.title()
    df["email"] = df["email"].str.lower()
    bad_email = df["email"].notna() & ~df["email"].str.match(EMAIL_RE, na=False)
    df.loc[bad_email, "email"] = np.nan
    record("Invalid emails -> missing", bad_email.sum(), "no '@' / bad format")

    # -- duplicates
    n = df.duplicated().sum()
    df = df.drop_duplicates()
    record("Remove duplicate rows", n, "identical after standardising text (incl. case/spacing copies)")
    dup_id = df["order_id"].notna() & df["order_id"].duplicated(keep="first")
    df = df[~dup_id]
    record("Remove repeated order IDs", dup_id.sum(), "kept first occurrence")

    # -- invalid values
    neg_q, neg_p = (df["quantity"] <= 0).sum(), (df["unit_price"] <= 0).sum()
    df.loc[df["quantity"] <= 0, "quantity"] = np.nan
    df.loc[df["unit_price"] <= 0, "unit_price"] = np.nan
    bad_d = ~df["discount"].between(0, 0.9) & df["discount"].notna()
    df.loc[bad_d, "discount"] = np.nan
    record("Invalid values -> missing", neg_q + neg_p + bad_d.sum(), "negative qty/price, discount outside 0-90%")

    # -- missing values
    no_date = df["order_date"].isna()
    df = df[~no_date]
    record("Drop rows without a date", no_date.sum(), "cannot be placed in time")
    text_gaps = int(df[["category", "region", "customer_name", "status"]].isna().sum().sum())
    for c in ("category", "region", "customer_name"):
        df[c] = df[c].fillna("Unknown")
    df["status"] = df["status"].fillna("Pending")
    n_q, n_p, n_d = df["quantity"].isna().sum(), df["unit_price"].isna().sum(), df["discount"].isna().sum()
    df["quantity"] = df["quantity"].fillna(df.groupby("category")["quantity"].transform("median")).fillna(df["quantity"].median())
    df["unit_price"] = df["unit_price"].fillna(df.groupby("category")["unit_price"].transform("median")).fillna(df["unit_price"].median())
    df["discount"] = df["discount"].fillna(0)
    df["quantity"] = df["quantity"].round().astype(int)
    record("Impute quantity", n_q, "median of category")
    record("Impute unit_price", n_p, "median of category")
    record("Impute discount", n_d, "0 (no discount)")
    record("Fill text gaps", text_gaps, "customer/region/category -> 'Unknown', status -> 'Pending'; email left blank")

    # -- outliers (cap, don't delete)
    capped = 0
    for c in ("quantity", "unit_price"):
        q1, q3 = df[c].quantile([.25, .75])
        hi = q3 + 3 * (q3 - q1)
        mask = df[c] > hi
        capped += int(mask.sum())
        df.loc[mask, c] = hi
        if c == "quantity":
            df[c] = df[c].round().astype(int)
    record("Cap outliers", capped, "values above Q3 + 3*IQR set to the limit")

    df["total_amount"] = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    df = df.sort_values("order_date").reset_index(drop=True)
    record("Final dataset", len(df), f"{len(df.columns)} columns")
    return df, pd.DataFrame(steps)


# =============================================================================
# 3. ANALYSIS & REPORTING
# =============================================================================
def build_aggregates(df):
    valid = df[df["status"] != "Cancelled"]
    monthly = valid.groupby("month").agg(Orders=("order_id", "count"), Revenue=("total_amount", "sum")).round(2)
    region = valid.groupby("region").agg(Orders=("order_id", "count"), Revenue=("total_amount", "sum")).round(2).sort_values("Revenue", ascending=False)
    category = valid.groupby("category").agg(Orders=("order_id", "count"), Revenue=("total_amount", "sum")).round(2).sort_values("Revenue", ascending=False)
    kpis = pd.DataFrame({
        "Metric": ["Report generated", "Date range", "Orders (excl. cancelled)", "Total revenue",
                   "Average order value", "Top region", "Top category", "Cancelled / returned orders"],
        "Value": [datetime.now().strftime("%Y-%m-%d %H:%M"),
                  f"{df['order_date'].min():%d %b %Y} to {df['order_date'].max():%d %b %Y}",
                  f"{len(valid):,}", f"{valid['total_amount'].sum():,.2f}",
                  f"{valid['total_amount'].mean():,.2f}", region.index[0], category.index[0],
                  f"{int(df['status'].isin(['Cancelled', 'Returned']).sum()):,}"],
    })
    return monthly, region, category, kpis


def make_dashboard(monthly, region, category, miss_before, miss_after, path):
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    k = FuncFormatter(lambda x, _: f"{x / 1000:,.0f}K")

    ax = axes[0, 0]
    x = pd.to_datetime(monthly.index)
    ax.plot(x, monthly["Revenue"], color=PALETTE[0], lw=2.2, marker="o", ms=5)
    ax.fill_between(x, monthly["Revenue"], color=PALETTE[0], alpha=0.12)
    ax.yaxis.set_major_formatter(k)
    ax.set_title("Monthly revenue", fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel("Revenue")

    ax = axes[0, 1]
    r = region["Revenue"].sort_values()
    bars = ax.barh(r.index, r.values, color=PALETTE[1])
    ax.bar_label(bars, labels=[f"{v / 1000:,.1f}K" for v in r.values], padding=3, fontsize=9)
    ax.set_xlim(0, r.max() * 1.15)
    ax.xaxis.set_major_formatter(k)
    ax.set_title("Revenue by region", fontsize=13, fontweight="bold", pad=10)

    ax = axes[1, 0]
    c = category["Revenue"]
    bars = ax.bar(c.index, c.values, color=PALETTE[2], width=0.6)
    ax.bar_label(bars, labels=[f"{v / 1000:,.1f}K" for v in c.values], padding=3, fontsize=9)
    ax.set_ylim(0, c.max() * 1.15)
    ax.yaxis.set_major_formatter(k)
    ax.set_title("Revenue by category", fontsize=13, fontweight="bold", pad=10)

    ax = axes[1, 1]
    cols = [c for c in miss_before.index if miss_before[c] > 0]
    idx = np.arange(len(cols))
    b1 = ax.bar(idx - 0.2, miss_before[cols], 0.4, color=PALETTE[3], label="Before cleaning")
    b2 = ax.bar(idx + 0.2, miss_after.reindex(cols).fillna(0), 0.4, color=PALETTE[2], label="After cleaning")
    ax.bar_label(b1, fontsize=8, padding=2)
    ax.bar_label(b2, fontsize=8, padding=2)
    ax.set_xticks(idx)
    ax.set_xticklabels(cols, rotation=30, ha="right")
    ax.set_ylim(0, miss_before.max() * 1.18)
    ax.legend(frameon=False)
    ax.set_title("Missing / placeholder values per column", fontsize=13, fontweight="bold", pad=10)

    for a in axes.flat:
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
        a.spines[["top", "right"]].set_visible(False)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def write_excel(path, kpis, quality, steps, monthly, region, category, df, dashboard_png):
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    with pd.ExcelWriter(path, engine="openpyxl", datetime_format="YYYY-MM-DD") as xw:
        kpis.to_excel(xw, sheet_name="Summary", index=False)
        quality.to_excel(xw, sheet_name="Summary", index=False, startrow=len(kpis) + 3)
        steps.to_excel(xw, sheet_name="Cleaning Log", index=False)
        monthly.to_excel(xw, sheet_name="Monthly")
        region.to_excel(xw, sheet_name="By Region")
        category.to_excel(xw, sheet_name="By Category")
        df.to_excel(xw, sheet_name="Cleaned Data", index=False)

        head_fill = PatternFill("solid", fgColor="1F3A5F")
        for ws in xw.book.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = head_fill
                cell.alignment = Alignment(horizontal="center")
            if ws.title != "Summary":
                ws.freeze_panes = "A2"
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col[:200])
                ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(width + 3, 12), 45)
        ws = xw.book["Summary"]
        hdr = len(kpis) + 4
        for cell in ws[hdr]:
            if cell.value is not None:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = head_fill
        img = XLImage(str(dashboard_png))
        img.width, img.height = 900, int(900 * 9 / 14)
        ws.add_image(img, "E2")
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 34


def write_html(path, kpis, quality, steps, dashboard_png):
    b64 = base64.b64encode(Path(dashboard_png).read_bytes()).decode()
    tbl = lambda d, idx=False: d.to_html(index=idx, classes="tbl", border=0)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Sales Data Report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6fa;color:#1c2330}}
.wrap{{max-width:1100px;margin:auto;padding:28px}}
h1{{margin:0 0 4px}} h2{{margin-top:34px;border-bottom:2px solid #1f3a5f;padding-bottom:6px}}
.card{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.tbl{{border-collapse:collapse;width:100%;font-size:14px}}
.tbl th{{background:#1f3a5f;color:#fff;text-align:left;padding:8px 10px}}
.tbl td{{padding:7px 10px;border-bottom:1px solid #e5e9f0}}
img{{width:100%;border-radius:8px}}
</style></head><body><div class="wrap">
<h1>Sales Data Report</h1><div>Automated cleaning &amp; reporting pipeline</div>
<h2>Key metrics</h2><div class="card">{tbl(kpis)}</div>
<h2>Visual summary</h2><div class="card"><img src="data:image/png;base64,{b64}"></div>
<h2>Data quality: before vs after</h2><div class="card">{tbl(quality)}</div>
<h2>Cleaning log</h2><div class="card">{tbl(steps)}</div>
</div></body></html>"""
    Path(path).write_text(html, encoding="utf-8")


# =============================================================================
# 4. PIPELINE
# =============================================================================
def run(args):
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(out / "pipeline.log", mode="w", encoding="utf-8")])

    if args.input:
        raw = pd.read_csv(args.input, dtype=object)
        log.info("Loaded %s: %d rows", args.input, len(raw))
    else:
        raw = generate_messy_data()
        raw.to_csv(out / "raw_messy_data.csv", index=False)
        log.info("No input given -> generated messy sample data (%d rows)", len(raw))

    raw_s = raw.copy()
    raw_s.columns = [snake(c) for c in raw_s.columns]
    miss_before = missing_counts(raw_s)
    dup_before = int(raw_s["order_id"].duplicated().sum())

    log.info("\n--- CLEANING ---")
    df, steps = clean_data(raw)
    miss_after = df.drop(columns=["total_amount", "month"]).isna().sum()

    quality = pd.DataFrame({
        "Check": ["Rows", "Columns", "Missing / placeholder cells", "Duplicate order IDs"],
        "Before": [len(raw), raw.shape[1], int(miss_before.sum()), dup_before],
        "After": [len(df), df.shape[1] - 2, int(miss_after.sum()), int(df["order_id"].duplicated().sum())],
    })

    monthly, region, category, kpis = build_aggregates(df)
    df.to_csv(out / "cleaned_data.csv", index=False)
    make_dashboard(monthly, region, category, miss_before, miss_after, out / "dashboard.png")
    write_excel(out / "sales_report.xlsx", kpis, quality, steps, monthly, region, category, df, out / "dashboard.png")
    write_html(out / "sales_report.html", kpis, quality, steps, out / "dashboard.png")

    log.info("\n--- QUALITY ---\n%s", quality.to_string(index=False))
    log.info("\n--- KPIs ---\n%s", kpis.to_string(index=False))
    log.info("\nSaved to %s/: cleaned_data.csv, sales_report.xlsx, sales_report.html, dashboard.png, pipeline.log", out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Automated data cleaning & reporting")
    p.add_argument("--input", default=None, help="Path to messy CSV (optional)")
    p.add_argument("--outdir", default="output", help="Folder for reports")
    run(p.parse_args())
