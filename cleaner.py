"""
cleaner.py
Data Ingestion, Header Auto-Detection, Ward Standardization,
Cause Normalization, and Aggregations for TUH Specimen Rejection Reports.
"""

import os
import re
import io
import pandas as pd
import numpy as np

# ==============================================================================
# 1. DICTIONARIES & MAPPINGS
# ==============================================================================

# Thai Month mapping
THAI_MONTHS = {
    'ม.ค.': 1, 'ม.ค': 1, 'มกราคม': 1,
    'ก.พ.': 2, 'ก.พ': 2, 'กุมภาพันธ์': 2,
    'มี.ค.': 3, 'มี.ค': 3, 'มีนาคม': 3,
    'เม.ย.': 4, 'เม.ย': 4, 'เมษายน': 4,
    'พ.ค.': 5, 'พ.ค': 5, 'พฤษภาคม': 5,
    'มิ.ย.': 6, 'มิ.ย': 6, 'มิถุนายน': 6,
    'ก.ค.': 7, 'ก.ค': 7, 'กรกฎาคม': 7,
    'ส.ค.': 8, 'ส.ค': 8, 'สิงหาคม': 8,
    'ก.ย.': 9, 'ก.ย': 9, 'กันยายน': 9,
    'ต.ค.': 10, 'ต.ค': 10, 'ตุลาคม': 10,
    'พ.ย.': 11, 'พ.ย': 11, 'พฤศจิกายน': 11,
    'ธ.ค.': 12, 'ธ.ค': 12, 'ธันวาคม': 12,
}

THAI_MONTH_NAMES_SHORT = [
    '', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
    'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'
]

DENOMINATOR_SHEET_MARKERS = (
    'ยอดตรวจจริง', 'ยอดตรวจทั้งหมด', 'ยอดสิ่งส่งตรวจ', 'จำนวนสิ่งส่งตรวจทั้งหมด',
    'ตัวหาร', 'denominator', 'total specimen', 'total specimens',
    'total sample', 'total samples'
)

MONTH_SHEET_PATTERN = re.compile(
    r"^\s*(?P<month>" + "|".join(re.escape(name) for name in sorted(THAI_MONTHS, key=len, reverse=True))
    + r")\s*(?P<year>[0-9๐-๙]{2}|[0-9๐-๙]{4})\s*$"
)

