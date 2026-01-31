# invoice_app.py
# pip install flask reportlab

import os
import sqlite3
from flask import Flask, render_template_string, request, send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

app = Flask(__name__)
DB = "invoice.db"

# -----------------------------
# DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            invoice_no TEXT,
            invoice_date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            description TEXT,
            hsn TEXT,
            qty REAL,
            rate REAL
        )
    """)
    conn.commit()
    conn.close()

# -----------------------------
# HTML FORM
# -----------------------------
FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>GST Invoice Generator</title>
<style>
body { font-family: Arial; background:#f4f4f4; }
.container { background:#fff; padding:20px; width:800px; margin:auto; }
input { width:200px; margin:5px; }
button { padding:8px 15px; margin-top:10px; }
</style>
</head>
<body>
<div class="container">
<h2>GST Invoice Generator</h2>

<form method="POST">
<b>Company Name</b><br>
<input name="company_name" required><br>

<b>Invoice No</b><br>
<input name="invoice_no" required><br>

<b>Invoice Date</b><br>
<input name="invoice_date"><br><br>

<h3>Items</h3>
<div id="items">
<div>
Desc <input name="desc_1">
HSN <input name="hsn_1">
Qty <input name="qty_1">
Rate <input name="rate_1"><br><br>
</div>
</div>

<button type="button" onclick="addItem()">Add Item</button><br><br>
<button type="submit">Generate PDF</button>
</form>
</div>

<script>
let count = 1;
function addItem(){
    count++;
    let div = document.createElement("div");
    div.innerHTML = `
    Desc <input name="desc_${count}">
    HSN <input name="hsn_${count}">
    Qty <input name="qty_${count}">
    Rate <input name="rate_${count}"><br><br>`;
    document.getElementById("items").appendChild(div);
}
</script>

</body>
</html>
"""

# -----------------------------
# ROUTE
# -----------------------------
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        company_name = request.form["company_name"]
        invoice_no = request.form["invoice_no"]
        invoice_date = request.form.get("invoice_date","")

        items = []
        i = 1
        while f"desc_{i}" in request.form:
            desc = request.form.get(f"desc_{i}")
            hsn = request.form.get(f"hsn_{i}")
            try:
                qty = float(request.form.get(f"qty_{i}") or 0)
                rate = float(request.form.get(f"rate_{i}") or 0)
            except:
                qty, rate = 0, 0

            if qty > 0:
                items.append({"desc":desc,"hsn":hsn,"qty":qty,"rate":rate})
            i += 1

        if not items:
            return "<h3>No valid items added</h3>"

        # Save DB
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO invoices(company_name,invoice_no,invoice_date) VALUES (?,?,?)",
                  (company_name, invoice_no, invoice_date))
        invoice_id = c.lastrowid

        for item in items:
            c.execute("INSERT INTO items(invoice_id,description,hsn,qty,rate) VALUES (?,?,?,?,?)",
                      (invoice_id,item["desc"],item["hsn"],item["qty"],item["rate"]))
        conn.commit()
        conn.close()

        # PDF
        pdf_name = f"invoice_{invoice_no}.pdf"
        doc = SimpleDocTemplate(pdf_name, pagesize=A4,
                                rightMargin=20*mm,leftMargin=20*mm,
                                topMargin=20*mm,bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"<b>{company_name}</b>", styles["Title"]))
        elements.append(Paragraph(f"Invoice No: {invoice_no}", styles["Normal"]))
        elements.append(Paragraph(f"Date: {invoice_date}", styles["Normal"]))
        elements.append(Spacer(1,12))

        table_data = [["#", "Description", "HSN", "Qty", "Rate", "Amount"]]
        total = 0
        for idx,item in enumerate(items,1):
            amt = item["qty"] * item["rate"]
            total += amt
            table_data.append([idx,item["desc"],item["hsn"],item["qty"],item["rate"],f"{amt:.2f}"])
        table_data.append(["","","","","Total",f"{total:.2f}"])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),0.5,colors.black),
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey)
        ]))

        elements.append(table)
        doc.build(elements)

        return send_file(pdf_name, as_attachment=True)

    return render_template_string(FORM_HTML)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
