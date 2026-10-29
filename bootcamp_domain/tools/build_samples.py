#!/usr/bin/env python3
"""Build the generated parts of the three simplified domain samples (finance, consumer, manufacturing).

    python3 -I bootcamp_domain/tools/build_samples.py           # write the files
    python3 -I bootcamp_domain/tools/build_samples.py --check   # exit 1 if a file is missing or stale

Writes, for every sample folder bootcamp_domain/<sample>/:
    01_data/<table>.csv          small synthetic data set (4 tables, deterministic: same seed -> same rows)
    01_data/manifest.json        row count of every CSV (notebook 01 and job task 02b check against it)
    04_genie/fjallmark_<sample>_analyst.json   the Genie Agent template (serialized space, version 2)

and prints the reference KPIs that the READMEs and the Pages quote. Standard library only.
Everything else in the samples (notebooks, SQL, context pages) is written by hand.
"""
import csv
import hashlib
import io
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # bootcamp_domain/
START, END = date(2025, 1, 1), date(2026, 9, 30)    # data window; END = reporting date (last closed period)
MONTHS = [(y, m) for y in (2025, 2026) for m in range(1, 13) if date(y, m, 1) <= END]
C = "__CATALOG__"                                    # replaced by notebook 04 with the participant's catalog

COMPANIES = [  # code, legal name, country, currency, EUR per 1 unit of local currency, parent
    ("SE01", "Fjällmark Consumer Goods AB", "SWE", "SEK", 0.0870, True),
    ("NO01", "Fjällmark Norge AS", "NOR", "NOK", 0.0850, False),
    ("DK01", "Fjällmark Danmark A/S", "DNK", "DKK", 0.1340, False),
    ("FI01", "Fjällmark Suomi Oy", "FIN", "EUR", 1.0000, False),
    ("DE01", "Fjällmark Deutschland GmbH", "DEU", "EUR", 1.0000, False),
    ("PL01", "Fjällmark Polska Sp. z o.o.", "POL", "PLN", 0.2320, False),
]
RATE = {c[0]: c[4] for c in COMPANIES}
CURRENCY = {c[0]: c[3] for c in COMPANIES}
BRANDS = ["Björkö Pantry", "Kallkälla", "Mjuk Care"]


