# TUH Specimen Rejection Dashboard

Streamlit dashboard for the TUH laboratory specimen rejection report.

## Streamlit Community Cloud

- Main file: app.py
- Python dependencies: requirements.txt
- Source workbook: แบบบันทึกการปฏิเสธสิ่งส่งตรวจ.xlsx

Deploy the current branch from a GitHub repository and select app.py as the main file.

## Monthly Google Sheets workflow

Add one tab for each calendar month in the connected Google workbook. Name it with
the Thai month and year, for example `ต.ค. 69`, `พ.ย. 69`, `ม.ค. 70`, or
`ตุลาคม 2569`. Both two-digit and four-digit Buddhist years are supported, as
well as four-digit Gregorian years. Keep the same column headers as the prior
monthly tab; it is fine to create an empty tab before entering the first case.
The dashboard picks up new rows and fiscal years automatically within 15 minutes
while open (or on the next visit). Tabs without a year or a readable header are
skipped and reported in the dashboard. A case is counted once even if it has
multiple rejection reasons.

## Rejection rate (%)

The dashboard does not infer a denominator from rejected cases. The existing
auto-generated `ยอดตรวจทั้งหมด` tab counts rejection records and is ignored
unless a row explicitly has `แหล่งข้อมูล` = `LIS`. For real rates, add a
separate tab named `ยอดตรวจจริง` with `เดือน`, `Ward`, and
`จำนวนสิ่งส่งตรวจทั้งหมด`, populated from the laboratory information system.
Use month values such as `ต.ค. 69`, `2026-10`, or a spreadsheet date. Add one
row per month and Ward; a blank Ward can hold the hospital-wide monthly total.
The dashboard calculates monthly and month-by-Ward rejection rates after the
next sync. Months or Wards without a valid total are marked as unavailable.
Rate numerators are affected by fiscal-year, month, and Ward filters, but not
by cause or resolution filters.

## Microbiology workload statistics

The dashboard also syncs the shared workbook `รวมสถิติการส่งตรวจทางจุลชีววิทยา
(ปีงบ) -NEW.xlsx` and adds a `🧫 งานจุลชีววิทยา` tab. It reads the repeated
`แยก Culture เดือน` blocks and the `แยก Culture ปี` table, so a new fiscal-year
block can be added without changing the parser. The tab provides fiscal-year
selection, specimen-type filters, monthly totals, year-to-year comparison, a
monthly breakdown table, and CSV export.
The `ยอดตรวจทั้งหมด` tab can include an explicit `LIS` column for overall
monthly totals. These rows keep Ward blank because the microbiology workbook
does not provide Ward-level counts, so the same LIS total is never repeated
across individual Ward rows.
