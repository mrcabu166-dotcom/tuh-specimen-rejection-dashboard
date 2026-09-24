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

The dashboard does not infer a denominator from rejected cases. To calculate a
real rejection rate, optionally add a tab named `ยอดตรวจทั้งหมด` with two columns:
`เดือน` and `จำนวนสิ่งส่งตรวจทั้งหมด`. Use month values such as `ต.ค. 69`,
`2026-10`, or a spreadsheet date. The dashboard will show the overall and
monthly rate after the next sync. An optional `Ward` column enables Ward-level
rates; without it, the rate is available for the overall selected period only.