def month_end(y: int, m: int) -> date:
    return (date(y + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)


def money(x: float) -> str:
    return f"{x:.2f}"


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def csv_text(header: list, rows: list) -> str:
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    for r in rows:
        wr.writerow([fmt(v) for v in r])
    return buf.getvalue()


# =========================================================================================================
# Finance: company_code, gl_account, journal_entry_line, ar_invoice
# =========================================================================================================
def build_finance():
    rng = random.Random(2026_01)
    tables = {}
    tables["company_code"] = (
        ["company_code", "company_name", "country_code", "currency_code", "eur_rate", "is_parent"],
        [(c[0], c[1], c[2], c[3], f"{c[4]:.4f}", c[5]) for c in COMPANIES])

    accounts = [("3010", "Sales revenue DTC webshop", "REVENUE"), ("3020", "Sales revenue B2B trade", "REVENUE"),
                ("3090", "Returns and trade discounts", "REVENUE"), ("4000", "Cost of goods sold at standard", "COGS"),
                ("4100", "Production variances", "COGS"), ("6000", "Marketing", "OPEX"),
                ("6100", "Personnel", "OPEX"), ("6200", "Freight and logistics", "OPEX")]
    tables["gl_account"] = (["gl_account_code", "account_name", "account_group"], accounts)

    size = {"SE01": 1_200_000, "NO01": 500_000, "DK01": 450_000, "FI01": 400_000, "DE01": 900_000, "PL01": 250_000}
    share = {"Björkö Pantry": 0.40, "Kallkälla": 0.35, "Mjuk Care": 0.25}
    cogs_ratio = {"Björkö Pantry": 0.56, "Kallkälla": 0.50, "Mjuk Care": 0.58}
    producer = {"Björkö Pantry": ["SE01"], "Kallkälla": ["SE01", "FI01"], "Mjuk Care": ["PL01"]}
    lines, b2b_net = [], {}   # b2b_net[(company, y, m)] = net B2B revenue in EUR (drives the AR invoices)

    def add(y, m, cc, acct, brand, channel, eur):
        eur = round(eur, 2)
        lines.append([len(lines) + 1, month_end(y, m), y, m, cc, acct, brand, channel, CURRENCY[cc],
                      money(round(eur / RATE[cc], 2)), money(eur)])

    for y, m in MONTHS:
        growth = 1.0 if y == 2025 else 1.06
        for cc, *_ in COMPANIES:
            company_net = 0.0
            for brand in BRANDS:
                season = 1.30 if (brand == "Kallkälla" and m in (6, 7, 8)) else (1.15 if m == 12 else 1.0)
                for channel, ch_share in (("DTC", 0.25), ("B2B", 0.75)) if cc != "PL01" else (("B2B", 1.0),):
                    gross = size[cc] * share[brand] * ch_share * season * growth * rng.uniform(0.95, 1.05)
                    returns = gross * rng.uniform(0.03, 0.05)
                    net = gross - returns
                    add(y, m, cc, "3010" if channel == "DTC" else "3020", brand, channel, gross)
                    add(y, m, cc, "3090", brand, channel, -returns)
                    add(y, m, cc, "4000", brand, channel, net * cogs_ratio[brand] * rng.uniform(0.98, 1.02))
                    company_net += net
                    if channel == "B2B":
                        b2b_net[(cc, y, m)] = b2b_net.get((cc, y, m), 0.0) + net
            for brand, producers in producer.items():
                if cc in producers and not (cc == "FI01" and (y, m) < (2025, 4)):   # Tampere plant from April 2025
                    variance = rng.uniform(-4_000, 8_000)
                    if (cc, brand, y, m) == ("PL01", "Mjuk Care", 2026, 3):
                        variance = 145_000.0    # Poznań line PL-POZ-L2 incident, worn filler nozzles
                    add(y, m, cc, "4100", brand, None, variance)
            for acct, pct in (("6000", 0.08), ("6100", 0.12), ("6200", 0.05)):
                add(y, m, cc, acct, None, None, company_net * pct * rng.uniform(0.95, 1.05))
    tables["journal_entry_line"] = (
        ["journal_entry_line_id", "posting_date", "fiscal_year", "fiscal_period", "company_code", "gl_account_code",
         "brand", "channel", "currency_code", "amount_local", "amount_eur"], lines)

    customers = {
        "SE01": [("NorthCart Retail", "erik.nilsson@northcart.example"), ("Svea Grossist", "maria.berg@sveagrossist.example"),
                 ("Apoteket Norrsken", "lars.holm@norrsken.example")],
        "NO01": [("Fjordhandel", "kari.hansen@fjordhandel.example"), ("Nordlys Dagligvare", "ole.berg@nordlys.example")],
        "DK01": [("Baltic FreshMarket", "mette.jensen@balticfresh.example"), ("Øresund Engros", "jens.larsen@oresund.example")],
        "FI01": [("Kaleva Kauppa", "aino.virtanen@kaleva.example"), ("Lappi Apteekki", "mikko.koski@lappi.example")],
        "DE01": [("Alpina Drogerie", "sabine.huber@alpina.example"), ("Hansa Frischmarkt", "jan.schulz@hansa.example"),
                 ("Polder Supermarkt", "pieter.visser@polder.example")],
        "PL01": [("Wisła Hurt", "anna.nowak@wisla.example"), ("Drogeria Poznańska", "piotr.wojcik@drogeria.example")],
    }
    per_month = {"SE01": 6, "NO01": 3, "DK01": 3, "FI01": 3, "DE01": 5, "PL01": 2}
    invoices = []
    for y, m in MONTHS:
        for cc, *_ in COMPANIES:
            n = per_month[cc]
            weights = [rng.uniform(0.7, 1.3) for _ in range(n)]
            for i in range(n):
                name, email = customers[cc][i % len(customers[cc])]
                eur = round(b2b_net[(cc, y, m)] * weights[i] / sum(weights), 2)
                billed = date(y, m, rng.randint(1, 28))
                due = billed + timedelta(days=45 if cc == "DE01" else 30)
                r = rng.random()
                delay = rng.randint(-5, 5) if r < 0.70 else (rng.randint(6, 30) if r < 0.95 else rng.randint(31, 60))
                paid = due + timedelta(days=delay)
                status = "paid"
                if name == "Alpina Drogerie" and i == 0 and billed >= date(2026, 6, 1):
                    status, paid = "disputed", None
                elif paid > END:
                    status, paid = "open", None
                if billed > END:
                    continue
                local = round(eur / RATE[cc], 2)
                open_local, open_eur = (0.0, 0.0) if status == "paid" else (local, eur)
                invoices.append([len(invoices) + 1, f"{cc}-{y}{m:02d}-{i + 1:03d}", cc, name, email, billed, due, paid,
                                 CURRENCY[cc], money(local), money(eur), money(open_local), money(open_eur), status])
    tables["ar_invoice"] = (
        ["ar_invoice_id", "invoice_number", "company_code", "customer_name", "customer_contact_email", "billing_date",
         "due_date", "payment_date", "currency_code", "total_amount_local", "total_amount_eur",
         "outstanding_amount_local", "outstanding_amount_eur", "invoice_status"], invoices)

    # reference KPIs (what the Pages and benchmarks quote)
    grp = {a[0]: a[2] for a in accounts}
    kpi = {}
    for fy in (2025, 2026):
        rev = sum(float(l[10]) for l in lines if l[2] == fy and grp[l[5]] == "REVENUE" and l[3] <= 9)
        cogs = sum(float(l[10]) for l in lines if l[2] == fy and grp[l[5]] == "COGS" and l[3] <= 9)
        kpi[f"net_revenue_eur Jan-Sep {fy}"] = round(rev)
        kpi[f"gross_margin_pct Jan-Sep {fy}"] = round(100 * (rev - cogs) / rev, 1)
    kpi["net_revenue_eur FY2025"] = round(sum(float(l[10]) for l in lines if l[2] == 2025 and grp[l[5]] == "REVENUE"))
    pl = {}
    for p in (2, 3, 4):
        pl[p] = round(sum(float(l[10]) for l in lines if (l[2], l[3], l[4]) == (2026, p, "PL01") and grp[l[5]] == "COGS"))
    kpi["PL01 COGS Feb/Mar/Apr 2026"] = pl
    q3 = lambda inv: date(2026, 7, 1) <= inv[5] <= END   # noqa: E731
    dso = {}
    for cc, *_ in COMPANIES:
        open_ar = sum(float(i[12]) for i in invoices if i[2] == cc)
        billed = sum(float(i[10]) for i in invoices if i[2] == cc and q3(i))
        dso[cc] = round(open_ar / (billed / 92), 1)
    open_all = sum(float(i[12]) for i in invoices)
    billed_all = sum(float(i[10]) for i in invoices if q3(i))
    dso["group"] = round(open_all / (billed_all / 92), 1)
    kpi["dso_days"] = dso
    kpi["overdue_ar_eur"] = round(sum(float(i[12]) for i in invoices if i[13] != "paid" and i[6] < END))
    return tables, kpi


# =========================================================================================================
# Consumer: product, shopper, dtc_order, dtc_order_line
# =========================================================================================================
def build_consumer():
    rng = random.Random(2026_02)
    tables = {}
    products = [
        ("BP-CRISP", "Björkö Crispbread Original", "Björkö Pantry", "FOOD", 3.20),
        ("BP-GRAN", "Björkö Granola Nordic Berries", "Björkö Pantry", "FOOD", 4.90),
        ("BP-OAT", "Björkö Oat Porridge", "Björkö Pantry", "FOOD", 2.80),
        ("BP-JAM", "Björkö Lingonberry Jam", "Björkö Pantry", "FOOD", 3.60),
        ("KK-LEMON", "Kallkälla Sparkling Lemon 6-pack", "Kallkälla", "BEVERAGE", 7.20),
        ("KK-ELDER", "Kallkälla Sparkling Elderflower 6-pack", "Kallkälla", "BEVERAGE", 7.20),
        ("KK-JUICE", "Kallkälla Apple Juice", "Kallkälla", "BEVERAGE", 2.60),
        ("KK-OAT", "Kallkälla Oat Drink", "Kallkälla", "BEVERAGE", 2.20),
        ("MC-SHAMP", "Mjuk Care Gentle Shampoo", "Mjuk Care", "PERSONAL_CARE", 6.90),
        ("MC-WASH", "Mjuk Care Body Wash", "Mjuk Care", "PERSONAL_CARE", 5.90),
        ("MC-DEO", "Mjuk Care Deodorant", "Mjuk Care", "PERSONAL_CARE", 4.50),
        ("MC-HAND", "Mjuk Care Hand Cream", "Mjuk Care", "PERSONAL_CARE", 5.50),
    ]
    tables["product"] = (["product_id", "product_name", "brand", "category", "unit_price_eur"],
                         [(p[0], p[1], p[2], p[3], money(p[4])) for p in products])

    markets = [("SWE", "SE01", 0.35), ("NOR", "NO01", 0.15), ("DNK", "DK01", 0.15), ("FIN", "FI01", 0.12),
               ("DEU", "DE01", 0.15), ("NLD", "DE01", 0.08)]
    names = {
        "SWE": (["Anna", "Erik", "Maja", "Lars", "Elsa", "Oskar", "Sara", "Johan"], ["Andersson", "Nilsson", "Berg", "Lindqvist", "Holm", "Ek"]),
        "NOR": (["Ingrid", "Ola", "Nora", "Henrik", "Kari"], ["Hansen", "Johansen", "Olsen", "Larsen"]),
        "DNK": (["Mette", "Mads", "Freja", "Jens", "Ida"], ["Jensen", "Nielsen", "Pedersen", "Madsen"]),
        "FIN": (["Aino", "Mikko", "Emilia", "Juha", "Laura"], ["Virtanen", "Korhonen", "Mäkinen", "Koski"]),
        "DEU": (["Sabine", "Lukas", "Lena", "Jonas", "Mia"], ["Müller", "Schmidt", "Becker", "Huber"]),
        "NLD": (["Pieter", "Sanne", "Daan", "Emma"], ["de Jong", "Visser", "Bakker", "Smit"]),
    }
    tiers = [(None, 0.45), ("Bronze", 0.25), ("Silver", 0.15), ("Gold", 0.10), ("Platinum", 0.05)]
    order_rate = {None: 3.0, "Bronze": 5.0, "Silver": 7.0, "Gold": 10.0, "Platinum": 14.0}   # orders per 21 months
    shoppers = []
    for i in range(1200):
        country, cc, _ = rng.choices(markets, weights=[m[2] for m in markets])[0]
        given, family = rng.choice(names[country][0]), rng.choice(names[country][1])
        tier = rng.choices([t[0] for t in tiers], weights=[t[1] for t in tiers])[0]
        signup = date(2024, 1, 1) + timedelta(days=rng.randint(0, 970))       # 2024-01-01 .. 2026-08-28
        email = f"{given}.{family}.{1000 + i}".lower().replace(" ", "") + "@example.com"
        shoppers.append([2_500_001 + i, given, family, email, country, cc, tier, signup, rng.random() < 0.6])
    tables["shopper"] = (["shopper_id", "given_name", "family_name", "email", "country_code", "company_code",
                          "loyalty_tier", "signup_date", "marketing_opt_in"], shoppers)

    span = (END - START).days
    orders, lines = [], []
    weights = [3, 3, 2, 2, 3, 2, 2, 2, 2, 2, 1, 1]
    for s in shoppers:
        first = max(s[7], START)
        active_days = (END - first).days
        if active_days <= 0:
            continue
        expected = order_rate[s[6]] * active_days / span * rng.uniform(0.5, 1.5)
        n = int(expected) + (1 if rng.random() < expected - int(expected) else 0)
        for _ in range(n):
            od = first + timedelta(days=rng.randint(0, active_days))
            order_id = 7_000_001 + len(orders)
            items = rng.choices([1, 2, 3, 4], weights=[3, 4, 2, 1])[0]
            basket = []
            while len(basket) < items:                       # distinct products per order
                p = rng.choices(products, weights=weights)[0]
                if p not in basket:
                    basket.append(p)
            total, qty_total = 0.0, 0
            for p in basket:
                q = rng.choices([1, 2, 3, 4, 6], weights=[4, 4, 2, 1, 1])[0]
                amount = round(q * p[4], 2)
                total += amount
                qty_total += q
                lines.append([9_000_001 + len(lines), order_id, s[5], p[0], q, money(p[4]), money(amount)])
            r = rng.random()
            return_p = 0.22 if (s[5] == "DE01" and (od.year, od.month) == (2026, 8)) else 0.06
            status = "cancelled" if r < 0.03 else ("returned" if r < 0.03 + return_p else "delivered")
            total = round(total, 2)
            orders.append([order_id, f"WEB-{order_id}", s[0], s[5], s[4], od, status, CURRENCY[s[5]],
                           money(round(total / RATE[s[5]], 2)), money(total), qty_total])
    orders.sort(key=lambda o: (o[5], o[0]))
    tables["dtc_order"] = (["order_id", "order_number", "shopper_id", "company_code", "country_code", "order_date",
                            "order_status", "currency_code", "order_amount_local", "order_amount_eur", "item_count"], orders)
    tables["dtc_order_line"] = (["order_line_id", "order_id", "company_code", "product_id", "quantity",
                                 "unit_price_eur", "line_amount_eur"], lines)

    placed = [o for o in orders if o[6] != "cancelled"]
    kpi = {}
    for fy in (2025, 2026):
        po = [o for o in placed if o[5].year == fy and o[5].month <= 9]
        kpi[f"gmv_eur Jan-Sep {fy}"] = round(sum(float(o[9]) for o in po))
        kpi[f"orders Jan-Sep {fy}"] = len(po)
        kpi[f"aov_eur Jan-Sep {fy}"] = round(sum(float(o[9]) for o in po) / len(po), 2)
    kpi["return_rate_pct overall"] = round(100 * sum(o[6] == "returned" for o in placed) / len(placed), 1)
    de_aug = [o for o in placed if o[3] == "DE01" and (o[5].year, o[5].month) == (2026, 8)]
    kpi["return_rate_pct DE01 Aug 2026"] = round(100 * sum(o[6] == "returned" for o in de_aug) / max(len(de_aug), 1), 1)
    kpi["active_shoppers last 12 months"] = len({o[2] for o in placed if o[5] >= date(2025, 10, 1)})
    return tables, kpi


# =========================================================================================================
# Manufacturing: plant, production_line, production_order, downtime_event
# =========================================================================================================
def build_manufacturing():
    rng = random.Random(2026_03)
    tables = {}
    plants = [("SE-LUN", "Lund Food Plant", "SWE", "SE01", "Björkö Pantry", date(2011, 2, 1)),
              ("SE-NKP", "Norrköping Beverage Plant", "SWE", "SE01", "Kallkälla", date(2013, 3, 1)),
              ("FI-TMP", "Tampere Oat Drink Plant", "FIN", "FI01", "Kallkälla", date(2025, 4, 1)),
              ("PL-POZ", "Poznań Personal Care Plant", "POL", "PL01", "Mjuk Care", date(2016, 9, 1))]
    tables["plant"] = (["plant_code", "plant_name", "country_code", "company_code", "main_brand", "commissioning_date"], plants)
    lines = [  # line, plant, name, category, scrap target %, products, unit cost EUR
        ("SE-LUN-L1", "SE-LUN", "Crispbread baking and wrapping", "FOOD", 2.5, ["Björkö Crispbread Original"], 0.95),
        ("SE-LUN-L2", "SE-LUN", "Granola and muesli baking", "FOOD", 2.5, ["Björkö Granola Nordic Berries"], 1.40),
        ("SE-LUN-L3", "SE-LUN", "Porridge and jam packing", "FOOD", 2.0, ["Björkö Oat Porridge", "Björkö Lingonberry Jam"], 0.90),
        ("SE-NKP-L1", "SE-NKP", "Sparkling water filling (bottles)", "BEVERAGE", 1.5, ["Kallkälla Sparkling Lemon", "Kallkälla Sparkling Elderflower"], 0.22),
        ("SE-NKP-L2", "SE-NKP", "Sparkling water filling (cans)", "BEVERAGE", 1.5, ["Kallkälla Sparkling Lemon", "Kallkälla Sparkling Elderflower"], 0.20),
        ("SE-NKP-L3", "SE-NKP", "Juice filling", "BEVERAGE", 2.0, ["Kallkälla Apple Juice"], 0.70),
        ("FI-TMP-L1", "FI-TMP", "Oat base processing", "BEVERAGE", 3.0, ["Kallkälla Oat Drink"], 0.55),
        ("FI-TMP-L2", "FI-TMP", "Oat drink filling", "BEVERAGE", 2.5, ["Kallkälla Oat Drink"], 0.60),
        ("FI-TMP-L3", "FI-TMP", "Oat drink packing", "BEVERAGE", 2.0, ["Kallkälla Oat Drink"], 0.15),
        ("PL-POZ-L1", "PL-POZ", "Deodorant filling", "PERSONAL_CARE", 2.0, ["Mjuk Care Deodorant"], 1.30),
        ("PL-POZ-L2", "PL-POZ", "Liquid filling (shampoo, body wash)", "PERSONAL_CARE", 2.0, ["Mjuk Care Gentle Shampoo", "Mjuk Care Body Wash"], 1.80),
        ("PL-POZ-L3", "PL-POZ", "Hand cream filling", "PERSONAL_CARE", 2.0, ["Mjuk Care Hand Cream"], 1.60),
    ]
    tables["production_line"] = (["line_code", "plant_code", "line_name", "product_category", "scrap_target_pct"],
                                 [(l[0], l[1], l[2], l[3], f"{l[4]:.1f}") for l in lines])
    supervisors = {"SE-LUN": ["Karin Ek", "Johan Lindgren"], "SE-NKP": ["Per Ström", "Lina Wall"],
                   "FI-TMP": ["Juha Laine", "Satu Heikkinen"], "PL-POZ": ["Marta Kowalczyk", "Tomasz Lis"]}
    brand_of = {p[0]: p[4] for p in plants}
    commissioned = {p[0]: p[5] for p in plants}
    orders, events = [], []
    week = START
    while week <= END:
        for code, plant, _, _, target, products, unit_cost in lines:
            if week < commissioned[plant]:
                continue
            for _ in range(rng.choice([1, 1, 2])):
                start = week + timedelta(days=rng.randint(0, 4))
                finish = start + timedelta(days=rng.randint(1, 3))
                planned = rng.randrange(5_000, 40_001, 500)
                incident = code == "PL-POZ-L2" and date(2026, 3, 1) <= start <= date(2026, 4, 3)
                scrap_pct = rng.uniform(0.6, 1.4) * target / 100 * (4.5 if incident else 1.0)
                late = rng.random() < (0.55 if incident else 0.12)
                actual_finish = finish + timedelta(days=rng.randint(1, 3)) if late else finish
                status = "completed"
                if rng.random() < 0.02:
                    status = "cancelled"
                elif actual_finish > END:
                    status = "in_progress"
                produced = round(planned * rng.uniform(0.94, 1.03))
                scrap = round(produced * scrap_pct)
                good, done = produced - scrap, actual_finish
                if status == "cancelled":
                    good, scrap, done = 0, 0, None
                elif status == "in_progress":
                    good, scrap, done = None, None, None
                actual_cost = None if good is None else round((good + scrap) * unit_cost * rng.uniform(0.97, 1.06), 2)
                order_id = 5_000_001 + len(orders)
                orders.append([order_id, f"PO-{order_id}", plant, code, rng.choice(products), brand_of[plant], start,
                               finish, done, status, planned, good, scrap, money(planned * unit_cost),
                               None if actual_cost is None else money(actual_cost), rng.choice(supervisors[plant])])
                if status != "completed":
                    continue
                n_events = rng.choices([0, 1, 2], weights=[5, 4, 1])[0] + (2 if incident else 0)
                for k in range(n_events):
                    reason = "mechanical_failure" if incident and k < 2 else rng.choices(
                        ["changeover", "mechanical_failure", "material_shortage", "cleaning", "quality_hold"],
                        weights=[4, 2, 2, 2, 1])[0]
                    minutes = rng.randint(90, 420) if incident and reason == "mechanical_failure" else rng.randint(10, 120)
                    events.append([8_000_001 + len(events), order_id, plant, code,
                                   start + timedelta(days=rng.randint(0, (finish - start).days)), reason, minutes])
        week += timedelta(days=7)
    tables["production_order"] = (
        ["production_order_id", "order_number", "plant_code", "line_code", "product_name", "brand", "planned_start_date",
         "planned_finish_date", "actual_finish_date", "order_status", "planned_qty", "good_qty", "scrap_qty",
         "planned_cost_eur", "actual_cost_eur", "shift_supervisor"], orders)
    tables["downtime_event"] = (["downtime_event_id", "production_order_id", "plant_code", "line_code", "event_date",
                                 "reason", "duration_min"], events)

    done = [o for o in orders if o[9] == "completed"]
    kpi = {}
    for plant, *_ in plants:
        po = [o for o in done if o[2] == plant and o[8].year == 2026]
        kpi[f"yield_pct 2026 {plant}"] = round(100 * sum(o[11] for o in po) / sum(o[11] + o[12] for o in po), 2)
    for mth in (2, 3, 4):
        po = [o for o in done if o[3] == "PL-POZ-L2" and (o[8].year, o[8].month) == (2026, mth)]
        kpi[f"scrap_rate_pct PL-POZ-L2 2026-{mth:02d}"] = round(100 * sum(o[12] for o in po) / max(sum(o[11] + o[12] for o in po), 1), 2)
    kpi["on_time_pct overall"] = round(100 * sum(o[8] <= o[7] for o in done) / len(done), 1)
    kpi["downtime_hours PL-POZ-L2 Mar 2026"] = round(sum(e[6] for e in events if e[3] == "PL-POZ-L2"
                                                         and (e[4].year, e[4].month) == (2026, 3)) / 60, 1)
    return tables, kpi


# =========================================================================================================
# Genie Agent templates (serialized space version 2)
# =========================================================================================================
def nid(key: str) -> str:
    """Deterministic 32-hex id, stable across rebuilds."""
    return hashlib.md5(f"fjallmark-genie-lite:{key}".encode("utf-8")).hexdigest()


def lines_of(text: str) -> list:
    """SQL / text as the array-of-strings form of serialized_space (each line keeps its newline)."""
    parts = text.strip("\n").split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


def col(name, synonyms=None, match=False, exclude=False, description=None):
    c = {"column_name": name}
    if exclude:
        c["exclude"] = True
        return c
    if description:
        c["description"] = [description]
    if synonyms:
        c["synonyms"] = synonyms
    if match:
        c["enable_format_assistance"] = True
        c["enable_entity_matching"] = True
    return c


SHARED_RULES = """You are a Genie Agent of Fjällmark Consumer Goods AB, a fictional Nordic consumer-goods group
(brands Björkö Pantry = food, Kallkälla = beverages, Mjuk Care = personal care). Answer with SQL on the
tables and metric views of this agent only. The business definitions are the Pages of the domain
(repository folder bootcamp_domain/{sample}/05_context/pages/) - follow them.

CALENDAR
- Data covers 2025-01-01 to 2026-09-30. September 2026 is the last closed month: read "today", "this year",
  "last month" and "YTD" relative to 2026-09-30. Compare YTD with the same months (Jan-Sep) of 2025.
- Fiscal year = calendar year, fiscal period = month 1-12, Q1 = months 1-3.

CURRENCY
- Every amount column ending in _eur is in EUR and can be added across entities. Never add *_local amounts
  of different currencies. Always state the currency in the answer.

PRIVACY AND GOVERNANCE
- Never list names, e-mail addresses or other personal data; answer about people only in aggregate.
- Rows you cannot see are governance working as designed (a Unity Catalog row filter that shows each user
  only the company codes or plants they are mapped to) - say so instead of guessing.

STYLE
- State the definition, the period and the currency you used. If a question is ambiguous, state your
  assumption. Prefer the metric views: query them with MEASURE(<measure>) and GROUP BY ALL, never SELECT *.
- If a question belongs to another domain (consumer webshop, finance, manufacturing), say which Fjällmark
  analyst answers it instead of guessing.
"""

AGENTS = {
    "finance": {
        "title": "Fjällmark Finance Analyst",
        "description": "Finance analyst for Fjällmark Consumer Goods AB (fictional). Answers questions on the official Net "
                       "Revenue, COGS and gross margin (general ledger, EUR) by company code, brand and channel, and on "
                       "receivables, overdue AR and DSO. Simplified domain sample. Data: 2025-01 to 2026-09.",
        "rules": """YOU ARE THE FINANCE ANALYST.
- Company codes: SE01 Sweden (SEK, parent), NO01 Norway (NOK), DK01 Denmark (DKK), FI01 Finland (EUR),
  DE01 Germany + Netherlands (EUR), PL01 Poland (PLN, B2B only).
- "Revenue", "sales", "turnover" = NET REVENUE: SUM(journal_entry_line.amount_eur) of GL accounts in account
  group REVENUE (3010 DTC, 3020 B2B, 3090 returns and trade discounts, negative). Use finance.net_revenue_metrics.
- COGS = account group COGS (4000 standard cost, 4100 production variances). Gross margin = net revenue - COGS;
  gross margin % = ratio of sums, never an average of percentages.
- Receivables (finance.ar_invoice) are a snapshot as of 2026-09-30. Open AR = SUM(outstanding_amount_eur);
  overdue = open and due_date < 2026-09-30. DSO = open AR / (billed Jul-Sep 2026 / 92), per company code.
  Use finance.receivables_metrics.
- Known events: DE01 DSO is high because Alpina Drogerie disputes its invoices since June 2026; PL01 COGS
  spiked in March 2026 (production variance from the Poznań line PL-POZ-L2 incident).""",
        "tables": [
            ("finance.company_code", "The six legal entities (company codes) with currency and the fixed EUR rate.",
             [col("company_code", ["legal entity", "entity", "company"], True), col("company_name", None, True),
              col("country_code", ["country"], True), col("currency_code", ["local currency"], True)]),
            ("finance.gl_account", "Chart of accounts: account group REVENUE, COGS or OPEX decides the P&L line.",
             [col("account_group", ["P&L line"], True), col("account_name", None, True)]),
            ("finance.journal_entry_line", "General-ledger lines, one per company code, month, account, brand and channel. "
             "amount_eur = P&L amount in EUR (revenue positive, returns negative, costs positive).",
             [col("amount_eur", ["amount", "EUR amount"]), col("brand", None, True),
              col("channel", ["sales channel", "DTC or B2B"], True), col("company_code", ["legal entity", "entity"], True),
              col("currency_code", ["local currency"], True), col("journal_entry_line_id", exclude=True)]),
            ("finance.ar_invoice", "B2B customer invoices (accounts receivable), snapshot as of 2026-09-30.",
             [col("company_code", ["legal entity", "entity"], True), col("customer_contact_email", exclude=True),
              col("customer_name", ["customer", "trade account"], True),
              col("invoice_status", ["status"], True)]),
        ],
        "metric_views": [
            ("finance.net_revenue_metrics", "OFFICIAL Net Revenue, COGS, gross margin and OPEX in EUR from the general "
             "ledger, by fiscal year / quarter / period, company code, brand, channel and account.",
             [col("brand", None, True), col("channel", ["sales channel"], True), col("company_code", ["legal entity", "entity"], True)]),
            ("finance.receivables_metrics", "Open AR, overdue AR, disputed AR and DSO (EUR) as of 2026-09-30, by company "
             "code, customer, invoice status and aging bucket.",
             [col("aging_bucket", ["aging"], True), col("company_code", ["legal entity", "entity"], True),
              col("customer_name", ["customer"], True)]),
        ],
        "examples": [
            ("ex_rev_year", "What are net revenue, COGS and gross margin by fiscal year?",
             f"""SELECT fiscal_year,
       MEASURE(net_revenue_eur) AS net_revenue_eur,
       MEASURE(cogs_eur) AS cogs_eur,
       MEASURE(gross_margin_eur) AS gross_margin_eur,
       MEASURE(gross_margin_pct) AS gross_margin_pct
FROM {C}.finance.net_revenue_metrics
GROUP BY ALL
ORDER BY fiscal_year""", "Revenue / margin questions: the official Net Revenue from finance.net_revenue_metrics, EUR."),
            ("ex_dso", "What is DSO by company code?",
             f"""SELECT company_code, MEASURE(open_ar_eur) AS open_ar_eur, MEASURE(dso_days) AS dso_days
FROM {C}.finance.receivables_metrics
GROUP BY ALL
ORDER BY dso_days DESC""", "DSO and receivables questions: finance.receivables_metrics, snapshot 2026-09-30."),
            ("ex_ytd", "How does year-to-date net revenue compare with last year?",
             f"""SELECT fiscal_year, MEASURE(net_revenue_eur) AS net_revenue_eur
FROM {C}.finance.net_revenue_metrics
WHERE fiscal_period <= 9
GROUP BY ALL
ORDER BY fiscal_year""", "YTD = January-September; compare with the same months of 2025."),
        ],
        "measures": [("sn_open_ar", "open_ar_eur", "Open AR (EUR)", "SUM(ar_invoice.outstanding_amount_eur)",
                      ["open receivables", "outstanding balance"])],
        "filters": [("sn_overdue", "Overdue receivables",
                     "ar_invoice.outstanding_amount_eur > 0 AND ar_invoice.due_date < DATE'2026-09-30'", ["overdue", "past due"])],
        "sample_questions": [("sq_quarter", "What were net revenue and gross margin by quarter in 2026?"),
                             ("sq_brand", "Which brand has the highest gross margin?"),
                             ("sq_dso", "Which company has the highest DSO, and why?")],
        "benchmarks": [
            ("bm_rev_2025", "What was total net revenue in 2025?",
             f"SELECT MEASURE(net_revenue_eur) AS net_revenue_eur\nFROM {C}.finance.net_revenue_metrics\nWHERE fiscal_year = 2025"),
            ("bm_gm_brand_2026", "What is the gross margin % by brand in 2026?",
             f"SELECT brand, MEASURE(gross_margin_pct) AS gross_margin_pct\nFROM {C}.finance.net_revenue_metrics\n"
             "WHERE fiscal_year = 2026 AND brand IS NOT NULL\nGROUP BY ALL\nORDER BY brand"),
            ("bm_pl01_cogs", "What was COGS of PL01 by month in Q1 2026?",
             f"SELECT fiscal_period, MEASURE(cogs_eur) AS cogs_eur\nFROM {C}.finance.net_revenue_metrics\n"
             "WHERE company_code = 'PL01' AND fiscal_year = 2026 AND fiscal_period BETWEEN 1 AND 3\nGROUP BY ALL\nORDER BY fiscal_period"),
            ("bm_dso_de01", "What is the DSO of DE01?",
             f"SELECT MEASURE(dso_days) AS dso_days\nFROM {C}.finance.receivables_metrics\nWHERE company_code = 'DE01'"),
            ("bm_overdue", "How much overdue AR is there per company code?",
             f"SELECT company_code, MEASURE(overdue_ar_eur) AS overdue_ar_eur\nFROM {C}.finance.receivables_metrics\n"
             "GROUP BY ALL\nORDER BY company_code"),
        ],
        "tricky": ["bm_rev_2025"],
    },
    "consumer": {
        "title": "Fjällmark Consumer Analyst",
        "description": "Consumer analyst for Fjällmark Consumer Goods AB (fictional). Answers questions on the DTC webshop: "
                       "GMV, orders, average order value, returns, active shoppers and loyalty tiers by market. "
                       "Simplified domain sample. Data: 2025-01 to 2026-09.",
        "rules": """YOU ARE THE CONSUMER ANALYST (DTC webshop fjallmark.example).
- Markets: SE01 Sweden (SEK), NO01 Norway (NOK), DK01 Denmark (DKK), FI01 Finland (EUR), DE01 Germany and the
  Netherlands (EUR). company_code is the selling entity; country_code tells DEU from NLD.
- GMV = SUM(dtc_order.order_amount_eur) of placed orders (order_status delivered or returned; cancelled orders
  never count). Amounts are net of VAT, excl. shipping. Use consumer.dtc_sales_metrics.
- Average order value = GMV / number of placed orders. Return rate = returned orders / placed orders.
- Active shopper = a shopper with at least one placed order in the last 12 months (2025-10-01..2026-09-30).
- Loyalty tiers: Bronze, Silver, Gold, Platinum; NULL = not a member.
- GMV is an operational webshop figure, not revenue: official Net Revenue is the Finance Analyst's.
- Known event: DE01 returns jumped in August 2026 (parcels damaged by a carrier).""",
        "tables": [
            ("consumer.product", "The 12 webshop products with brand, category and list price (EUR).",
             [col("brand", None, True), col("category", ["product category"], True), col("product_name", ["product"], True)]),
            ("consumer.shopper", "Webshop shoppers: market, loyalty tier, sign-up date. Personal columns are hidden.",
             [col("company_code", ["market entity"], True), col("country_code", ["country", "market"], True),
              col("email", exclude=True), col("family_name", exclude=True), col("given_name", exclude=True),
              col("loyalty_tier", ["tier", "loyalty level"], True)]),
            ("consumer.dtc_order", "Webshop orders: one row per order, amount in market currency and EUR, status.",
             [col("company_code", ["market entity"], True), col("country_code", ["country", "market"], True),
              col("order_amount_eur", ["order value"]), col("order_status", ["status"], True)]),
            ("consumer.dtc_order_line", "Order lines: product, quantity and line amount (EUR).",
             [col("company_code", ["market entity"], True), col("line_amount_eur", ["line value"])]),
        ],
        "metric_views": [
            ("consumer.dtc_sales_metrics", "Webshop KPIs: GMV, orders, AOV, return rate and active shoppers (EUR), by "
             "order month / quarter / year, market, order status and loyalty tier.",
             [col("company_code", ["market entity"], True), col("country_code", ["country", "market"], True),
              col("loyalty_tier", ["tier"], True)]),
        ],
        "examples": [
            ("ex_gmv_month", "What is GMV by month in 2026?",
             f"""SELECT order_month, MEASURE(gmv_eur) AS gmv_eur, MEASURE(orders) AS orders
FROM {C}.consumer.dtc_sales_metrics
WHERE order_year = 2026
GROUP BY ALL
ORDER BY order_month""", "Webshop sales questions: GMV from consumer.dtc_sales_metrics, EUR, cancelled orders excluded."),
            ("ex_returns", "What is the return rate by market?",
             f"""SELECT country_code, MEASURE(return_rate_pct) AS return_rate_pct
FROM {C}.consumer.dtc_sales_metrics
GROUP BY ALL
ORDER BY return_rate_pct DESC""", "Return rate = returned / placed orders, from the metric view."),
            ("ex_brand", "What is GMV by brand?",
             f"""SELECT p.brand, SUM(l.line_amount_eur) AS gmv_eur
FROM {C}.consumer.dtc_order_line l
JOIN {C}.consumer.dtc_order o ON o.order_id = l.order_id
JOIN {C}.consumer.product p ON p.product_id = l.product_id
WHERE o.order_status <> 'cancelled'
GROUP BY ALL
ORDER BY gmv_eur DESC""", "Brand or product splits come from the order lines joined to product."),
        ],
        "measures": [("sn_placed_orders", "placed_orders", "Placed orders",
                      "COUNT(CASE WHEN dtc_order.order_status <> 'cancelled' THEN dtc_order.order_id END)", ["orders"])],
        "filters": [("sn_placed", "Placed orders", "dtc_order.order_status <> 'cancelled'", ["placed", "valid orders"])],
        "sample_questions": [("sq_gmv", "How did GMV develop month by month in 2026?"),
                             ("sq_tier", "What is the average order value by loyalty tier?"),
                             ("sq_returns", "Which market has the highest return rate, and why?")],
        "benchmarks": [
            ("bm_gmv_ytd", "What was GMV from January to September 2026?",
             f"SELECT MEASURE(gmv_eur) AS gmv_eur\nFROM {C}.consumer.dtc_sales_metrics\n"
             "WHERE order_date BETWEEN DATE'2026-01-01' AND DATE'2026-09-30'"),
            ("bm_aov_tier", "What is the average order value by loyalty tier?",
             f"SELECT loyalty_tier, MEASURE(average_order_value_eur) AS average_order_value_eur\n"
             f"FROM {C}.consumer.dtc_sales_metrics\nGROUP BY ALL\nORDER BY loyalty_tier"),
            ("bm_return_de", "What was the return rate of DE01 in August 2026?",
             f"SELECT MEASURE(return_rate_pct) AS return_rate_pct\nFROM {C}.consumer.dtc_sales_metrics\n"
             "WHERE company_code = 'DE01' AND order_month = DATE'2026-08-01'"),
            ("bm_active", "How many active shoppers do we have?",
             f"SELECT MEASURE(active_shoppers) AS active_shoppers\nFROM {C}.consumer.dtc_sales_metrics\n"
             "WHERE order_date BETWEEN DATE'2025-10-01' AND DATE'2026-09-30'"),
            ("bm_orders_market", "How many orders were placed per market in 2025?",
             f"SELECT country_code, MEASURE(orders) AS orders\nFROM {C}.consumer.dtc_sales_metrics\n"
             "WHERE order_year = 2025\nGROUP BY ALL\nORDER BY country_code"),
        ],
        "tricky": ["bm_active"],
    },
    "manufacturing": {
        "title": "Fjällmark Manufacturing Analyst",
        "description": "Manufacturing analyst for Fjällmark Consumer Goods AB (fictional). Answers questions on the four "
                       "plants and their lines: production orders, yield, scrap, on-time completion, downtime and "
                       "production cost. Simplified domain sample. Data: 2025-01 to 2026-09.",
        "rules": """YOU ARE THE MANUFACTURING ANALYST.
- Plants: SE-LUN Lund (food, Björkö Pantry), SE-NKP Norrköping (beverages, Kallkälla), FI-TMP Tampere (oat
  drinks, Kallkälla, commissioned April 2025), PL-POZ Poznań (personal care, Mjuk Care). Lines are named
  <plant>-L<n>, e.g. PL-POZ-L2 = liquid filling (shampoo, body wash).
- Only completed production orders count for yield, scrap and on-time KPIs; in_progress and cancelled orders
  do not. Use manufacturing.production_metrics.
- Yield = good_qty / (good_qty + scrap_qty); scrap rate = scrap_qty / (good_qty + scrap_qty); ratios of sums.
- On time = actual_finish_date <= planned_finish_date. Downtime = SUM(downtime_event.duration_min).
- Known event: March 2026, line PL-POZ-L2 had worn filler nozzles - scrap and downtime spiked until the repair
  on 4 April 2026.""",
        "tables": [
            ("manufacturing.plant", "The four plants with country, company code and main brand.",
             [col("plant_code", ["plant", "site"], True), col("plant_name", None, True)]),
            ("manufacturing.production_line", "The 12 production lines (3 per plant) with their scrap target.",
             [col("line_code", ["line"], True), col("line_name", None, True), col("plant_code", ["plant"], True)]),
            ("manufacturing.production_order", "Production orders: one product on one line; planned and actual dates, "
             "quantities, cost (EUR) and status.",
             [col("brand", None, True), col("line_code", ["line"], True), col("order_status", ["status"], True),
              col("plant_code", ["plant", "site"], True), col("product_name", ["product", "SKU"], True),
              col("shift_supervisor", exclude=True)]),
            ("manufacturing.downtime_event", "Stops on a line during a production order, with reason and minutes.",
             [col("line_code", ["line"], True), col("plant_code", ["plant"], True),
              col("reason", ["downtime reason", "cause"], True)]),
        ],
        "metric_views": [
            ("manufacturing.production_metrics", "Production KPIs of completed orders: yield, scrap rate, on-time "
             "completion, downtime and cost (EUR), by plant, line, product, brand and finish month / quarter / year.",
             [col("line_code", ["line"], True), col("plant_code", ["plant", "site"], True), col("product_name", ["product"], True)]),
        ],
        "examples": [
            ("ex_yield_plant", "What is the yield by plant in 2026?",
             f"""SELECT plant_code, MEASURE(yield_pct) AS yield_pct, MEASURE(scrap_rate_pct) AS scrap_rate_pct
FROM {C}.manufacturing.production_metrics
WHERE finish_year = 2026
GROUP BY ALL
ORDER BY plant_code""", "Yield / scrap questions: manufacturing.production_metrics, completed orders only."),
            ("ex_downtime_reason", "What are the main downtime reasons?",
             f"""SELECT reason, ROUND(SUM(duration_min) / 60, 1) AS downtime_hours
FROM {C}.manufacturing.downtime_event
GROUP BY ALL
ORDER BY downtime_hours DESC""", "Downtime by reason comes from manufacturing.downtime_event."),
            ("ex_line_month", "How did scrap develop on PL-POZ-L2 by month?",
             f"""SELECT finish_month, MEASURE(scrap_rate_pct) AS scrap_rate_pct, MEASURE(downtime_minutes) AS downtime_minutes
FROM {C}.manufacturing.production_metrics
WHERE line_code = 'PL-POZ-L2'
GROUP BY ALL
ORDER BY finish_month""", "Trends per line: group the metric view by finish_month."),
        ],
        "measures": [("sn_downtime_h", "downtime_hours", "Downtime (hours)", "SUM(downtime_event.duration_min) / 60",
                      ["downtime", "stop time"])],
        "filters": [("sn_completed", "Completed orders", "production_order.order_status = 'completed'", ["completed", "finished"])],
        "sample_questions": [("sq_yield", "What is the yield by plant in 2026?"),
                             ("sq_scrap", "Why did scrap spike in Poznań in March 2026?"),
                             ("sq_on_time", "Which line has the lowest on-time completion rate?")],
        "benchmarks": [
            ("bm_yield_2026", "What is the yield % per plant in 2026?",
             f"SELECT plant_code, MEASURE(yield_pct) AS yield_pct\nFROM {C}.manufacturing.production_metrics\n"
             "WHERE finish_year = 2026\nGROUP BY ALL\nORDER BY plant_code"),
            ("bm_scrap_l2", "What was the scrap rate of line PL-POZ-L2 in March 2026?",
             f"SELECT MEASURE(scrap_rate_pct) AS scrap_rate_pct\nFROM {C}.manufacturing.production_metrics\n"
             "WHERE line_code = 'PL-POZ-L2' AND finish_month = DATE'2026-03-01'"),
            ("bm_on_time", "What is the on-time completion rate per plant?",
             f"SELECT plant_code, MEASURE(on_time_completion_pct) AS on_time_completion_pct\n"
             f"FROM {C}.manufacturing.production_metrics\nGROUP BY ALL\nORDER BY plant_code"),
            ("bm_downtime_reason", "Which downtime reason caused the most minutes on PL-POZ-L2 in March 2026?",
             f"SELECT reason, SUM(duration_min) AS downtime_minutes\nFROM {C}.manufacturing.downtime_event\n"
             "WHERE line_code = 'PL-POZ-L2' AND event_date BETWEEN DATE'2026-03-01' AND DATE'2026-03-31'\n"
             "GROUP BY ALL\nORDER BY downtime_minutes DESC\nLIMIT 1"),
            ("bm_orders_plant", "How many production orders were completed per plant in 2025?",
             f"SELECT plant_code, MEASURE(completed_orders) AS completed_orders\nFROM {C}.manufacturing.production_metrics\n"
             "WHERE finish_year = 2025\nGROUP BY ALL\nORDER BY plant_code"),
        ],
        "tricky": ["bm_scrap_l2"],
    },
}

LICENSE_NOTE = [
    "Genie Agent template of a simplified Fjällmark domain sample - generated by bootcamp_domain/tools/build_samples.py,",
    "do not edit by hand. Table names follow the Lakehouse Industry Data Model - Consumer Goods v2 MVM (Copyright",
    "Databricks, Inc.; Databricks license, see bootcamp_domain/LICENSE.md and NOTICE.md); the simplified tables and the",
    "agent content are written for the fictional company Fjällmark Consumer Goods AB. Placeholder __CATALOG__ is",
    "replaced by 01_notebooks/04_genie_agent.py.",
]


def build_space(sample: str) -> dict:
    a = AGENTS[sample]
    by_id = lambda xs: sorted(xs, key=lambda x: x["id"])  # noqa: E731

    def source(identifier, description, cfgs):
        e = {"identifier": f"{C}.{identifier}", "description": [description]}
        if cfgs:
            e["column_configs"] = sorted(cfgs, key=lambda c: c["column_name"])
        return e

    text = SHARED_RULES.format(sample=sample) + "\n" + a["rules"] + "\n"
    space = {
        "version": 2,
        "config": {"sample_questions": by_id([{"id": nid(f"{sample}:{k}"), "question": [q]} for k, q in a["sample_questions"]])},
        "data_sources": {
            "tables": sorted([source(*t) for t in a["tables"]], key=lambda x: x["identifier"]),
            "metric_views": sorted([source(*m) for m in a["metric_views"]], key=lambda x: x["identifier"]),
        },
        "instructions": {
            "text_instructions": [{"id": nid(f"{sample}:text_instruction"), "content": lines_of(text)}],
            "example_question_sqls": by_id([{"id": nid(f"{sample}:{k}"), "question": [q], "sql": lines_of(sql),
                                             "usage_guidance": [g]} for k, q, sql, g in a["examples"]]),
            "join_specs": [],
            "sql_snippets": {
                "measures": by_id([{"id": nid(f"{sample}:{k}"), "alias": al, "display_name": dn, "sql": [s], "synonyms": syn}
                                   for k, al, dn, s, syn in a["measures"]]),
                "filters": by_id([{"id": nid(f"{sample}:{k}"), "display_name": dn, "sql": [s], "synonyms": syn}
                                  for k, dn, s, syn in a["filters"]]),
                "expressions": [],
            },
        },
        "benchmarks": {"questions": by_id([{"id": nid(f"{sample}:{k}"), "question": [q],
                                            "answer": [{"format": "SQL", "content": lines_of(sql)}]}
                                           for k, q, sql in a["benchmarks"]])},
    }
    for s in space["data_sources"]["tables"] + space["data_sources"]["metric_views"]:
        names = [c["column_name"] for c in s.get("column_configs", [])]
        assert len(names) == len(set(names)), f"duplicate column config in {s['identifier']}"
    for b in space["benchmarks"]["questions"]:
        assert "SELECT *" not in "".join(b["answer"][0]["content"]).upper()
    return space


def genie_template(sample: str) -> str:
    space = build_space(sample)
    a = AGENTS[sample]
    doc = {
        "_license": LICENSE_NOTE,
        "_generated_by": "bootcamp_domain/tools/build_samples.py",
        "template_version": hashlib.sha256(json.dumps(space, ensure_ascii=False).encode("utf-8")).hexdigest()[:12],
        "domain": sample,
        "title": a["title"],
        "description": a["description"],
        "tricky_benchmark_ids": sorted(nid(f"{sample}:{k}") for k in a["tricky"]),
        "serialized_space": space,
    }
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


# =========================================================================================================
# Write / check
# =========================================================================================================
def render() -> tuple:
    files, kpis = {}, {}
    for sample, builder in (("finance", build_finance), ("consumer", build_consumer),
                            ("manufacturing", build_manufacturing)):
        tables, kpi = builder()
        manifest = {"_note": "Row counts of the CSV files in this folder. Generated by bootcamp_domain/tools/build_samples.py.",
                    "schema": sample, "tables": {}}
        for table, (header, rows) in tables.items():
            files[f"{sample}/01_data/{table}.csv"] = csv_text(header, rows)
            manifest["tables"][table] = {"file": f"01_data/{table}.csv", "rows": len(rows), "columns": len(header)}
        files[f"{sample}/01_data/manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=1) + "\n"
        files[f"{sample}/04_genie/fjallmark_{sample}_analyst.json"] = genie_template(sample)
        kpis[sample] = kpi
    return files, kpis


def main() -> int:
    check = "--check" in sys.argv[1:]
    files, kpis = render()
    stale = []
    for rel, text in files.items():
        path = ROOT / rel
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {rel}")
    if check:
        print("\n".join(f"stale: {s}" for s in stale) or f"OK - {len(files)} generated files up to date")
        return 1 if stale else 0
    for sample, kpi in kpis.items():
        print(f"\n{sample} reference KPIs (a user who sees everything):")
        for k, v in kpi.items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