# Standard Hospital Ward Mapping
# Maps raw ward names, abbreviations, typos, and variations to official hospital ward names
WARD_MAPPING = {
    # --- อายุรกรรม (Internal Medicine) ---
    'อช.ส': 'อายุรกรรมชายสามัญ',
    'อช-สามัญ': 'อายุรกรรมชายสามัญ',
    'อช.สามัญ': 'อายุรกรรมชายสามัญ',
    'ACH.S': 'อายุรกรรมชายสามัญ',
    'อายุรกรรมชายสามัญ': 'อายุรกรรมชายสามัญ',
    
    'อช.พ': 'อายุรกรรมชายพิเศษ',
    'อช-พิเศษ': 'อายุรกรรมชายพิเศษ',
    'อช.พิเศษ': 'อายุรกรรมชายพิเศษ',
    'อายุรกรรมชายพิเศษ': 'อายุรกรรมชายพิเศษ',
    'อายุุรกรรมชายพิเศษ': 'อายุรกรรมชายพิเศษ',
    
    'อญ.ส': 'อายุรกรรมหญิงสามัญ',
    'อญ-สามัญ': 'อายุรกรรมหญิงสามัญ',
    'อญ.สามัญ': 'อายุรกรรมหญิงสามัญ',
    'อายุรกรรมหญิงสามัญ': 'อายุรกรรมหญิงสามัญ',
    'อายุกรรมหญิงสามัญ': 'อายุรกรรมหญิงสามัญ',
    'อายุรกรรมหญิงสามััญ': 'อายุรกรรมหญิงสามัญ',
    'อายุรกรรมหญิิงสามัญ': 'อายุรกรรมหญิงสามัญ',
    'อายุรกรรมหญฺิงสามัญ': 'อายุรกรรมหญิงสามัญ',
    'อายุหญิงสามัญ': 'อายุรกรรมหญิงสามัญ',
    
    'อญ-พิเศษ': 'อายุรกรรมหญิงพิเศษ',
    'อายุรกรรมหญิงพิเศษ': 'อายุรกรรมหญิงพิเศษ',
    
    'Med Kitti': 'อายุรกรรมกิตติวัฒนา',
    'Med.Kitti': 'อายุรกรรมกิตติวัฒนา',
    'MED.KITTI': 'อายุรกรรมกิตติวัฒนา',
    'med.kiti': 'อายุรกรรมกิตติวัฒนา',
    'Med.kitti': 'อายุรกรรมกิตติวัฒนา',
    'M.kiti': 'อายุรกรรมกิตติวัฒนา',
    'อายุรกรรมกิตติวัฒนา': 'อายุรกรรมกิตติวัฒนา',
    'อายุรกรรมกิตติ': 'อายุรกรรมกิตติวัฒนา',
    'อายุุรกรรมกิตติ': 'อายุรกรรมกิตติวัฒนา',
    
    'อายุรกรรมความดันลบ': 'อายุรกรรมความดันลบ',
    'อายุุรกรรมความดันลบ': 'อายุรกรรมความดันลบ',
    'อายุรกรรมลบ': 'อายุรกรรมความดันลบ',
    
    'อายุรกรรม': 'อายุรกรรมทั่วไป',
    
    # --- ศัลยกรรม (Surgery) ---
    'ศัลยกรรม 1': 'ศัลยกรรม 1',
    'ศัลยกรรม1': 'ศัลยกรรม 1',
    'Sur1': 'ศัลยกรรม 1',
    
    'ศัลยกรรม 2': 'ศัลยกรรม 2',
    'ศัลยกรรม2': 'ศัลยกรรม 2',
    'sur2': 'ศัลยกรรม 2',
    'ser.2': 'ศัลยกรรม 2',
    
    'ศัลยกรรม 3': 'ศัลยกรรม 3',
    'ศัลยกรรม3': 'ศัลยกรรม 3',
    
    'ศัลยกรรมพิเศษ 1': 'ศัลยกรรมพิเศษ 1',
    'ศัลยกรรมพิเศษ1': 'ศัลยกรรมพิเศษ 1',
    'ศััลยกรรมพิเศษ 1': 'ศัลยกรรมพิเศษ 1',
    
    'ศัลยกรรมพิเศษ 2': 'ศัลยกรรมพิเศษ 2',
    'ศัลยกรรมพิเศษ2': 'ศัลยกรรมพิเศษ 2',
    'ศัลพิเศษ2': 'ศัลยกรรมพิเศษ 2',
    'ศัล-พิเศษ 2': 'ศัลยกรรมพิเศษ 2',
    
    'ศัลยกรรม-พิเศษ': 'ศัลยกรรมพิเศษ',
    'ศัลยกรรมพิเศษ': 'ศัลยกรรมพิเศษ',
    
    # --- ศัลยกรรมกระดูกและข้อ (Orthopedics) ---
    'ศัลยกรรมกระดูกและข้อสามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศัลกรรมกระดูกและข้อสามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ortho.สามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศัลยกรรมกระดูก-สามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศัลยกรรมกระดูกสามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศัลกระดูกสามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศูัลยกรรมกระดูกและข้อสามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศัลกระดูกและข้อสามัญ': 'ศัลยกรรมกระดูกและข้อสามัญ',
    'ศัลยกรรมกระดูก': 'ศัลยกรรมกระดูกและข้อสามัญ',
    
    'ศัลยกรรมกระดูกและข้อพิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัลกระดูกพิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัลกระดูก-พิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัลกระดูกข้อพิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัลยกรรมกระดูก-พิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัลยกรรมกระดูกพิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัล-กระดูกพิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    'ศัลย์กระดูกและข้อพิเศษ': 'ศัลยกรรมกระดูกและข้อพิเศษ',
    
    # --- กุมารเวชกรรม (Pediatrics) ---
    'Ped1': 'กุมารเวชกรรม 1',
    'กุมารเวชกรรม1': 'กุมารเวชกรรม 1',
    'กุุมารเวชกรรม 1': 'กุมารเวชกรรม 1',
    'กุุมารเวชกรรม1': 'กุมารเวชกรรม 1',
    
    'กุมารเวชกรรม2': 'กุมารเวชกรรม 2',
    'กุมาร 2': 'กุมารเวชกรรม 2',
    'กุมารเวชกรรม 2': 'กุมารเวชกรรม 2',
    
    'กุมารพิเศษ': 'กุมารเวชกรรมพิเศษ',
    'กุุมารเวชกรรมพิเศษ': 'กุมารเวชกรรมพิเศษ',
    
    # --- สูติ-นรีเวชกรรม (OB-GYN) ---
    'สูติ-นรีเวชกรรมสามัญ': 'สูติ-นรีเวชกรรมสามัญ',
    'สูติสามัญ': 'สูติ-นรีเวชกรรมสามัญ',
    'สูติ-สามัญ': 'สูติ-นรีเวชกรรมสามัญ',
    'สูติ-นรีสามัญ': 'สูติ-นรีเวชกรรมสามัญ',
    
    'สูติ-นรีเวชกรรมพิเศษ': 'สูติ-นรีเวชกรรมพิเศษ',
    
    'ห้องคลอด': 'ห้องคลอด (LR)',
    'งานพยาบาลผู้คลอด': 'ห้องคลอด (LR)',
    'LR': 'ห้องคลอด (LR)',
    
    # --- หอผู้ป่วยวิกฤต (ICU / Critical Care) ---
    'MICU': 'หอผู้ป่วยวิกฤตอายุรกรรม (MICU)',
    'icum': 'หอผู้ป่วยวิกฤตอายุรกรรม (MICU)',
    'วิกฤตอายุรกรรม': 'หอผู้ป่วยวิกฤตอายุรกรรม (MICU)',
    'วิกฤตอายุรกรรม(ดุลชั้น4)': 'หอผู้ป่วยวิกฤตอายุรกรรม (MICU)',
    
    'sicu': 'หอผู้ป่วยวิกฤตศัลยกรรม (SICU)',
    'SICU': 'หอผู้ป่วยวิกฤตศัลยกรรม (SICU)',
    'วิกฤตศัลยกรรม': 'หอผู้ป่วยวิกฤตศัลยกรรม (SICU)',
    'วิฤตศัลยกรรม': 'หอผู้ป่วยวิกฤตศัลยกรรม (SICU)',
    'วิกฤตศัลยกรรมหัวใจและทรวงอก': 'หอผู้ป่วยวิกฤตศัลยกรรมหัวใจและทรวงอก (CVT ICU)',
    
    'RICU': 'หอผู้ป่วยวิกฤตระบบการหายใจ (RICU)',
    'วิกฤตระบบหายใจ': 'หอผู้ป่วยวิกฤตระบบการหายใจ (RICU)',
    'วิกฤตระบบการหายใจ': 'หอผู้ป่วยวิกฤตระบบการหายใจ (RICU)',
    
    'CCU': 'หอผู้ป่วยวิกฤตโรคหัวใจ (CCU)',
    'ccu': 'หอผู้ป่วยวิกฤตโรคหัวใจ (CCU)',
    'วิกฤตโรคหัวใจ': 'หอผู้ป่วยวิกฤตโรคหัวใจ (CCU)',
    'วิกฤโรคหัวใจ': 'หอผู้ป่วยวิกฤตโรคหัวใจ (CCU)',
    
    'NICU': 'หอผู้ป่วยทารกแรกเกิดวิกฤต (NICU)',
    'กึ่งวิกฤตทารกแรกเกิด': 'หอผู้ป่วยทารกแรกเกิดวิกฤต (NICU)',
    
    'PICU': 'หอผู้ป่วยวิกฤตกุมารเวชกรรม (PICU)',
    'วิกฤตกุมาร': 'หอผู้ป่วยวิกฤตกุมารเวชกรรม (PICU)',
    'วิกฤตกุมารเวชกรรม': 'หอผู้ป่วยวิกฤตกุมารเวชกรรม (PICU)',
    
    'วิกฤตวิสัญญี': 'หอผู้ป่วยวิกฤตวิสัญญี',
    'วิกฤตวิสัญญี่': 'หอผู้ป่วยวิกฤตวิสัญญี',
    'วิฤตวิสัญญี': 'หอผู้ป่วยวิกฤตวิสัญญี',
    
    'วิกฤตไฟไหม้': 'หอผู้ป่วยวิกฤตแผลไหม้ (Burn ICU)',
    'วิกฤตไฟไหม้น้ำร้อนลวก': 'หอผู้ป่วยวิกฤตแผลไหม้ (Burn ICU)',
    'วิกฤตไฟไหม้น้ำร้อนล้วก': 'หอผู้ป่วยวิกฤตแผลไหม้ (Burn ICU)',
    'icu-ไฟไหม้': 'หอผู้ป่วยวิกฤตแผลไหม้ (Burn ICU)',
    'ICU.Burn': 'หอผู้ป่วยวิกฤตแผลไหม้ (Burn ICU)',
    
    # --- ระบบประสาท (Neuro / Stroke) ---
    'วิกฤตศัลยกรรมประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'วิิฤตศัลประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'ศ.ประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'ศัลประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'ศัลยกรรมประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'ศัลกรรมระบบประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'ศัลยกรรมระบบประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'S.Neuro': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    'งานการพยาบาลผู้ป่วยวิกฤตศัลยกรรมระบบประสาท': 'หอผู้ป่วยศัลยกรรมระบบประสาท',
    
    'โรคหลอดเลือดสมอง': 'หอผู้ป่วยโรคหลอดเลือดสมอง (Stroke Unit)',
    'โรคหลอดเลือดสมองและระบบประสาท': 'หอผู้ป่วยโรคหลอดเลือดสมอง (Stroke Unit)',
    'โรคหลอกเลือดสมอง': 'หอผู้ป่วยโรคหลอดเลือดสมอง (Stroke Unit)',
    'โรตหลอดเลือดสมองและระบบประสาท': 'หอผู้ป่วยโรคหลอดเลือดสมอง (Stroke Unit)',
    'หลอดเลือดสมอง': 'หอผู้ป่วยโรคหลอดเลือดสมอง (Stroke Unit)',
    
    # --- ห้องพิเศษยูงทอง (Yuangthong Private Wards) ---
    'พิเศษยูงทอง1': 'ห้องพิเศษยูงทอง 1',
    'YT1': 'ห้องพิเศษยูงทอง 1',
    'ยูงทอง 1': 'ห้องพิเศษยูงทอง 1',
    
    'พิเศษยูงทอง2': 'ห้องพิเศษยูงทอง 2',
    'พิเศษยุงทอง2': 'ห้องพิเศษยูงทอง 2',
    'ยูงทอง 2': 'ห้องพิเศษยูงทอง 2',
    'ยูงทอง2': 'ห้องพิเศษยูงทอง 2',
    
    'พิเศษยูงทอง3': 'ห้องพิเศษยูงทอง 3',
    'ยูงทอง 3': 'ห้องพิเศษยูงทอง 3',
    'ยูงทอง3': 'ห้องพิเศษยูงทอง 3',
    
    'พิเศษยูงทอง4': 'ห้องพิเศษยูงทอง 4',
    'พิเศษยููงทอง4': 'ห้องพิเศษยูงทอง 4',
    'ยููงทอง 4': 'ห้องพิเศษยูงทอง 4',
    'ยูงทอง4': 'ห้องพิเศษยูงทอง 4',
    
    'พิเศษยูงทอง5': 'ห้องพิเศษยูงทอง 5',
    'YT5.': 'ห้องพิเศษยูงทอง 5',
    'ยูงทอง5': 'ห้องพิเศษยูงทอง 5',
    
    'พิเศษยูงทอง6': 'ห้องพิเศษยูงทอง 6',
    'ยูงทอง 6': 'ห้องพิเศษยูงทอง 6',
    'ยูงทอง6': 'ห้องพิเศษยูงทอง 6',
    
    'พิเศษยูงทอง': 'ห้องพิเศษยูงทอง',
    
    # --- ห้องพิเศษอาคารดุลโสภาคย์ ---
    'ผู้ป่วยดุล4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'ผู้้ป่วยพิเศษดุล4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'ผู้ป่วยพิเศษดุล4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'พิเศษดุลฯ4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'ดุลฯ4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'พิเศษดุล4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'พิเศษดุุล 4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'DUL 4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'dul 4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    'Dul.4': 'พิเศษอาคารดุลโสภาคย์ ชั้น 4',
    
    'ผู่้ป่วยพิเศษดุล5': 'พิเศษอาคารดุลโสภาคย์ ชั้น 5',
    'พิเศษดุลย์ฯชั้น5': 'พิเศษอาคารดุลโสภาคย์ ชั้น 5',
    
    'พิเศษเฉพาะทาง': 'หอผู้ป่วยพิเศษเฉพาะทาง',
    'VIP': 'หอผู้ป่วย VIP',
    'vip': 'หอผู้ป่วย VIP',
    'VIP ศัลยกรรม2': 'หอผู้ป่วย VIP',
    'VIP ศัล-กระดูก': 'หอผู้ป่วย VIP',
    'หอผู้ป่วยปัญจา': 'หอผู้ป่วยปัญจา',
    'ปํญจา': 'หอผู้ป่วยปัญจา',
    'AY': 'หอผู้ป่วย AY',
    
    # --- ผู้ป่วยนอก (OPD) ---
    'OPD Med1': 'OPD อายุรกรรม 1',
    'OPD.Med1': 'OPD อายุรกรรม 1',
    'opd.med1': 'OPD อายุรกรรม 1',
    'opd M1': 'OPD อายุรกรรม 1',
    'Med1': 'OPD อายุรกรรม 1',
    'อายุรกรรม1(OPD)': 'OPD อายุรกรรม 1',
    'อายุรกรรม1 OPD': 'OPD อายุรกรรม 1',
    'OPD อายุรกรรม 1': 'OPD อายุรกรรม 1',
    'อายุระกรรม1(OPD)': 'OPD อายุรกรรม 1',
    'อายุรกรรม1': 'OPD อายุรกรรม 1',
    
    'OPD Med2': 'OPD อายุรกรรม 2',
    'OPD-MED2': 'OPD อายุรกรรม 2',
    'opd.med2': 'OPD อายุรกรรม 2',
    'MED-2': 'OPD อายุรกรรม 2',
    'OPD M2': 'OPD อายุรกรรม 2',
    'OPD M-2': 'OPD อายุรกรรม 2',
    'opd อายุรกรรม2': 'OPD อายุรกรรม 2',
    'อายุรกรรม2(OPD)': 'OPD อายุรกรรม 2',
    'อายุรกรรม2 OPD': 'OPD อายุรกรรม 2',
    'อายุุรกรรม2(OPD)': 'OPD อายุรกรรม 2',
    'อายุรกรรม2 opd': 'OPD อายุรกรรม 2',
    'อายุรกรรม2opd': 'OPD อายุรกรรม 2',
    
    'OPD GP': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'opd GP': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'OPD-GP': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'GP': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'เวชศาสตร์ทั่วไป': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'เวชศาสตร์ทั่วไปและครอบครัว': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'เวชศาสตร์ทั่วไปและครอบตรัว(OPD)': 'OPD เวชศาสตร์ทั่วไป (GP)',
    'เวชศาสตร์ทั่วไปและครอบครัว OPD': 'OPD เวชศาสตร์ทั่วไป (GP)',
    
    'OPD.Ped': 'OPD กุมารเวชกรรม',
    
    'OPD SUR': 'OPD ศัลยกรรม',
    'ศัลยกรรม OPD': 'OPD ศัลยกรรม',
    'ศัลยกรรม1(OPD)': 'OPD ศัลยกรรม',
    'ศัลยกรรมกระดูกและข้อ(OPD)': 'OPD ศัลยกรรมกระดูกและข้อ',
    
    'นรีเวชกรรม OPD': 'OPD สูติ-นรีเวชกรรม',
    
    'หู คอ จมูก': 'หู คอ จมูก (ENT)',
    'หู คอ จมูก (OPD)': 'หู คอ จมูก (ENT)',
    'หู คอ จมูก OPD': 'หู คอ จมูก (ENT)',
    'หู คอ จมูก ทันตกรรม และศัลยกรรมช่องปาก': 'หู คอ จมูก (ENT)',
    'ENT': 'หู คอ จมูก (ENT)',
    'ENT ': 'หู คอ จมูก (ENT)',
    
    'OPD ปลอดเชื้อ': 'OPD หน่วยตรวจปลอดเชื้อ',
    'ปลอดเชื้อ': 'OPD หน่วยตรวจปลอดเชื้อ',
    'หน่วยตรวจโรคปลอดเชื้อ': 'OPD หน่วยตรวจปลอดเชื้อ',
    
    'โรคติดเชื้อ': 'OPD คลินิกโรคติดเชื้อ',
    'โรคติดเชื้อแพร่กระจายทางอากาศ (OPD)': 'OPD โรคติดเชื้อทางเดินหายใจ',
    
    'OPD OT': 'OPD กิจกรรมบำบัด (OT)',
    'OPD-LAB': 'จุดรับสิ่งส่งตรวจ OPD LAB',
    
    'นอกเวลา': 'คลินิกนอกเวลาราชการ',
    'opd นอกเวลา': 'คลินิกนอกเวลาราชการ',
    'หัตถการและตรวจโรคนอกเวลาราชการ': 'คลินิกนอกเวลาราชการ',
    
    # --- แผนกและศูนย์เฉพาะทาง ---
    'ER': 'อุบัติเหตุและฉุกเฉิน (ER)',
    'er': 'อุบัติเหตุและฉุกเฉิน (ER)',
    'อุบัติเหตุและฉุกเฉิน': 'อุบัติเหตุและฉุกเฉิน (ER)',
    
    'เคมีบำบัด': 'ศูนย์เคมีบำบัด',
    'Cemo': 'ศูนย์เคมีบำบัด',
    'ผู้ป่วยเคมีบำบัดและศูนย์ปลูกถ่ายเซลล์': 'ศูนย์เคมีบำบัดและปลูกถ่ายเซลล์',
    'ผู้ป่วยนอกเคมีบำบัดและหอผู้ป่วยพิเศษเคมี': 'ศูนย์เคมีบำบัด',
    'ผู้ป่วยนอกเคมีบำบัด': 'ศูนย์เคมีบำบัด',
    
    'โรคไตและไตเทียม': 'ศูนย์โรคไตและไตเทียม',
    'ศูนย์์ไตเทียมประสิทธิภาพสูง': 'ศูนย์โรคไตและไตเทียม',
    'opd โรคไตและไตเทียม': 'ศูนย์โรคไตและไตเทียม',
    
    'ผ่าตัดเปลี่ยนข้อ': 'ห้องผ่าตัด (OR)',
    'ผ่่าตัดไม่ค้างคืน': 'ห้องผ่าตัดผู้ป่วยนอก (Day Surgery)',
    
    'THUMC': 'ศูนย์การแพทย์ธรรมศาสตร์',
    'THAMC': 'ศูนย์การแพทย์ธรรมศาสตร์',
    'ศูนย์การแพทย์ธรรมศาสตร์': 'ศูนย์การแพทย์ธรรมศาสตร์',
    'ศูนย์การแพทย์': 'ศูนย์การแพทย์ธรรมศาสตร์',
    
    'จักษุ': 'จักษุวิทยา (OPD Eye)',
    'Eye Dul 6': 'จักษุวิทยา (OPD Eye)',
    
    'รังสีร่วมรักษา': 'ศูนย์รังสีร่วมรักษา',
    'ศูนย์โรคหัวใจและหลอดเลือด': 'ศูนย์โรคหัวใจและหลอดเลือด',
    'ศูนย์โรคผิวหนัง': 'ศูนย์โรคผิวหนัง',
    'ปลูกถ่ายอวัยวะ': 'ศูนย์ปลูกถ่ายอวัยวะ',
    'ศูนย์รวมใจรักษ์': 'ศูนย์รวมใจรักษ์ (Palliative Care)',
    'ส่องกล้อง': 'หน่วยส่องกล้อง (Endoscopy)',
}

