"""마진 · 판정 계산 (화면과 무관한 순수 로직)."""
import io

import pandas as pd

REQUIRED = ["시료명", "항목", "측정값", "기준값"]
EPS = 1e-12


def read_csv(data: bytes) -> pd.DataFrame:
    """UTF-8(BOM 포함) 우선, 실패하면 CP949(엑셀 저장 CSV)로 읽는다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=enc, dtype=str, skip_blank_lines=True)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("파일 인코딩을 읽을 수 없습니다 (UTF-8 / CP949 아님).")
    df.columns = [c.strip() for c in df.columns]
    df = df.fillna("").apply(lambda s: s.str.strip())
    df = df[(df != "").any(axis=1)].reset_index(drop=True)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("필수 열이 없습니다: " + ", ".join(missing))
    if df.empty:
        raise ValueError("데이터가 없습니다.")
    return df


def judge(measured: float, limit: float, kind: str = "이하"):
    """마진 = 기준값 − 측정값.
    '이하' 기준: 마진 ≥ 0 이면 적합 / '이상' 기준: 마진 ≤ 0 이면 적합.
    숫자가 아니면 (None, None)."""
    if pd.isna(measured) or pd.isna(limit):
        return None, None
    margin = limit - measured
    ok = margin <= EPS if "이상" in str(kind) else margin >= -EPS
    return margin, ok


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    """원본 열 + '마진', '판정'(적합/부적합/-) 열을 붙여 돌려준다."""
    out = df.copy()
    m = pd.to_numeric(out["측정값"], errors="coerce")
    s = pd.to_numeric(out["기준값"], errors="coerce")
    kinds = out["기준종류"] if "기준종류" in out.columns else pd.Series("이하", index=out.index)
    res = [judge(a, b, k) for a, b, k in zip(m, s, kinds)]
    out["마진"] = [r[0] for r in res]
    out["판정"] = ["-" if r[1] is None else ("적합" if r[1] else "부적합") for r in res]
    return out


def counts(df: pd.DataFrame) -> dict:
    return {
        "전체": len(df),
        "적합": int((df["판정"] == "적합").sum()),
        "부적합": int((df["판정"] == "부적합").sum()),
    }


def to_excel(df: pd.DataFrame) -> bytes:
    """결과를 xlsx 바이트로. 부적합 줄은 연한 빨강 배경."""
    from openpyxl.styles import Font, PatternFill

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="결과")
        ws = xw.sheets["결과"]
        fill = PatternFill("solid", fgColor="FDE8E8")
        red = Font(color="C62828", bold=True)
        judge_col = list(df.columns).index("판정") + 1
        for i, v in enumerate(df["판정"], start=2):
            if v == "부적합":
                for cell in ws[i]:
                    cell.fill = fill
                ws.cell(i, judge_col).font = red
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(40, width * 1.6 + 2)
    return buf.getvalue()
