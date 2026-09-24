"""Regression checks for the monthly Google Sheets workflow."""

import io
import unittest

import pandas as pd
from openpyxl import Workbook

from cleaner import get_kpis, get_rejection_rate_tables, load_and_consolidate, load_microbiology_stats, parse_sheet_month


HEADERS = ['วันที่', 'เวลา', 'HN', 'Ward', 'สิ่งส่งตรวจ', 'ใบส่งตรวจ']


def make_workbook(november_has_case=False, with_denominator=False):
    book = Workbook()
    book.remove(book.active)

    def monthly_sheet(name, day=None, header=True):
        sheet = book.create_sheet(name)
        if header:
            sheet.append(HEADERS)
        if day is not None:
            sheet.append([day, '09:00', 'HN-ปิดบัง', 'อช.ส', 'ติดชื่อผิดราย', None])

    # Staff may drag tabs, so workbook order must not determine chronology.
    monthly_sheet('ม.ค. 70', 2)
    monthly_sheet('พ.ย. 69', 3 if november_has_case else None)
    monthly_sheet('ต.ค. 69', 1)
    monthly_sheet('ธ.ค. 69', 5, header=False)  # incomplete new tab
    monthly_sheet('ต.ค.', 4)  # missing year, cannot be assigned safely
    monthly_sheet('หมายเหตุ ต.ค. 69', 6)  # helper tab, not a monthly tab
    monthly_sheet('สรุป', 7)  # existing summary, must not double count
    if with_denominator:
        totals = book.create_sheet('ยอดตรวจทั้งหมด')
        totals.append(['เดือน', 'จำนวนสิ่งส่งตรวจทั้งหมด', 'แหล่งข้อมูล'])
        totals.append(['ต.ค. 69', 100, 'LIS'])
        totals.append(['พ.ย. 69', 200, 'LIS'])
        totals.append(['ม.ค. 70', 300, 'LIS'])

    result = io.BytesIO()
    book.save(result)
    result.seek(0)
    result.name = 'monthly.xlsx'
    return result