# Grouping standardized wards into major clinical departments
WARD_GROUPS = {
    # อายุรกรรม
    'อายุรกรรมชายสามัญ': 'อายุรกรรม (Medicine)',
    'อายุรกรรมชายพิเศษ': 'อายุรกรรม (Medicine)',
    'อายุรกรรมหญิงสามัญ': 'อายุรกรรม (Medicine)',
    'อายุรกรรมหญิงพิเศษ': 'อายุรกรรม (Medicine)',
    'อายุรกรรมกิตติวัฒนา': 'อายุรกรรม (Medicine)',
    'อายุรกรรมความดันลบ': 'อายุรกรรม (Medicine)',
    'อายุรกรรมทั่วไป': 'อายุรกรรม (Medicine)',
    
    # ศัลยกรรม
    'ศัลยกรรม 1': 'ศัลยกรรม (Surgery)',
    'ศัลยกรรม 2': 'ศัลยกรรม (Surgery)',
    'ศัลยกรรม 3': 'ศัลยกรรม (Surgery)',
    'ศัลยกรรมพิเศษ 1': 'ศัลยกรรม (Surgery)',
    'ศัลยกรรมพิเศษ 2': 'ศัลยกรรม (Surgery)',
    'ศัลยกรรมพิเศษ': 'ศัลยกรรม (Surgery)',
    
    # ศัลยกรรมกระดูก
    'ศัลยกรรมกระดูกและข้อสามัญ': 'ศัลยกรรมกระดูก (Orthopedics)',
    'ศัลยกรรมกระดูกและข้อพิเศษ': 'ศัลยกรรมกระดูก (Orthopedics)',
    
    # กุมารเวชกรรม
    'กุมารเวชกรรม 1': 'กุมารเวชกรรม (Pediatrics)',
    'กุมารเวชกรรม 2': 'กุมารเวชกรรม (Pediatrics)',
    'กุมารเวชกรรมพิเศษ': 'กุมารเวชกรรม (Pediatrics)',
    
    # สูติ-นรีเวชกรรม
    'สูติ-นรีเวชกรรมสามัญ': 'สูติ-นรีเวชกรรม (OB-GYN)',
    'สูติ-นรีเวชกรรมพิเศษ': 'สูติ-นรีเวชกรรม (OB-GYN)',
    'ห้องคลอด (LR)': 'สูติ-นรีเวชกรรม (OB-GYN)',
    
    # ผู้ป่วยวิกฤต (ICU)
    'หอผู้ป่วยวิกฤตอายุรกรรม (MICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตศัลยกรรม (SICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตศัลยกรรมหัวใจและทรวงอก (CVT ICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตระบบการหายใจ (RICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตโรคหัวใจ (CCU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยทารกแรกเกิดวิกฤต (NICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตกุมารเวชกรรม (PICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตวิสัญญี': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    'หอผู้ป่วยวิกฤตแผลไหม้ (Burn ICU)': 'ผู้ป่วยวิกฤต (Critical Care / ICU)',
    
    # ระบบประสาท
    'หอผู้ป่วยศัลยกรรมระบบประสาท': 'ระบบประสาท (Neuro / Stroke)',
    'หอผู้ป่วยโรคหลอดเลือดสมอง (Stroke Unit)': 'ระบบประสาท (Neuro / Stroke)',
    
    # ห้องผู้ป่วยพิเศษ
    'ห้องพิเศษยูงทอง 1': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'ห้องพิเศษยูงทอง 2': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'ห้องพิเศษยูงทอง 3': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'ห้องพิเศษยูงทอง 4': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'ห้องพิเศษยูงทอง 5': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'ห้องพิเศษยูงทอง 6': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'ห้องพิเศษยูงทอง': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'พิเศษอาคารดุลโสภาคย์ ชั้น 4': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'พิเศษอาคารดุลโสภาคย์ ชั้น 5': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'หอผู้ป่วยพิเศษเฉพาะทาง': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'หอผู้ป่วย VIP': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'หอผู้ป่วยปัญจา': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    'หอผู้ป่วย AY': 'ห้องผู้ป่วยพิเศษ (Private Wards)',
    
    # ผู้ป่วยนอก (OPD)
    'OPD อายุรกรรม 1': 'ผู้ป่วยนอก (OPD)',
    'OPD อายุรกรรม 2': 'ผู้ป่วยนอก (OPD)',
    'OPD เวชศาสตร์ทั่วไป (GP)': 'ผู้ป่วยนอก (OPD)',
    'OPD กุมารเวชกรรม': 'ผู้ป่วยนอก (OPD)',
    'OPD ศัลยกรรม': 'ผู้ป่วยนอก (OPD)',
    'OPD ศัลยกรรมกระดูกและข้อ': 'ผู้ป่วยนอก (OPD)',
    'OPD สูติ-นรีเวชกรรม': 'ผู้ป่วยนอก (OPD)',
    'หู คอ จมูก (ENT)': 'ผู้ป่วยนอก (OPD)',
    'OPD หน่วยตรวจปลอดเชื้อ': 'ผู้ป่วยนอก (OPD)',
    'OPD คลินิกโรคติดเชื้อ': 'ผู้ป่วยนอก (OPD)',
    'OPD โรคติดเชื้อทางเดินหายใจ': 'ผู้ป่วยนอก (OPD)',
    'OPD กิจกรรมบำบัด (OT)': 'ผู้ป่วยนอก (OPD)',
    'จุดรับสิ่งส่งตรวจ OPD LAB': 'ผู้ป่วยนอก (OPD)',
    'คลินิกนอกเวลาราชการ': 'ผู้ป่วยนอก (OPD)',
    'จักษุวิทยา (OPD Eye)': 'ผู้ป่วยนอก (OPD)',
    
    # ฉุกเฉิน & ศูนย์เฉพาะทางอื่นๆ
    'อุบัติเหตุและฉุกเฉิน (ER)': 'อุบัติเหตุและฉุกเฉิน (ER)',
    'ศูนย์เคมีบำบัด': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ศูนย์เคมีบำบัดและปลูกถ่ายเซลล์': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ศูนย์โรคไตและไตเทียม': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ห้องผ่าตัด (OR)': 'ห้องผ่าตัด/วิสัญญี',
    'ห้องผ่าตัดผู้ป่วยนอก (Day Surgery)': 'ห้องผ่าตัด/วิสัญญี',
    'ศูนย์การแพทย์ธรรมศาสตร์': 'ศูนย์การแพทย์ธรรมศาสตร์',
    'ศูนย์รังสีร่วมรักษา': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ศูนย์โรคหัวใจและหลอดเลือด': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ศูนย์โรคผิวหนัง': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ศูนย์ปลูกถ่ายอวัยวะ': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'ศูนย์รวมใจรักษ์ (Palliative Care)': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
    'หน่วยส่องกล้อง (Endoscopy)': 'ศูนย์ความเป็นเลิศ/เฉพาะทาง',
}

