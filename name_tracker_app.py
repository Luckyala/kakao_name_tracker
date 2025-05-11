import streamlit as st
import re
import pandas as pd
from io import BytesIO
from collections import defaultdict
from datetime import datetime

st.title("이름/별명 날짜별 참여 분석기 (정규화 최적화)")
st.write("0509 형식의 날짜도 인식하고, 조/브랜드 이름 제거 및 이름 정규화를 통해 날짜별 참여 여부를 정확히 분석합니다.")

uploaded_files = st.file_uploader("📂 텍스트 파일들을 업로드하세요", type=["txt"], accept_multiple_files=True)

# ✅ 숫자) + 조 이름 제거 후 이름 추출
pattern = re.compile(
    r"\d+\)\s*(?:(?:\d+조|[가-힣]+조)[\s/]*)?([\w가-힣/_]+(?:[\s/][\w가-힣/_]+)*)"
)

# ✅ 이름 정규화 함수
def normalize_name_to_core(name):
    parts = re.split(r"[\s/]", name.strip())
    parts = [p for p in parts if p]

    # 블랙리스트 단어 (브랜드/조/수식어 등)
    blacklist = {"하고랩스", "사부작사부작", "으랏차", "인스피레이션", "BGO"}
    parts = [p for p in parts if not re.fullmatch(r"\d+조", p) and p not in blacklist]

    # 가장 긴 한글 이름 (우선)
    korean_parts = [p for p in parts if re.fullmatch(r"[가-힣]{2,3}", p)]
    if korean_parts:
        return max(korean_parts, key=len)

    # ID 스타일 (혼합형)
    id_parts = [p for p in parts if re.fullmatch(r"[가-힣a-zA-Z0-9_]{4,}", p)]
    if id_parts:
        return id_parts[-1]

    # fallback
    return " ".join(sorted(parts))

# ✅ 텍스트에서 이름 추출
def extract_names_from_text(text):
    names = []
    for line in text.split("\n"):
        original_line = line.strip()
        if not original_line or not re.search(r"\d+\)", original_line):
            continue
        match = pattern.search(original_line)
        if match:
            name = match.group(1).strip()
            name = re.sub(r"\s+", " ", name)
            names.append(name)
        else:
            st.warning(f"❌ 이름 추출 실패: '{original_line}'")
    return names

# ✅ 파일명에서 날짜 추출
def extract_date_from_filename(filename):
    match = re.search(r"(\d{4}[.-]?\d{2}[.-]?\d{2}|\d{1,2}월\s*\d{1,2}일|\d{4})", filename)
    if match:
        raw_date = match.group(1)
        try:
            if "월" in raw_date:
                m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", raw_date)
                return datetime.strptime(f"2024-{int(m.group(1)):02}-{int(m.group(2)):02}", "%Y-%m-%d").date()
            elif re.fullmatch(r"\d{4}", raw_date):  # 예: '0509'
                return datetime.strptime(f"2024-{raw_date[:2]}-{raw_date[2:]}", "%Y-%m-%d").date()
            else:
                return datetime.strptime(raw_date.replace('.', '-'), "%Y-%m-%d").date()
        except:
            return None
    return None

# ✅ 메인 실행
if uploaded_files:
    participation = defaultdict(dict)
    all_dates = set()

    for file in uploaded_files:
        date = extract_date_from_filename(file.name)
        if not date:
            st.error(f"⚠️ 날짜 인식 실패: {file.name}")
            continue

        all_dates.add(date)
        content = file.read().decode('utf-8')
        raw_names = extract_names_from_text(content)

        for n in raw_names:
            normalized = normalize_name_to_core(n)
            participation[normalized][date] = 'O'

    sorted_dates = sorted(all_dates)
    rows = []
    for name, dates in participation.items():
        row = {'이름': name}
        for d in sorted_dates:
            row[str(d)] = dates.get(d, 'X')
        row['총 횟수'] = list(dates.values()).count('O')
        rows.append(row)

    df = pd.DataFrame(rows)

    # 누락 컬럼 보완
    for col in ['이름', '총 횟수']:
        if col not in df.columns:
            df[col] = ""
    for d in sorted_dates:
        col = str(d)
        if col not in df.columns:
            df[col] = "X"

    df = df[['이름'] + [str(d) for d in sorted_dates] + ['총 횟수']]
    st.dataframe(df)

    # ✅ CSV 다운로드
    st.download_button(
        label="📥 날짜별 참여 현황 다운로드 (CSV)",
        data=df.to_csv(index=False),
        file_name="날짜별_참여현황.csv",
        mime="text/csv"
    )

    # ✅ Excel 다운로드
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    st.download_button(
        label="📥 날짜별 참여 현황 다운로드 (Excel)",
        data=excel_buffer,
        file_name="날짜별_참여현황.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )