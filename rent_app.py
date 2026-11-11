"""장비 대여 기록부."""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

CSV = Path(__file__).with_name("rent.csv")
COLS = ["대여자", "장비", "대여일", "반납예정일", "반납"]
SEED = """대여자,장비,대여일,반납예정일,반납
김민수,오실로스코프,2026-11-02,2026-11-09,N
이서연,노트북,2026-11-05,2026-11-12,N
박지훈,스펙트럼 분석기,2026-10-28,2026-11-04,Y
최유나,프로젝터,2026-11-10,2026-11-11,N
정우성,측정 케이블 세트,2026-10-30,2026-11-06,N
"""


def load() -> pd.DataFrame:
    if not CSV.exists():
        CSV.write_text(SEED, encoding="utf-8-sig")
    return pd.read_csv(CSV, encoding="utf-8-sig", dtype=str).fillna("")


def save(df: pd.DataFrame) -> None:
    df[COLS].to_csv(CSV, index=False, encoding="utf-8-sig")


def status(row, base: date):
    """(글자, 색) — 색: red / yellow / None"""
    if row["반납"].upper() == "Y":
        return "반납 완료", None
    due = date.fromisoformat(row["반납예정일"])
    d = (due - base).days
    if d < 0:
        return f"연체 {-d}일", "red"
    if d == 0:
        return "오늘 반납", "yellow"
    return f"대여 중 {d}일 남음", None


st.set_page_config(page_title="장비 대여 기록부", layout="wide")
st.title("장비 대여 기록부")
df = load()

# 등록 폼
with st.form("add", clear_on_submit=True):
    c = st.columns(4)
    who = c[0].text_input("대여자")
    item = c[1].text_input("장비")
    start = c[2].date_input("대여일", value=date.today())
    due = c[3].date_input("반납 예정일", value=date.today() + timedelta(days=7))
    if st.form_submit_button("등록", type="primary"):
        if not who.strip() or not item.strip():
            st.error("대여자와 장비를 입력해 주세요.")
        elif due < start:
            st.error("반납 예정일이 대여일보다 빠릅니다.")
        else:
            new = pd.DataFrame([[who.strip(), item.strip(), start.isoformat(), due.isoformat(), "N"]], columns=COLS)
            save(pd.concat([df, new], ignore_index=True))
            st.toast(f"등록했습니다: {who} / {item}")
            st.rerun()

st.divider()
base = st.date_input("기준일", value=date.today())

# 건수
stats = [status(r, base) for _, r in df.iterrows()]
m = st.columns(4)
m[0].metric("전체", len(df))
m[1].metric("대여 중", sum(s[0] != "반납 완료" for s in stats))
m[2].metric("오늘 반납", sum(s[1] == "yellow" for s in stats))
m[3].metric("연체", sum(s[1] == "red" for s in stats))

n_rent = sum(s[0] != "반납 완료" for s in stats)
st.caption(
    f"기준일 {base.isoformat()} · 전체 {len(df)}건 중 대여 중 {n_rent}건, 반납 완료 {len(df) - n_rent}건 "
    f"(대여 중 가운데 연체 {sum(s[1] == 'red' for s in stats)}건, 오늘 반납 {sum(s[1] == 'yellow' for s in stats)}건)"
)

# 상태 표
ICON = {"red": "🔴 ", "yellow": "🟡 "}
view = df[["대여자", "장비", "대여일", "반납예정일"]].copy()
view["상태"] = [ICON.get(c, "") + t for t, c in stats]
BG = {"red": "background-color:#fde8e8;color:#c62828;font-weight:bold",
      "yellow": "background-color:#fff6d6;color:#8a6d00;font-weight:bold"}


def paint(col):
    return [BG.get(c, "") for _, c in stats] if col.name == "상태" else [""] * len(col)


sel = st.dataframe(
    view.style.apply(paint),
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="multi-row",
    key="tbl",
)

# 반납 처리: 표에서 줄을 선택(왼쪽 체크) 후 버튼
picked = [i for i in sel.selection.rows if df.loc[i, "반납"].upper() != "Y"]
if st.button(f"선택한 줄 반납 처리 ({len(picked)}건)", disabled=not picked, type="primary"):
    df.loc[picked, "반납"] = "Y"
    save(df)
    st.toast("반납 처리: " + ", ".join(df.loc[picked, "대여자"] + " / " + df.loc[picked, "장비"]))
    st.rerun()