# Standard Category Labels
CATEGORY_LABELS = {
    'สิ่งส่งตรวจ': 'ปัญหาด้านสิ่งส่งตรวจ',
    'ใบส่งตรวจ': 'ปัญหาด้านใบส่งตรวจ',
    'ระบบจ่ายเงิน': 'ปัญหาด้านระบบการเงิน',
    'ระบบสารสนเทศ': 'ปัญหาด้านระบบสารสนเทศ',
    'อื่น ๆ': 'ปัญหาอื่นๆ / รายละเอียดเพิ่มเติม',
}


# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def standardize_ward(ward_raw: str) -> tuple[str, str]:
    """
    Standardize raw ward string. Returns (standard_name, ward_group).
    """
    if not isinstance(ward_raw, str) or not ward_raw.strip():
        return 'ไม่ระบุหอผู้ป่วย', 'ไม่ระบุกลุ่ม'
    
    cleaned = ward_raw.strip()

    # Repeated Thai vowel/tone marks are typing errors that look almost
    # identical on screen but otherwise create a separate Ward in charts.
    # For example, "อายุุรกรรมหญิงสามัญ" must join "อายุรกรรมหญิงสามัญ".
    cleaned = re.sub(r'([\u0e31\u0e34-\u0e3a\u0e47-\u0e4e])\1+', r'\1', cleaned)
    
    # Direct dictionary lookup
    if cleaned in WARD_MAPPING:
        std = WARD_MAPPING[cleaned]
        grp = WARD_GROUPS.get(std, 'อื่น ๆ')
        return std, grp
    
    # Case-insensitive / normalized search
    lower_cleaned = cleaned.lower()
    for raw_k, std_v in WARD_MAPPING.items():
        if raw_k.lower() == lower_cleaned:
            grp = WARD_GROUPS.get(std_v, 'อื่น ๆ')
            return std_v, grp
            
    # Fuzzy heuristic fallbacks
    if 'ยูงทอง' in cleaned:
        std = 'ห้องพิเศษยูงทอง'
        return std, 'ห้องผู้ป่วยพิเศษ (Private Wards)'
    if 'ดุล' in cleaned:
        std = 'พิเศษอาคารดุลโสภาคย์'
        return std, 'ห้องผู้ป่วยพิเศษ (Private Wards)'
    if 'er' in lower_cleaned or 'ฉุกเฉิน' in cleaned:
        return 'อุบัติเหตุและฉุกเฉิน (ER)', 'อุบัติเหตุและฉุกเฉิน (ER)'
    if 'ic' in lower_cleaned or 'วิกฤต' in cleaned:
        return cleaned, 'ผู้ป่วยวิกฤต (Critical Care / ICU)'
    if 'opd' in lower_cleaned:
        return cleaned, 'ผู้ป่วยนอก (OPD)'

    return cleaned, 'อื่น ๆ'


def parse_sheet_month(sheet_name: str) -> tuple[int | None, int | None, str | None]:
    """
    Parse month and year from sheet name (e.g. 'ต.ค. 68', 'ม.ค.69').
    Returns (month, year_ce, label_thai)
    e.g. ('ต.ค. 68') -> (10, 2025, 'ต.ค. 2568')
    """
    match = MONTH_SHEET_PATTERN.fullmatch(sheet_name.strip())
    if match is None:
        return None, None, None

    month = THAI_MONTHS[match.group('month')]
    year = int(match.group('year'))
    if year < 100:  # Two-digit Buddhist year, e.g. 69 -> 2569.
        year_be = 2500 + year
    elif 2400 <= year <= 2700:
        year_be = year
    elif 1900 <= year <= 2100:
        year_be = year + 543
    else:
        return None, None, None

    year_ce = year_be - 543
    return month, year_ce, f"{THAI_MONTH_NAMES_SHORT[month]} {year_be}"


def find_header_row(df_raw: pd.DataFrame) -> int | None:
    """
    Search up to top 35 rows to locate header row containing key columns.
    """
    for idx in range(min(35, len(df_raw))):
        row_vals = [str(x).strip() for x in df_raw.iloc[idx].values if pd.notna(x)]
        row_text = " ".join(row_vals)
        # Require the date/time/HN header group so the document title (which
        # also contains the words "สิ่งส่งตรวจ") is not mistaken for a header.
        if (('วันที่' in row_text or 'Day' in row_text)
                and ('เวลา' in row_text or 'Time' in row_text or 'HN' in row_text)
                and ('Ward' in row_text or 'หอผู้ป่วย' in row_text or 'สภาพปัญหา' in row_text or 'สิ่งส่งตรวจ' in row_text)):
            return idx
    return None


def read_excel_sheet_data(xl: pd.ExcelFile, sheet_name: str) -> tuple[pd.DataFrame, int]:
    """Read a sheet while supporting the two-row merged headers in monthly tabs."""
    df_raw = xl.parse(sheet_name, header=None)
    if df_raw.empty:
        return pd.DataFrame(), -1
    h_idx = find_header_row(df_raw)
    if h_idx is None:
        raise ValueError(f"ชีท '{sheet_name}' ไม่มีหัวตาราง วันที่/เวลา/Ward ที่ระบบอ่านได้")
    header_values = [str(value).strip() if pd.notna(value) else '' for value in df_raw.iloc[h_idx].tolist()]

    # Monthly tabs place Ward and the five issue groups on the row below the
    # date/time/HN row. Overlay that row onto the first header row before
    # reading data, which keeps the correct column positions after merges.
    if h_idx + 1 < len(df_raw):
        second_values = [str(value).strip() if pd.notna(value) else '' for value in df_raw.iloc[h_idx + 1].tolist()]
        second_text = ' '.join(second_values)
        if 'Ward' in second_text and ('สิ่งส่งตรวจ' in second_text or 'ใบส่งตรวจ' in second_text):
            header_values = [lower or upper for upper, lower in zip(header_values, second_values)]
            df_data = xl.parse(sheet_name, skiprows=h_idx + 2, header=None)
            # Keep a stable name for blank/extra columns; process_dataframe_rows
            # only maps the semantic headers above.
            if len(header_values) < len(df_data.columns):
                header_values.extend([''] * (len(df_data.columns) - len(header_values)))
            df_data.columns = header_values[:len(df_data.columns)]
            return df_data, h_idx

    df_data = xl.parse(sheet_name, skiprows=h_idx)
    df_data.columns = [str(c).strip() for c in df_data.columns]
    return df_data, h_idx


def _parse_period_value(value) -> tuple[str | None, str | None]:
    """Return ISO year-month and Thai label from a denominator period cell."""
    if pd.isna(value):
        return None, None
    text = str(value).strip()
    if not text or text in {'nan', 'None', '-'}:
        return None, None
    parsed = parse_sheet_month(text)
    if parsed[0] is not None:
        month, year_ce, label = parsed
        return f'{year_ce:04d}-{month:02d}', label
    match = re.fullmatch(r'(\d{4})[-/]([01]?\d)', text)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            year_ce = year - 543 if year >= 2400 else year
            return f'{year_ce:04d}-{month:02d}', f'{THAI_MONTH_NAMES_SHORT[month]} {year_ce + 543}'
    parsed_date = pd.to_datetime(value, errors='coerce')
    if not pd.isna(parsed_date):
        return f'{parsed_date.year:04d}-{parsed_date.month:02d}', f'{THAI_MONTH_NAMES_SHORT[parsed_date.month]} {parsed_date.year + 543}'
    return None, None


