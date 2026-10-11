"""Build the one-page PDF report from reports/metrics.json and the charts. Run after analyze.py."""
import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

REPORTS = Path("reports")
OUT = REPORTS / "sales_report_2011.pdf"
INK, MUTED, ACCENT, LINE, SOFT = (HexColor(c) for c in ("#16201d", "#5d6965", "#1f6b58", "#dde2df", "#eef4f1"))

pdfmetrics.registerFont(TTFont("Sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

m = json.loads((REPORTS / "metrics.json").read_text())
pct = lambda x: f"{x * 100:.0f}%"


def wrap(c, text, x, y, width, font="Sans", size=8.6, leading=11.6, color=INK):
    """Draw text wrapped to width; supports **bold** segments. Returns the y below the last line."""
    words = []
    for i, part in enumerate(text.split("**")):
        words += [(w, "Sans-Bold" if i % 2 else font) for w in part.split()]
    line, lines = [], []
    for w in words:
        trial = line + [w]
        if sum(pdfmetrics.stringWidth(t + " ", f, size) for t, f in trial) > width and line:
            lines.append(line)
            line = [w]
        else:
            line = trial
    lines.append(line)
    for ln in lines:
        cx = x
        for t, f in ln:
            c.setFont(f, size)
            c.setFillColor(color)
            c.drawString(cx, y, t)
            cx += pdfmetrics.stringWidth(t + " ", f, size)
        y -= leading
    return y


W, H = A4
L, R = 16 * mm, W - 16 * mm
c = canvas.Canvas(str(OUT), pagesize=A4)
c.setTitle("Sales Performance Report, Dec 2010 - Nov 2011")
c.setAuthor("Aldo Fransisco")

# Header
y = H - 18 * mm
c.setFont("Sans", 7.5)
c.setFillColor(MUTED)
c.drawString(L, y, "UK ONLINE GIFT SHOP  ·  SALES PERFORMANCE REPORT")
c.drawRightString(R, y, "Prepared by Aldo Fransisco")
y -= 9 * mm
HEADLINE = "Sales peak in autumn, and repeat buyers carry the year"
size = 17
while pdfmetrics.stringWidth(HEADLINE, "Sans-Bold", size) > R - L:
    size -= 0.5
c.setFont("Sans-Bold", size)
c.setFillColor(INK)
c.drawString(L, y, HEADLINE)
y -= 5.5 * mm
c.setFont("Sans", 9)
c.setFillColor(MUTED)
c.drawString(L, y, f"12 months, {m['period']}  ·  product sales only, after data cleaning  ·  amounts in GBP")

# KPI row
y -= 11 * mm
kpis = [
    (f"£{m['revenue_total'] / 1e6:.2f}M", "revenue"),
    (f"{m['orders_total']:,}", "orders"),
    (f"£{m['avg_order_value']:.0f}", "average order"),
    (f"{m['customers_with_id']:,}", "known customers"),
]
col = (R - L) / 4
for i, (big, small) in enumerate(kpis):
    x = L + i * col
    c.setFont("Sans-Bold", 15)
    c.setFillColor(ACCENT)
    c.drawString(x, y, big)
    c.setFont("Sans", 8)
    c.setFillColor(MUTED)
    c.drawString(x, y - 4.5 * mm, small)
y -= 9 * mm
c.setStrokeColor(LINE)
c.line(L, y, R, y)

# Charts
img_w = R - L
img_h = img_w * 2.7 / 7.6
y -= img_h + 2 * mm
c.drawImage(str(REPORTS / "monthly_revenue.png"), L, y, img_w, img_h)
half = (img_w - 4 * mm) / 2
half_h = half * 2.6 / 3.7
y -= half_h + 1 * mm
c.drawImage(str(REPORTS / "customers_new_vs_returning.png"), L, y, half, half_h)
c.drawImage(str(REPORTS / "top_products.png"), L + half + 4 * mm, y, half, half_h)

# Findings and actions
x_nov = m["xmas_share_by_month"]["2011-11"]
x_jul = m["xmas_share_by_month"]["2011-07"]
items = [
    ("Plan for the autumn peak",
     f"September to November brought in **{pct(m['peak_sep_nov_share'])}** of the year's revenue in three months. "
     f"November alone (£{m['best_month_revenue'] / 1e6:.2f}M) was **{m['best_vs_weakest_ratio']:.1f}×** February. "
     f"Christmas products grew from {x_jul * 100:.1f}% of sales in July to {pct(x_nov)} in November.",
     "Order Christmas stock and plan warehouse staff by July, and launch seasonal lines in August "
     "so they are in stock before the September jump."),
    ("Look after the best customers",
     f"Returning customers produced **{pct(m['returning_share_jan_nov'])}** of known-customer revenue from January to November. "
     f"The top {m['top10pct_customers']} customers (10%) account for **{pct(m['top10pct_customer_share'])}** "
     f"of known-customer revenue, while {pct(m['one_time_customer_share'])} of customers ordered only once.",
     f"Give the top {m['top10pct_customers']} accounts early access to the autumn range and a named contact. "
     "Send one-time buyers a reorder reminder 30 days after their first order."),
    ("Focus the range",
     f"The best-selling 20% of products ({m['top20pct_products']} of {m['products_total']:,}) "
     f"earn **{pct(m['top20pct_product_share'])}** of revenue. "
     f"The UK accounts for {pct(m['uk_share'])} of sales.",
     f"Never let the top {m['top20pct_products']} products run out. Review the slowest sellers each quarter and "
     "clear or drop the ones that tie up stock without adding sales."),
]
y -= 6 * mm
c.setFont("Sans-Bold", 10.5)
c.setFillColor(INK)
c.drawString(L, y, "What the data says, and what to do")
y -= 6 * mm
for title, finding, action in items:
    c.setFont("Sans-Bold", 9.2)
    c.setFillColor(ACCENT)
    c.drawString(L, y, title)
    y = wrap(c, finding, L, y - 4.6 * mm, R - L)
    box_top = y + 2.6 * mm
    y2 = wrap(c, "**Action:** " + action, L + 3 * mm, y - 1.4 * mm, R - L - 6 * mm)
    c.setFillColor(SOFT)
    c.rect(L, y2 + 1.2 * mm, R - L, box_top - (y2 + 1.2 * mm) - 0.6 * mm, stroke=0, fill=1)
    wrap(c, "**Action:** " + action, L + 3 * mm, y - 1.4 * mm, R - L - 6 * mm)
    y = y2 - 3.5 * mm

# Footer
c.setStrokeColor(LINE)
c.line(L, 14 * mm, R, 14 * mm)
c.setFont("Sans", 7)
c.setFillColor(MUTED)
c.drawString(L, 10 * mm, "Data: UCI Online Retail dataset (Chen, 2015), CC BY 4.0. Dec 2011 excluded (only 9 days of data).")
c.drawString(L, 6.8 * mm, f"Customer figures use the {pct(m['revenue_share_with_customer_id'])} of revenue that has a customer ID; "
                          "guest-checkout sales have none.")
c.save()
print("wrote", OUT, "lowest y", round(y / mm, 1), "mm")