class MonthlyTabsTest(unittest.TestCase):
    def test_month_names_require_unambiguous_year(self):
        self.assertEqual(parse_sheet_month('ต.ค. 69')[:2], (10, 2026))
        self.assertEqual(parse_sheet_month('ม.ค.70')[:2], (1, 2027))
        self.assertEqual(parse_sheet_month('ตุลาคม 2569')[:2], (10, 2026))
        self.assertEqual(parse_sheet_month('ต.ค. 2026')[:2], (10, 2026))
        self.assertIsNone(parse_sheet_month('ต.ค.')[0])
        self.assertIsNone(parse_sheet_month('หมายเหตุ ต.ค. 69')[0])

    def test_new_month_is_read_and_empty_future_tab_is_safe(self):
        cases, causes = load_and_consolidate(make_workbook())
        self.assertEqual(cases['date'].tolist(), ['2026-10-01', '2027-01-02'])
        self.assertEqual(cases['fiscal_year'].tolist(), ['ปีงบประมาณ 2570'] * 2)
        self.assertEqual(len(causes), 2)
        self.assertTrue(any('ธ.ค. 69' in warning for warning in cases.attrs['ingestion_warnings']))
        self.assertTrue(any('ชื่อไม่ครบ' in warning for warning in cases.attrs['ingestion_warnings']))

    def test_rows_added_later_appear_without_code_change(self):
        cases, _ = load_and_consolidate(make_workbook(november_has_case=True))
        self.assertEqual(cases['date'].tolist(), ['2026-10-01', '2026-11-03', '2027-01-02'])

    def test_yearless_only_tab_is_not_assigned_to_wrong_fiscal_year(self):
        book = Workbook()
        sheet = book.active
        sheet.title = 'ต.ค.'
        sheet.append(HEADERS)
        sheet.append([1, '09:00', 'HN-ปิดบัง', 'อช.ส', 'ติดชื่อผิดราย', None])
        result = io.BytesIO()
        book.save(result)
        result.seek(0)
        result.name = 'yearless.xlsx'

        cases, _ = load_and_consolidate(result)
        self.assertTrue(cases.empty)
        self.assertTrue(cases.attrs['ingestion_warnings'])

    def test_optional_denominator_sheet_is_loaded(self):
        cases, _ = load_and_consolidate(make_workbook(with_denominator=True))
        denominator = cases.attrs['denominator']
        self.assertEqual(denominator['year_month'].tolist(), ['2026-10', '2026-11', '2027-01'])
        self.assertEqual(denominator['total_specimens'].tolist(), [100.0, 200.0, 300.0])
        self.assertTrue(cases.attrs['denominator_sheet_found'])

    def test_generated_rejection_counts_are_not_accepted_as_real_totals(self):
        book = Workbook()
        sheet = book.active
        sheet.title = 'ก.ย. 69'
        sheet.append(HEADERS)
        sheet.append([1, '09:00', 'HN-ปิดบัง', 'อช.ส', 'ติดชื่อผิดราย', None])
        fake = book.create_sheet('ยอดตรวจทั้งหมด')
        fake.append(['เดือน', 'จำนวนสิ่งส่งตรวจทั้งหมด', 'Ward'])
        fake.append(['ก.ย. 69', 1, 'อช.ส'])
        source = io.BytesIO()
        book.save(source)
        source.seek(0)
        cases, _ = load_and_consolidate(source)
        self.assertTrue(cases.attrs['denominator'].empty)
        self.assertTrue(any('แหล่งข้อมูล' in warning for warning in cases.attrs['ingestion_warnings']))

    def test_microbiology_parser_reads_repeated_fiscal_year_blocks(self):
        book = Workbook()
        monthly = book.active
        monthly.title = 'แยก Culture เดือน '
        monthly.append(['สถิติ'])
        monthly.append(['ปีงบ 2569'])
        monthly.append(['เดือน', 'รายการสิ่งส่งตรวจ'])
        monthly.append([None, 'Hemo', 'Urine', 'Fungus'])
        monthly.append(['ตุลาคม', 10, 20, 3])
        monthly.append(['พฤศจิกายน', 11, 21, 4])
        monthly.append(['Total.', 21, 41, 7])
        annual = book.create_sheet('แยก Culture ปี')
        annual.append(['รายการสิ่งส่งตรวจ', 'ปีงบประมาณ'])
        annual.append([None, 2568, 2569])
        annual.append(['Hemo', 100, None])
        annual.append(['Urine', 200, None])
        annual.append(['Fungus', 30, None])
        result = io.BytesIO()
        book.save(result)
        result.seek(0)
        stats = load_microbiology_stats(result)
        self.assertEqual(len(stats['monthly']), 6)
        self.assertEqual(stats['monthly']['count'].sum(), 69)
        fy2569 = stats['annual'][stats['annual']['fiscal_year_num'] == 2569]
        self.assertEqual(fy2569['count'].sum(), 69)
        self.assertEqual(stats['annual'][stats['annual']['fiscal_year_num'] == 2568]['count'].sum(), 330)

    def test_microbiology_annual_parser_does_not_treat_counts_as_fiscal_years(self):
        book = Workbook()
        annual = book.active
        annual.title = 'แยก Culture ปี'
        annual.append(['รายการสิ่งส่งตรวจ', 'ปีงบประมาณ'])
        annual.append([None, 2568, 2569])
        annual.append(['Hemo', 19114, None])
        annual.append(['Stool', 2611, None])
        annual.append(['Urine', 8906, None])
        result = io.BytesIO()
        book.save(result)
        result.seek(0)

        stats = load_microbiology_stats(result)
        self.assertEqual(sorted(stats['annual']['fiscal_year_num'].unique().tolist()), [2568])
        self.assertNotIn(2611, stats['annual']['fiscal_year_num'].tolist())

    def test_repeated_thai_vowel_joins_the_same_ward_in_kpi_and_detail(self):
        book = Workbook()
        sheet = book.active
        sheet.title = 'ก.ย. 69'
        sheet.append(HEADERS)
        sheet.append([1, '09:00', 'HN-ปิดบัง', 'อายุรกรรมหญิงสามัญ', 'ติดชื่อผิดราย', None])
        sheet.append([2, '09:00', 'HN-ปิดบัง', 'อายุุรกรรมหญิงสามัญ', 'ติดชื่อผิดราย', None])
        source = io.BytesIO()
        book.save(source)
        source.seek(0)
        source.name = 'wards.xlsx'

        cases, causes = load_and_consolidate(source)
        target = 'อายุรกรรมหญิงสามัญ'
        self.assertEqual(cases['ward_standard'].unique().tolist(), [target])
        self.assertEqual(get_kpis(cases, causes)['top_ward_cases'], 2)
        self.assertEqual(len(cases[cases['ward_standard'] == target]), 2)

    def test_real_rate_uses_month_and_ward_totals_without_double_counting(self):
        cases = pd.DataFrame([
            {'year_month': '2026-09', 'thai_month_year': 'ก.ย. 2569', 'ward_standard': 'Ward A'},
            {'year_month': '2026-09', 'thai_month_year': 'ก.ย. 2569', 'ward_standard': 'Ward B'},
        ])
        totals = pd.DataFrame([
            {'year_month': '2026-09', 'thai_month_year': 'ก.ย. 2569', 'ward_standard': '', 'total_specimens': 300},
            {'year_month': '2026-09', 'thai_month_year': 'ก.ย. 2569', 'ward_standard': 'Ward A', 'total_specimens': 100},
            {'year_month': '2026-09', 'thai_month_year': 'ก.ย. 2569', 'ward_standard': 'Ward B', 'total_specimens': 200},
        ])
        months, wards = get_rejection_rate_tables(cases, totals, ['2026-09'], ['Ward A', 'Ward B'], ['Ward A', 'Ward B'])
        self.assertEqual(months.iloc[0]['total_specimens'], 300)
        self.assertEqual(months.iloc[0]['rejected'], 2)
        self.assertEqual(wards.set_index('ward_standard').loc['Ward A', 'rate_pct'], 1.0)

        one_month, one_ward = get_rejection_rate_tables(cases, totals, ['2026-09'], ['Ward A'], ['Ward A', 'Ward B'])
        self.assertEqual(one_month.iloc[0]['total_specimens'], 100)
        self.assertEqual(one_month.iloc[0]['rate_pct'], 1.0)

        missing = totals[totals['ward_standard'].ne('Ward A')]
        missing_month, missing_ward = get_rejection_rate_tables(cases, missing, ['2026-09'], ['Ward A'], ['Ward A', 'Ward B'])
        self.assertEqual(missing_month.iloc[0]['status'], 'ไม่มีตัวหาร')
        self.assertEqual(missing_ward.iloc[0]['status'], 'ไม่มีตัวหาร')


if __name__ == '__main__':
    unittest.main()