def _read_denominator_sheets(xl: pd.ExcelFile, sheet_names: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Read optional monthly totals used as the denominator of rejection rate."""
    records = []
    warnings = []
    found_sheet_names = []
    for sheet_name in sheet_names:
        name_lower = sheet_name.strip().lower()
        if not any(marker.lower() in name_lower for marker in DENOMINATOR_SHEET_MARKERS):
            continue
        found_sheet_names.append(sheet_name)
        raw = xl.parse(sheet_name, header=None)
        if raw.empty:
            warnings.append(f"ชีทตัวหาร '{sheet_name}' ยังไม่มีข้อมูล")
            continue
        header_idx = None
        for idx in range(min(20, len(raw))):
            row_text = ' '.join(str(v).strip().lower() for v in raw.iloc[idx].tolist() if pd.notna(v))
            has_period = any(token in row_text for token in ['เดือน', 'month', 'ปี', 'year', 'งวด'])
            has_total = any(token in row_text for token in ['จำนวนสิ่งส่งตรวจทั้งหมด', 'ยอดตรวจ', 'ตัวหาร', 'total specimen', 'total sample', 'จำนวนทั้งหมด'])
            if has_period and has_total:
                header_idx = idx
                break
        if header_idx is None:
            warnings.append(f"ชีทตัวหาร '{sheet_name}' ต้องมีคอลัมน์ เดือน และ จำนวนสิ่งส่งตรวจทั้งหมด")
            continue

        table = raw.iloc[header_idx + 1:].copy()
        headers = [str(v).strip() if pd.notna(v) else '' for v in raw.iloc[header_idx].tolist()]
        table.columns = headers[:len(table.columns)]
        period_col = next((c for c in table.columns if any(token in str(c).lower() for token in ['เดือน', 'month', 'งวด', 'year_month'])), None)
        total_col = next((c for c in table.columns if any(token in str(c).lower() for token in ['จำนวนสิ่งส่งตรวจทั้งหมด', 'ยอดตรวจ', 'ตัวหาร', 'total specimen', 'total sample', 'จำนวนทั้งหมด'])), None)
        ward_col = next((c for c in table.columns if 'ward' in str(c).lower() or 'หอผู้ป่วย' in str(c).lower()), None)
        source_col = next((c for c in table.columns if 'แหล่งข้อมูล' in str(c).lower() or 'data source' in str(c).lower()), None)
        if period_col is None or total_col is None:
            warnings.append(f"ชีทตัวหาร '{sheet_name}' ต้องมีคอลัมน์ เดือน และ จำนวนสิ่งส่งตรวจทั้งหมด")
            continue
        # The old auto-generated tab counts rejected rows. Accept a dedicated
        # real-totals tab or rows explicitly marked as LIS data only.
        dedicated_lis_sheet = 'ยอดตรวจจริง' in name_lower
        if not dedicated_lis_sheet and source_col is None:
            warnings.append(f"ชีทตัวหาร '{sheet_name}' ไม่มีคอลัมน์แหล่งข้อมูล; ข้ามยอดที่อาจนับจากเคสปฏิเสธ")
            continue
        for _, row in table.iterrows():
            if not dedicated_lis_sheet:
                source = str(row.get(source_col, '')).strip().lower()
                if source not in {'lis', 'ระบบห้องปฏิบัติการ', 'laboratory information system'}:
                    continue
            year_month, thai_label = _parse_period_value(row.get(period_col))
            total = pd.to_numeric(str(row.get(total_col, '')).replace(',', '').strip(), errors='coerce')
            if year_month is None or pd.isna(total) or float(total) <= 0:
                continue
            ward_raw = str(row.get(ward_col, '')).strip() if ward_col is not None else ''
            ward_standard = standardize_ward(ward_raw)[0] if ward_raw and ward_raw not in {'nan', 'None'} else ''
            records.append({
                'year_month': year_month,
                'thai_month_year': thai_label,
                'ward_standard': ward_standard,
                'total_specimens': float(total),
                'source_sheet': sheet_name,
            })
    if not records:
        empty = pd.DataFrame(columns=['year_month', 'thai_month_year', 'ward_standard', 'total_specimens', 'source_sheet'])
        empty.attrs['sheet_names'] = found_sheet_names
        return empty, warnings
    denominator = pd.DataFrame(records)
    denominator['total_specimens'] = denominator['total_specimens'].astype(float)
    denominator.attrs['sheet_names'] = found_sheet_names
    return denominator, warnings


# ==============================================================================
# 3. CORE DATA INGESTION & NORMALIZATION
# ==============================================================================

def process_dataframe_rows(df: pd.DataFrame, default_month: int = None, default_year: int = None, default_label: str = None) -> pd.DataFrame:
    """
    Clean and normalize raw dataframe table.
    """
    # Standard column mapping
    col_map = {}
    for c in df.columns:
        c_str = str(c).strip()
        if 'วันที่' in c_str:
            col_map[c] = 'day'
        elif 'เวลา' in c_str:
            col_map[c] = 'time'
        elif 'HN' in c_str or 'hn' in c_str:
            col_map[c] = 'hn'
        elif 'Ward' in c_str or 'หอผู้ป่วย' in c_str:
            col_map[c] = 'ward_raw'
        elif 'สิ่งส่งตรวจ' in c_str:
            col_map[c] = 'specimen_issue'
        elif 'ใบส่งตรวจ' in c_str:
            col_map[c] = 'request_issue'
        elif 'ระบบจ่ายเงิน' in c_str or 'การเงิน' in c_str:
            col_map[c] = 'payment_issue'
        elif 'ระบบสารสนเทศ' in c_str or 'LIS' in c_str:
            col_map[c] = 'it_issue'
        elif 'อื่น ๆ' in c_str or 'อื่นๆ' in c_str or 'รายละเอียด' in c_str:
            col_map[c] = 'other_issue'
        elif 'ผู้รับเรื่อง' in c_str:
            col_map[c] = 'receiver'
        elif 'สถานะ' in c_str:
            col_map[c] = 'status'
        elif 'หลักฐาน' in c_str:
            col_map[c] = 'evidence'
        elif 'ผู้รายงาน' in c_str:
            col_map[c] = 'reporter'
        elif 'การติดตาม' in c_str:
            col_map[c] = 'followup'
        elif 'การแก้ไข' in c_str:
            col_map[c] = 'resolution'
        elif 'ผู้ติดตาม' in c_str:
            col_map[c] = 'follower'
        elif 'หัวหน้างาน' in c_str:
            col_map[c] = 'supervisor'

    df = df.rename(columns=col_map)

    # Some monthly sheets contain the same header twice (for example two
    # "สถานะ" columns). Pandas then returns a DataFrame for ``df[col]`` and
    # string operations fail. Coalesce duplicate columns by keeping the first
    # non-empty value in each row before the required-column checks below.
    if df.columns.duplicated().any():
        merged_columns = {}
        for position, column_name in enumerate(df.columns):
            series = df.iloc[:, position]
            if column_name not in merged_columns:
                merged_columns[column_name] = series.copy()
                continue
            existing = merged_columns[column_name]
            empty = existing.isna() | existing.astype(str).str.strip().isin(['', 'nan', 'None'])
            merged_columns[column_name] = existing.where(~empty, series)
        df = pd.DataFrame(merged_columns, index=df.index)
    
    # Ensure mandatory columns exist
    for req_col in ['day', 'time', 'hn', 'ward_raw', 'specimen_issue', 'request_issue',
                    'payment_issue', 'it_issue', 'other_issue', 'receiver', 'status',
                    'evidence', 'reporter', 'followup', 'resolution', 'follower', 'supervisor']:
        if req_col not in df.columns:
            df[req_col] = ''

    # Filter out empty or header-like rows
    def is_valid_row(r):
        day_val = str(r['day']).strip()
        ward_val = str(r['ward_raw']).strip()
        has_ward = ward_val not in ['', 'nan', 'None']
        if day_val in ['วันที่', 'Day']:
            return False
        # Must have at least some date or ward or issue
        has_issue = any(str(r[c]).strip() not in ['', 'nan', 'None'] for c in ['specimen_issue', 'request_issue', 'payment_issue', 'it_issue', 'other_issue'])
        if day_val in ['', 'nan', 'None']:
            # Keep incomplete records so the date audit can report them.
            has_identity = any(str(r[c]).strip() not in ['', 'nan', 'None'] for c in ['hn', 'time'])
            return bool(has_ward and (has_issue or has_identity))
        return bool(has_ward or has_issue)

    valid_mask = df.apply(is_valid_row, axis=1)
    df = df[valid_mask].copy()

    # Clean text values
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().replace({'nan': '', 'None': ''})

    # Standardize Ward
    ward_res = df['ward_raw'].apply(standardize_ward)
    df['ward_standard'] = [w[0] for w in ward_res]
    df['ward_group'] = [w[1] for w in ward_res]

    # Process Day, Month, Year
    # If default_month and default_year are given (from monthly sheet), use them
    # Otherwise infer by day reset or context clues
    cur_m = default_month or 10
    cur_y = default_year or 2025
    prev_d = -1
    
    dates = []
    year_months = []
    thai_labels = []
    fiscal_quarters = []
    fiscal_year_labels = []
    valid_dates = []

    for idx, row in df.iterrows():
        raw_d = row['day']
        try:
            d_numeric = float(raw_d)
            d_int = int(d_numeric)
            day_is_integer = d_numeric.is_integer()
        except (TypeError, ValueError, OverflowError):
            d_int = 1
            day_is_integer = False
        
        # If this is a consolidated file without pre-assigned sheet month,
        # detect month transitions when day drops significantly
        if default_month is None:
            if day_is_integer and prev_d > 0 and d_int < prev_d:
                # Month advances
                cur_m += 1
                if cur_m > 12:
                    cur_m = 1
                    cur_y += 1
            if day_is_integer:
                prev_d = d_int
        
        max_days = [0, 31, 29 if cur_y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        date_is_valid = day_is_integer and 1 <= d_int <= max_days[cur_m]
        date_iso = f"{cur_y:04d}-{cur_m:02d}-{d_int:02d}" if date_is_valid else None
        ym_str = f"{cur_y:04d}-{cur_m:02d}"
        be_y = cur_y + 543
        th_label = f"{THAI_MONTH_NAMES_SHORT[cur_m]} {be_y}"
        
        # Thai Fiscal Year Quarter:
        # Q1: ต.ค.-ธ.ค. (Months 10, 11, 12)
        # Q2: ม.ค.-มี.ค. (Months 1, 2, 3)
        # Q3: เม.ย.-มิ.ย. (Months 4, 5, 6)
        # Q4: ก.ค.-ก.ย. (Months 7, 8, 9)
        if cur_m in [10, 11, 12]:
            q_str = f"Q1/{be_y+1}"
        elif cur_m in [1, 2, 3]:
            q_str = f"Q2/{be_y}"
        elif cur_m in [4, 5, 6]:
            q_str = f"Q3/{be_y}"
        else:
            q_str = f"Q4/{be_y}"

        fiscal_year = be_y + 1 if cur_m >= 10 else be_y

        dates.append(date_iso)
        year_months.append(ym_str)
        thai_labels.append(th_label)
        fiscal_quarters.append(q_str)
        fiscal_year_labels.append(f"ปีงบประมาณ {fiscal_year}")
        valid_dates.append(date_is_valid)

    df['date'] = dates
    df['year_month'] = year_months
    df['thai_month_year'] = thai_labels
    df['fiscal_quarter'] = fiscal_quarters
    df['fiscal_year'] = fiscal_year_labels
    df['date_valid'] = valid_dates

    # Clean status, followup, and resolution
    df['status'] = df['status'].replace({'': 'รอตรวจสอบ'})
    df['followup'] = df['followup'].replace({'': 'ติดตามแล้ว'})
    df['resolution'] = df['resolution'].replace({'': 'แก้ไขแล้ว'})
    
    # Tag incidents
    df['is_incident'] = df['supervisor'].str.contains('อุบัติการณ์', na=False) | \
                        df['resolution'].str.contains('อุบัติการณ์', na=False) | \
                        df['other_issue'].str.contains('อุบัติการณ์', na=False)

    # Classify Specimen Type
    def classify_specimen_type(r):
        text = f"{r.get('specimen_issue', '')} {r.get('request_issue', '')} {r.get('other_issue', '')}".lower()
        if any(k in text for k in ['hemo', 'h/c', 'เลือด', 'blood', 'c-line']):
            return 'เลือด (Blood / Hemo)'
        elif any(k in text for k in ['sputum', 'เสมหะ', 'afb', 'tb', 'tracheal']):
            return 'เสมหะ / ทางเดินหายใจ (Sputum)'
        elif any(k in text for k in ['urine', 'ปัสสาวะ', 'uc', 'u/c', 'msu']):
            return 'ปัสสาวะ (Urine)'
        elif any(k in text for k in ['stool', 'อุจจาระ', 'rectal']):
            return 'อุจจาระ (Stool)'
        elif any(k in text for k in ['pus', 'swab', 'หนอง', 'แผล', 'slide', 'slied']):
            return 'หนอง / ป้ายแผล (Pus / Swab)'
        elif any(k in text for k in ['fluid', 'synovial', 'peritoneal', 'csf', 'น้ำ']):
            return 'สารน้ำ / CSF (Body Fluid)'
        elif any(k in text for k in ['tissue', 'ชิ้นเนื้อ', 'เนื้อ']):
            return 'ชิ้นเนื้อ (Tissue)'
        else:
            return 'อื่น ๆ / ไม่ระบุชัดเจน'

    # Classify Risk Level
    def classify_risk_level(r):
        if r.get('is_incident', False) or 'อุบัติการณ์' in str(r.get('supervisor', '')):
            return '🚨 ความเสี่ยงสูง / อุบัติการณ์'
        elif str(r.get('resolution', '')) in ['แก้ไขไม่ได้', 'ยกเลิก', 'ขอยกเลิก']:
            return '⚠️ ความเสี่ยงปานกลาง (แก้ไขไม่ได้/ยกเลิก)'
        else:
            return '✅ ความเสี่ยงต่ำ (แก้ไขได้)'

    df['specimen_type'] = df.apply(classify_specimen_type, axis=1)
    df['risk_level'] = df.apply(classify_risk_level, axis=1)

    return df


def load_and_consolidate(file_source) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ingest Excel (all monthly sheets) or CSV file.
    Returns:
      df_cases: Case-level DataFrame (1 row per rejection transaction)
      df_causes: Cause-level Tidy DataFrame (unpivoted, 1 row per rejection reason)
    """
    all_dfs = []
    
    # Check if file_source is str or file-like buffer
    is_excel = False
    is_csv = False

    if isinstance(file_source, str):
        if file_source.endswith('.xlsx') or file_source.endswith('.xls'):
            is_excel = True
        elif file_source.endswith('.csv'):
            is_csv = True
    else:
        # Buffer
        fname = getattr(file_source, 'name', '').lower()
        if fname.endswith('.xlsx') or fname.endswith('.xls'):
            is_excel = True
        elif fname.endswith('.csv'):
            is_csv = True
        else:
            # Try excel first
            is_excel = True

    if is_excel:
        xl = pd.ExcelFile(file_source)
        all_sheet_names = xl.sheet_names
        
        # A new monthly tab is discovered on every reload. Only complete month
        # and year names are accepted so a yearless tab cannot be misdated.
        monthly_sheets = []
        ingestion_warnings = []
        has_month_like_tabs = False
        denominator, denominator_warnings = _read_denominator_sheets(xl, all_sheet_names)
        denominator_sheet_found = bool(denominator.attrs.get('sheet_names', []))
        ingestion_warnings.extend(denominator_warnings)
        for s in all_sheet_names:
            if s.strip() in ['สรุป', 'Summary', 'All', 'Sheet1', 'sheet1']:
                continue
            m, y, lbl = parse_sheet_month(s)
            if m is not None:
                has_month_like_tabs = True
                monthly_sheets.append((s, m, y, lbl))
            elif any(s.strip().startswith(name) for name in THAI_MONTHS):
                has_month_like_tabs = True
                ingestion_warnings.append("ข้ามชีทรายเดือนที่ชื่อไม่ครบ: ตั้งชื่อเป็นเดือนและปี เช่น ต.ค. 69")

        if monthly_sheets:
            # Sheet order may change when staff copy or drag a new tab.
            monthly_sheets.sort(key=lambda item: (item[2], item[1], item[0]))
            seen_months = set()
            for s_name, m_num, y_num, m_lbl in monthly_sheets:
                month_key = (y_num, m_num)
                if month_key in seen_months:
                    ingestion_warnings.append(f"พบหลายชีทสำหรับ {m_lbl}; ระบบรวมข้อมูลจากทุกชีท โปรดตรวจข้อมูลซ้ำ")
                seen_months.add(month_key)
                try:
                    df_data, h_idx = read_excel_sheet_data(xl, s_name)
                except ValueError as exc:
                    ingestion_warnings.append(str(exc))
                    continue
                if df_data.empty:
                    continue
                processed_df = process_dataframe_rows(df_data, default_month=m_num, default_year=y_num, default_label=m_lbl)
                if processed_df.empty:
                    continue
                processed_df['source_sheet'] = s_name
                all_dfs.append(processed_df)
        elif not has_month_like_tabs:
            # Read from default/first sheet (e.g. 'สรุป')
            target_sheet = 'สรุป' if 'สรุป' in all_sheet_names else all_sheet_names[0]
            df_data, h_idx = read_excel_sheet_data(xl, target_sheet)
            processed_df = process_dataframe_rows(df_data)
            processed_df['source_sheet'] = target_sheet
            all_dfs.append(processed_df)

    else:
        # CSV file
        try:
            df_raw = pd.read_csv(file_source, header=None, encoding='utf-8')
        except:
            if hasattr(file_source, 'seek'):
                file_source.seek(0)
            df_raw = pd.read_csv(file_source, header=None, encoding='cp874')
            
        h_idx = find_header_row(df_raw) or 0
        if hasattr(file_source, 'seek'):
            file_source.seek(0)
        try:
            df_data = pd.read_csv(file_source, skiprows=h_idx, encoding='utf-8')
        except:
            if hasattr(file_source, 'seek'):
                file_source.seek(0)
            df_data = pd.read_csv(file_source, skiprows=h_idx, encoding='cp874')
            
        df_data.columns = [str(c).strip() for c in df_data.columns]
        processed_df = process_dataframe_rows(df_data)
        processed_df['source_sheet'] = 'CSV Data'
        all_dfs.append(processed_df)

    # Combine all
    if not all_dfs:
        empty_cases, empty_causes = pd.DataFrame(), pd.DataFrame()
        empty_cases.attrs['ingestion_warnings'] = ingestion_warnings if is_excel else []
        empty_cases.attrs['denominator'] = denominator if is_excel else pd.DataFrame()
        empty_cases.attrs['denominator_sheet_found'] = denominator_sheet_found if is_excel else False
        return empty_cases, empty_causes

    df_cases = pd.concat(all_dfs, ignore_index=True)
    df_cases['case_id'] = [f"REJ-{i+1:04d}" for i in range(len(df_cases))]

    # Unpivot causes into Tidy format
    df_causes = unpivot_causes(df_cases)

    df_cases.attrs['ingestion_warnings'] = ingestion_warnings if is_excel else []
    df_cases.attrs['denominator'] = denominator if is_excel else pd.DataFrame()
    df_cases.attrs['denominator_sheet_found'] = denominator_sheet_found if is_excel else False

    return df_cases, df_causes


def unpivot_causes(df_cases: pd.DataFrame) -> pd.DataFrame:
    """
    Unpivots the 5 rejection cause columns:
      - สิ่งส่งตรวจ
      - ใบส่งตรวจ
      - ระบบจ่ายเงิน
      - ระบบสารสนเทศ
      - อื่น ๆ
    Into a normalized Tidy DataFrame where each row represents one distinct rejection cause.
    """
    cause_rows = []
    
    cause_cols = [
        ('specimen_issue', 'ปัญหาด้านสิ่งส่งตรวจ'),
        ('request_issue', 'ปัญหาด้านใบส่งตรวจ'),
        ('payment_issue', 'ปัญหาด้านระบบการเงิน'),
        ('it_issue', 'ปัญหาด้านระบบสารสนเทศ'),
    ]

    for _, row in df_cases.iterrows():
        base_info = {
            'case_id': row['case_id'],
            'date': row['date'],
            'time': row['time'],
            'year_month': row['year_month'],
            'thai_month_year': row['thai_month_year'],
            'fiscal_quarter': row['fiscal_quarter'],
            'fiscal_year': row['fiscal_year'],
            'hn': row['hn'],
            'ward_raw': row['ward_raw'],
            'ward_standard': row['ward_standard'],
            'ward_group': row['ward_group'],
            'receiver': row['receiver'],
            'status': row['status'],
            'evidence': row['evidence'],
            'reporter': row['reporter'],
            'followup': row['followup'],
            'resolution': row['resolution'],
            'follower': row['follower'],
            'supervisor': row['supervisor'],
            'is_incident': row['is_incident'],
            'specimen_type': row.get('specimen_type', 'อื่น ๆ / ไม่ระบุชัดเจน'),
            'risk_level': row.get('risk_level', '✅ ความเสี่ยงต่ำ (แก้ไขได้)'),
            'notes': row['other_issue']
        }
        
        found_any = False
        
        # Check standard 4 categories
        for col_name, cat_label in cause_cols:
            val = str(row.get(col_name, '')).strip()
            if val and val not in ['', 'nan', 'None', '-']:
                # Split multiple causes separated by comma or semicolon if present
                sub_reasons = [x.strip() for x in re.split(r'[,;/\n]', val) if x.strip()]
                for sr in sub_reasons:
                    entry = base_info.copy()
                    entry['category'] = cat_label
                    entry['reason'] = sr
                    cause_rows.append(entry)
                    found_any = True

        # Check 'other_issue' (อื่น ๆ)
        other_val = str(row.get('other_issue', '')).strip()
        if other_val and other_val not in ['', 'nan', 'None', '-']:
            # If no primary cause was marked in the 4 columns, classify other_issue
            if not found_any:
                cat_label = 'ปัญหาอื่นๆ / รายละเอียดเพิ่มเติม'
                if 'สไลด์' in other_val or 'Slide' in other_val or 'สิ่งส่งตรวจ' in other_val or 'หลอด' in other_val or 'ขวด' in other_val or 'กระปุก' in other_val:
                    cat_label = 'ปัญหาด้านสิ่งส่งตรวจ'
                elif 'Request' in other_val or 'ใบ' in other_val or 'คีย์' in other_val or 'ระบบ E-phis' in other_val:
                    cat_label = 'ปัญหาด้านใบส่งตรวจ'
                elif 'จ่ายเงิน' in other_val or 'การเงิน' in other_val or 'ชำระ' in other_val:
                    cat_label = 'ปัญหาด้านระบบการเงิน'
                elif 'LIS' in other_val:
                    cat_label = 'ปัญหาด้านระบบสารสนเทศ'

                entry = base_info.copy()
                entry['category'] = cat_label
                entry['reason'] = other_val[:80] + ('...' if len(other_val) > 80 else '')
                cause_rows.append(entry)
                found_any = True
                
        # If completely empty
        if not found_any:
            entry = base_info.copy()
            entry['category'] = 'ไม่ระบุสาเหตุชัดเจน'
            entry['reason'] = 'ไม่ระบุสาเหตุ'
            cause_rows.append(entry)

    df_causes = pd.DataFrame(cause_rows)
    return df_causes


# ==============================================================================
# 4. METRICS & AGGREGATIONS
# ==============================================================================

def get_kpis(df_cases: pd.DataFrame, df_causes: pd.DataFrame) -> dict:
    """
    Compute headline KPI metrics for executive overview.
    """
    total_cases = len(df_cases)
    if total_cases == 0:
        return {
            'total_cases': 0,
            'top_ward': '-',
            'top_ward_cases': 0,
            'top_cause': '-',
            'top_cause_count': 0,
            'resolution_rate': 0.0,
            'incident_count': 0
        }
    
    # Top Ward
    ward_counts = df_cases['ward_standard'].value_counts()
    top_ward = ward_counts.index[0] if len(ward_counts) > 0 else '-'
    top_ward_cases = int(ward_counts.iloc[0]) if len(ward_counts) > 0 else 0
    
    # Top Cause
    cause_counts = df_causes['reason'].value_counts()
    top_cause = cause_counts.index[0] if len(cause_counts) > 0 else '-'
    top_cause_count = int(cause_counts.iloc[0]) if len(cause_counts) > 0 else 0
    
    # Resolution Rate
    resolved_count = df_cases['resolution'].str.contains('แก้ไขแล้ว|ยกเลิก', na=False).sum()
    resolution_rate = round((resolved_count / total_cases) * 100, 1)
    
    # Incidents
    incident_count = int(df_cases['is_incident'].sum())
    
    return {
        'total_cases': total_cases,
        'top_ward': top_ward,
        'top_ward_cases': top_ward_cases,
        'top_cause': top_cause,
        'top_cause_count': top_cause_count,
        'resolution_rate': resolution_rate,
        'incident_count': incident_count
    }


def get_rejection_rate_tables(
    cases: pd.DataFrame,
    denominator: pd.DataFrame,
    selected_months: list[str],
    selected_wards: list[str],
    all_wards: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate monthly and Ward rates only where real totals are complete.

    The denominator sheet can contain either a hospital total per month, Ward
    totals, or both. A hospital total is never used for a selected Ward subset.
    """
    columns = ['year_month', 'thai_month_year', 'ward_standard', 'rejected',
               'total_specimens', 'rate_pct', 'status']
    if cases.empty and (denominator is None or denominator.empty):
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=columns)

    scoped_cases = cases[
        cases['year_month'].isin(selected_months)
        & cases['ward_standard'].isin(selected_wards)
    ]
    scoped_den = denominator[denominator['year_month'].isin(selected_months)].copy() if denominator is not None and not denominator.empty else pd.DataFrame(columns=columns)
    scoped_den['ward_standard'] = scoped_den['ward_standard'].fillna('').astype(str).str.strip()
    ward_den = scoped_den[scoped_den['ward_standard'].isin(selected_wards) & scoped_den['ward_standard'].ne('')]
    overall_den = scoped_den[scoped_den['ward_standard'].eq('')]
    case_counts = scoped_cases.groupby(['year_month', 'ward_standard']).size().to_dict()
    ward_totals = ward_den.groupby(['year_month', 'ward_standard'])['total_specimens'].sum().to_dict() if not ward_den.empty else {}
    labels = dict(zip(cases['year_month'], cases['thai_month_year']))
    labels.update(dict(zip(scoped_den['year_month'], scoped_den['thai_month_year'])))

    def make_row(month, ward, rejected, total, missing=False):
        if missing or pd.isna(total) or total <= 0:
            status, rate = 'ไม่มีตัวหาร', None
        elif rejected > 0 and total <= rejected:
            status, rate = 'ตัวหารไม่ถูกต้อง', None
        else:
            status, rate = 'พร้อมใช้', round(rejected / total * 100, 2)
        return [month, labels.get(month, month), ward, int(rejected),
                None if pd.isna(total) else float(total), rate, status]

    ward_keys = set(case_counts) | set(ward_totals)
    ward_rows = [make_row(month, ward, case_counts.get((month, ward), 0),
                          ward_totals.get((month, ward), float('nan')))
                 for month, ward in sorted(ward_keys)]
    ward_table = pd.DataFrame(ward_rows, columns=columns)

    all_selected = set(selected_wards) == set(all_wards)
    overall_totals = overall_den.groupby('year_month')['total_specimens'].sum().to_dict() if not overall_den.empty else {}
    month_rows = []
    for month in sorted(set(selected_months) & (set(scoped_cases['year_month']) | set(scoped_den['year_month']))):
        rejected = int(sum(count for (ym, _), count in case_counts.items() if ym == month))
        if all_selected and month in overall_totals:
            total, missing = overall_totals[month], False
        else:
            month_keys = [(ym, ward) for ym, ward in case_counts if ym == month]
            missing = any(key not in ward_totals for key in month_keys)
            totals = [value for (ym, _), value in ward_totals.items() if ym == month]
            total = sum(totals) if totals else float('nan')
        month_rows.append(make_row(month, '', rejected, total, missing))
    return pd.DataFrame(month_rows, columns=columns), ward_table


# ============================================================================
# 4. MICROBIOLOGY WORKLOAD STATISTICS
# ============================================================================

MICROBIOLOGY_SPECIMEN_NAMES = (
    'Hemo', 'Urine', 'Stool', 'Genital tract', 'Sputum', 'Pus', 'Fluid',
    'Gram stain', 'AFB', 'Modified AFB', 'KOH', 'Fungus', 'TB', 'PCR'
)


def _microbiology_number(value):
    """Convert spreadsheet counts to numbers while ignoring placeholders."""
    if value is None or (isinstance(value, str) and value.strip() in {'', '-', ' -', '#VALUE!'}):
        return None
    number = pd.to_numeric(str(value).replace(',', '').strip(), errors='coerce')
    return None if pd.isna(number) else float(number)


def _microbiology_month(value):
    text = str(value or '').strip().lower()
    for name, month in THAI_MONTHS.items():
        if text == name.lower():
            return month
    return None


def _microbiology_fiscal_year(value):
    match = re.search(r'ปีงบ\s*([0-9๐-๙]{4})', str(value or ''))
    if not match:
        return None
    digits = str(match.group(1)).translate(str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789'))
    return int(digits)


def _microbiology_period(fiscal_year, month):
    """Return Gregorian year-month for a Thai fiscal-year/month pair."""
    year_ce = fiscal_year - 543 if month <= 9 else fiscal_year - 544
    return f'{year_ce:04d}-{month:02d}'


def load_microbiology_stats(source) -> dict:
    """Read the annual and monthly microbiology workload workbook.

    The workbook repeats a small monthly block for every fiscal year, so this
    parser finds each ``ปีงบ`` marker and reads the headers immediately below it
    instead of relying on fixed row numbers. This lets new fiscal-year blocks
    be added without changing the dashboard code.
    """
    monthly_records = []
    annual_records = []
    warnings = []
    try:
        xl = pd.ExcelFile(source)
    except Exception as exc:
        return {'monthly': pd.DataFrame(), 'annual': pd.DataFrame(), 'warnings': [str(exc)]}

    month_sheet = next((name for name in xl.sheet_names if 'แยก culture เดือน' in name.lower()), None)
    year_sheet = next((name for name in xl.sheet_names if 'แยก culture ปี' in name.lower()), None)
    if month_sheet is None:
        warnings.append('ไม่พบชีทแยก Culture เดือน')
    if year_sheet is None:
        warnings.append('ไม่พบชีทแยก Culture ปี')

    if month_sheet:
        raw = xl.parse(month_sheet, header=None)
        fy_rows = [(idx, _microbiology_fiscal_year(row.iloc[0])) for idx, row in raw.iterrows()]
        fy_rows = [(idx, fy) for idx, fy in fy_rows if fy is not None]
        for block_index, (fy_row, fiscal_year) in enumerate(fy_rows):
            next_fy_row = fy_rows[block_index + 1][0] if block_index + 1 < len(fy_rows) else len(raw)
            header_row = None
            specimen_columns = {}
            for candidate in range(fy_row + 1, min(fy_row + 6, next_fy_row)):
                values = raw.iloc[candidate].tolist()
                found = {}
                # The first monthly table occupies A:O. Some versions repeat
                # aggregate views to the right; ignore those duplicate columns.
                for col, value in enumerate(values[:15]):
                    label = str(value or '').strip()
                    canonical = next((name for name in MICROBIOLOGY_SPECIMEN_NAMES if label.lower() == name.lower()), None)
                    if canonical:
                        found[col] = canonical
                if len(found) >= 3:
                    header_row, specimen_columns = candidate, found
                    break
            if header_row is None:
                warnings.append(f'ปีงบประมาณ {fiscal_year}: ไม่พบหัวคอลัมน์ชนิดสิ่งส่งตรวจ')
                continue
            for row_index in range(header_row + 1, next_fy_row):
                month = _microbiology_month(raw.iat[row_index, 0] if raw.shape[1] else None)
                if month is None:
                    continue
                for col, specimen in specimen_columns.items():
                    count = _microbiology_number(raw.iat[row_index, col])
                    if count is None:
                        continue
                    monthly_records.append({
                        'fiscal_year_num': fiscal_year,
                        'fiscal_year': f'ปีงบประมาณ {fiscal_year}',
                        'month_num': month,
                        'month': str(raw.iat[row_index, 0]).strip(),
                        'year_month': _microbiology_period(fiscal_year, month),
                        'specimen_type': specimen,
                        'count': count,
                        'source_sheet': month_sheet,
                    })

    if year_sheet:
        raw = xl.parse(year_sheet, header=None)
        for header_row in range(len(raw)):
            years = []
            for col in range(1, min(raw.shape[1], 20)):
                number = _microbiology_number(raw.iat[header_row, col])
                if number is not None and 2400 <= number <= 2700:
                    years.append((col, int(number)))
            if len(years) < 2:
                continue
            for row_index in range(header_row + 1, min(header_row + 20, len(raw))):
                label = str(raw.iat[row_index, 0] or '').strip()
                specimen = next((name for name in MICROBIOLOGY_SPECIMEN_NAMES if label.lower() == name.lower()), None)
                if specimen is None:
                    if row_index > header_row + 1 and not label:
                        break
                    continue
                for col, fiscal_year in years:
                    count = _microbiology_number(raw.iat[row_index, col])
                    if count is None:
                        continue
                    annual_records.append({
                        'fiscal_year_num': fiscal_year,
                        'fiscal_year': f'ปีงบประมาณ {fiscal_year}',
                        'specimen_type': specimen,
                        'count': count,
                        'source_sheet': year_sheet,
                    })

    monthly = pd.DataFrame(monthly_records)
    annual = pd.DataFrame(annual_records)
    if monthly.empty:
        monthly = pd.DataFrame(columns=['fiscal_year_num', 'fiscal_year', 'month_num', 'month', 'year_month', 'specimen_type', 'count', 'source_sheet'])
    if annual.empty:
        annual = pd.DataFrame(columns=['fiscal_year_num', 'fiscal_year', 'specimen_type', 'count', 'source_sheet'])

    # The annual sheet may lag behind the current fiscal year. Fill only missing
    # annual keys from monthly totals; existing official annual totals win.
    if not monthly.empty:
        monthly_totals = (monthly.groupby(['fiscal_year_num', 'fiscal_year', 'specimen_type'], as_index=False)['count'].sum())
        if not annual.empty:
            existing = set(zip(annual['fiscal_year_num'], annual['specimen_type']))
            monthly_totals = monthly_totals[
                ~monthly_totals.apply(lambda row: (row['fiscal_year_num'], row['specimen_type']) in existing, axis=1)
            ]
        if not monthly_totals.empty:
            monthly_totals['source_sheet'] = 'คำนวณจากแยก Culture เดือน'
            annual = pd.concat([annual, monthly_totals], ignore_index=True)

    return {'monthly': monthly, 'annual': annual, 'warnings': warnings,
            'month_sheet': month_sheet, 'year_sheet': year_sheet}


def get_monthly_trend(df_cases: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate rejection cases over time by Year-Month.
    """
    if df_cases.empty:
        return pd.DataFrame(columns=['year_month', 'thai_month_year', 'count'])
    
    trend = df_cases.groupby(['year_month', 'thai_month_year']).size().reset_index(name='count')
    trend = trend.sort_values('year_month')
    return trend


def get_top_wards(df_cases: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Get top wards with highest specimen rejection counts.
    """
    if df_cases.empty:
        return pd.DataFrame(columns=['ward_standard', 'ward_group', 'count'])
    
    ward_df = df_cases.groupby(['ward_standard', 'ward_group']).size().reset_index(name='count')
    ward_df = ward_df.sort_values('count', ascending=False).head(top_n)
    return ward_df


def get_category_distribution(df_causes: pd.DataFrame) -> pd.DataFrame:
    """
    Get breakdown by rejection category.
    """
    if df_causes.empty:
        return pd.DataFrame(columns=['category', 'count', 'pct'])
    
    cat_df = df_causes['category'].value_counts().reset_index()
    cat_df.columns = ['category', 'count']
    cat_df['pct'] = round((cat_df['count'] / cat_df['count'].sum()) * 100, 1)
    return cat_df


def get_top_reasons(df_causes: pd.DataFrame, top_n: int = 10, category: str = None) -> pd.DataFrame:
    """
    Get top rejection reasons, optionally filtered by category.
    """
    if df_causes.empty:
        return pd.DataFrame(columns=['reason', 'category', 'count'])
    
    filtered = df_causes
    if category and category != 'ทั้งหมด':
        filtered = filtered[filtered['category'] == category]
        
    reason_df = filtered.groupby(['reason', 'category']).size().reset_index(name='count')
    reason_df = reason_df.sort_values('count', ascending=False).head(top_n)
    return reason_df


def get_ward_cause_crosstab(df_causes: pd.DataFrame, top_wards_n: int = 12) -> pd.DataFrame:
    """
    Cross-tabulation matrix of Top Wards x Rejection Categories.
    """
    if df_causes.empty:
        return pd.DataFrame()
        
    top_wards = df_causes['ward_standard'].value_counts().head(top_wards_n).index.tolist()
    sub_df = df_causes[df_causes['ward_standard'].isin(top_wards)]
    
    ct = pd.crosstab(sub_df['ward_standard'], sub_df['category'])
    # Re-order index by total counts
    ct['total'] = ct.sum(axis=1)
    ct = ct.sort_values('total', ascending=True)
    ct = ct.drop(columns=['total'])
    return ct


def get_unmapped_wards(df_cases: pd.DataFrame) -> pd.DataFrame:
    """
    Audit tool: identify ward names that were not in WARD_MAPPING dictionary.
    """
    if df_cases.empty:
        return pd.DataFrame(columns=['ward_raw', 'assigned_standard', 'assigned_group', 'case_count'])
        
    unmapped = []
    counts = df_cases['ward_raw'].value_counts()
    for raw_w, cnt in counts.items():
        if raw_w not in WARD_MAPPING:
            std, grp = standardize_ward(raw_w)
            unmapped.append({
                'ward_raw': raw_w,
                'assigned_standard': std,
                'assigned_group': grp,
                'case_count': cnt
            })
    return pd.DataFrame(unmapped)
