"""
Monthly sales performance analysis for the UK online gift shop.

Input : data/sales_clean.csv  (output of the online-retail-cleaning project)
Output: reports/metrics.json  every number used in the report
        reports/*.png         charts

Period analysed: Dec 2010 - Nov 2011 (12 full months).
Dec 2011 is left out because the data stops on 9 Dec 2011.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATA = Path("data/sales_clean.csv")
REPORTS = Path("reports")
INK, MUTED, ACCENT, ACCENT_LIGHT, WARN, GRID = (
    "#16201d", "#5d6965", "#1f6b58", "#9cc9b8", "#b5651d", "#e3e7e5")

# Seasonal products are found by name; this catches the main Christmas lines.
XMAS_WORDS = "CHRISTMAS|XMAS|ADVENT|SANTA|REINDEER|SNOW"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlelocation": "left", "axes.titlesize": 11.5, "axes.titlecolor": INK,
    "figure.dpi": 200,
})


def load() -> pd.DataFrame:
    s = pd.read_csv(DATA, parse_dates=["InvoiceDate"], dtype={"CustomerID": str, "StockCode": str})
    s = s[s["InvoiceDate"] < "2011-12-01"].copy()
    s["Month"] = s["InvoiceDate"].dt.to_period("M")
    return s


def monthly_table(s: pd.DataFrame) -> pd.DataFrame:
    m = s.groupby("Month").agg(revenue=("Revenue", "sum"), orders=("InvoiceNo", "nunique"))
    m["avg_order"] = m["revenue"] / m["orders"]
    xmas = s["Description"].str.contains(XMAS_WORDS, na=False)
    m["xmas_share"] = s[xmas].groupby("Month")["Revenue"].sum() / m["revenue"]
    return m


def customer_split(s: pd.DataFrame) -> pd.DataFrame:
    """Revenue per month from first-time vs returning customers (rows with a CustomerID only)."""
    k = s[s["HasCustomerID"]]
    first = k.groupby("CustomerID")["Month"].min()
    is_new = k["Month"] == k["CustomerID"].map(first)
    return k.groupby(["Month", is_new])["Revenue"].sum().unstack().rename(
        columns={True: "new", False: "returning"}).fillna(0)


def product_table(s: pd.DataFrame) -> pd.DataFrame:
    # Group by stock code; a few codes have several spellings, so use the most common name.
    name = s.groupby("StockCode")["Description"].agg(lambda d: d.value_counts().index[0])
    p = s.groupby("StockCode").agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"))
    p["name"] = name
    return p.sort_values("revenue", ascending=False)


def chart_monthly(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 2.7))
    labels = [p.strftime("%b\n%y") if p.month in (12, 1) else p.strftime("%b") for p in m.index]
    peak = [str(p) in ("2011-09", "2011-10", "2011-11") for p in m.index]
    bars = ax.bar(range(len(m)), m["revenue"] / 1000, color=[ACCENT if x else ACCENT_LIGHT for x in peak], width=0.7)
    for b, v in zip(bars, m["revenue"] / 1000):
        ax.text(b.get_x() + b.get_width() / 2, v + 18, f"{v:,.0f}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(m)), labels)
    ax.set_ylabel("£ thousand")
    ax.set_ylim(0, m["revenue"].max() / 1000 * 1.15)
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    ax.set_title("Monthly revenue: September to November is the peak season")
    fig.tight_layout()
    fig.savefig(REPORTS / "monthly_revenue.png")
    plt.close(fig)


def chart_customers(c: pd.DataFrame) -> None:
    c = c.iloc[1:]  # Dec 2010 is the first month of data, so every customer looks new
    fig, ax = plt.subplots(figsize=(3.7, 2.6))
    x = range(len(c))
    ax.bar(x, c["returning"] / 1000, color=ACCENT, width=0.7, label="Returning customers")
    ax.bar(x, c["new"] / 1000, bottom=c["returning"] / 1000, color=WARN, width=0.7, label="First-time customers")
    ax.set_xticks(list(x), [p.strftime("%b")[0] for p in c.index])
    ax.set_ylabel("£ thousand")
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Revenue by customer type, Jan–Nov 2011", fontsize=10)
    fig.tight_layout()
    fig.savefig(REPORTS / "customers_new_vs_returning.png")
    plt.close(fig)


def chart_products(p: pd.DataFrame) -> None:
    top = p.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(3.7, 2.6))
    ax.barh(range(len(top)), top["revenue"] / 1000, color=ACCENT, height=0.65)
    names = [n.title() if len(n) <= 24 else n.title()[:23] + "…" for n in top["name"]]
    ax.set_yticks(range(len(top)), names, fontsize=7.5)
    for i, v in enumerate(top["revenue"] / 1000):
        ax.text(v + 2, i, f"£{v:,.0f}k", va="center", fontsize=7.5, color=INK)
    ax.set_xlim(0, top["revenue"].max() / 1000 * 1.3)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("£ thousand")
    ax.set_title("Top 8 products by revenue", fontsize=10)
    fig.tight_layout()
    fig.savefig(REPORTS / "top_products.png")
    plt.close(fig)


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    s = load()
    m = monthly_table(s)
    c = customer_split(s)
    p = product_table(s)

    k = s[s["HasCustomerID"]]
    cust_rev = k.groupby("CustomerID")["Revenue"].sum().sort_values(ascending=False)
    orders_per_cust = k.groupby("CustomerID")["InvoiceNo"].nunique()
    n_top10 = int(len(cust_rev) * 0.10)
    n_top20_products = int(len(p) * 0.20)
    first_month = k.groupby("CustomerID")["Month"].min()
    dec_cohort = set(first_month[first_month == pd.Period("2010-12", "M")].index)
    active_nov = set(k.loc[k["Month"] == pd.Period("2011-11", "M"), "CustomerID"])
    peak = m.loc["2011-09":"2011-11"]
    c_after_dec = c.iloc[1:]

    metrics = {
        "period": "Dec 2010 - Nov 2011",
        "revenue_total": round(m["revenue"].sum(), 2),
        "orders_total": int(m["orders"].sum()),
        "avg_order_value": round(m["revenue"].sum() / m["orders"].sum(), 2),
        "customers_with_id": int(len(cust_rev)),
        "revenue_share_with_customer_id": round(k["Revenue"].sum() / s["Revenue"].sum(), 4),
        "best_month": str(m["revenue"].idxmax()),
        "best_month_revenue": round(m["revenue"].max(), 2),
        "weakest_month": str(m["revenue"].idxmin()),
        "weakest_month_revenue": round(m["revenue"].min(), 2),
        "best_vs_weakest_ratio": round(m["revenue"].max() / m["revenue"].min(), 2),
        "peak_sep_nov_revenue": round(peak["revenue"].sum(), 2),
        "peak_sep_nov_share": round(peak["revenue"].sum() / m["revenue"].sum(), 4),
        "xmas_share_by_month": {str(k_): round(v, 4) for k_, v in m["xmas_share"].items()},
        "returning_share_jan_nov": round(c_after_dec["returning"].sum() / c_after_dec.sum().sum(), 4),
        "returning_share_nov": round(c.loc["2011-11", "returning"] / c.loc["2011-11"].sum(), 4),
        "top10pct_customers": n_top10,
        "top10pct_customer_share": round(cust_rev.head(n_top10).sum() / cust_rev.sum(), 4),
        "one_time_customer_share": round((orders_per_cust == 1).mean(), 4),
        "dec_cohort_size": len(dec_cohort),
        "dec_cohort_active_nov": len(dec_cohort & active_nov),
        "products_total": int(len(p)),
        "top20pct_products": n_top20_products,
        "top20pct_product_share": round(p["revenue"].head(n_top20_products).sum() / p["revenue"].sum(), 4),
        "uk_share": round(s.loc[s["Country"] == "United Kingdom", "Revenue"].sum() / s["Revenue"].sum(), 4),
        "monthly": {str(i): {"revenue": round(r.revenue, 2), "orders": int(r.orders),
                             "avg_order": round(r.avg_order, 2)} for i, r in m.iterrows()},
        "top_products": [{"stock_code": i, "name": r["name"], "revenue": round(r.revenue, 2)}
                         for i, r in p.head(10).iterrows()],
    }
    (REPORTS / "metrics.json").write_text(json.dumps(metrics, indent=2))

    chart_monthly(m)
    chart_customers(c)
    chart_products(p)

    for key in ("revenue_total", "orders_total", "avg_order_value", "best_month", "best_vs_weakest_ratio",
                "peak_sep_nov_share", "returning_share_jan_nov", "returning_share_nov",
                "top10pct_customers", "top10pct_customer_share", "one_time_customer_share",
                "dec_cohort_size", "dec_cohort_active_nov", "products_total", "top20pct_products",
                "top20pct_product_share", "uk_share"):
        print(f"{key:28s} {metrics[key]}")
    print("xmas share Jul-Nov:", {k_: v for k_, v in metrics["xmas_share_by_month"].items() if k_ >= "2011-07"})


if __name__ == "__main__":
    main()
