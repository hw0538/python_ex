"""CSV 측정 데이터 대시보드 (화면)."""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import calc

st.set_page_config(page_title="측정 데이터 대시보드", layout="wide")
st.title("측정 데이터 대시보드")

up = st.file_uploader("CSV 파일을 올려 주세요", type="csv")
if up is None:
    st.info("CSV 파일을 올리면 표 · 건수 · 차트가 표시됩니다.")
    st.stop()

try:
    df = calc.evaluate(calc.read_csv(up.getvalue()))
except ValueError as e:
    st.error(str(e))
    st.stop()

st.caption(f"불러온 파일: {up.name} ({len(df)}건)")

# 필터 · 정렬
c1, c2, c3 = st.columns([1, 1, 1])
samples = c1.multiselect("시료명", sorted(df["시료명"].unique()))
items = c2.multiselect("항목", list(dict.fromkeys(df["항목"])))
order = c3.radio("마진 정렬", ["원래 순서", "작은 순", "큰 순"], horizontal=True)

view = df
if samples:
    view = view[view["시료명"].isin(samples)]
if items:
    view = view[view["항목"].isin(items)]
if order != "원래 순서":
    view = view.sort_values("마진", ascending=(order == "작은 순"), na_position="last")

# 건수
n = calc.counts(view)
k1, k2, k3 = st.columns(3)
k1.metric("전체", n["전체"])
k2.metric("적합", n["적합"])
k3.metric("부적합", n["부적합"])

# 막대 차트: 항목별, 측정값 막대(부적합 빨강) + 기준값 점선
chart_df = view.dropna(subset=["마진"]).copy()
chart_df["측정값"] = pd.to_numeric(chart_df["측정값"])
chart_df["기준값"] = pd.to_numeric(chart_df["기준값"])
label_cols = [c for c in ["시료명", "시험주파수(MHz)"] if c in chart_df.columns]
chart_df["라벨"] = chart_df[label_cols].astype(str).agg(" / ".join, axis=1) + " #" + chart_df.index.astype(str)

color = alt.Color(
    "판정:N",
    scale=alt.Scale(domain=["적합", "부적합"], range=["#2f5bd3", "#c62828"]),
    legend=alt.Legend(orient="top", title=None),
)
cols = st.columns(2)
for i, (item, g) in enumerate(chart_df.groupby("항목", sort=False)):
    unit = g["단위"].iloc[0] if "단위" in g.columns else ""
    y = alt.Y("라벨:N", sort=None, title=None)
    base = alt.Chart(g)
    bars = base.mark_bar().encode(
        x=alt.X("측정값:Q", title=f"측정값 ({unit})"),
        y=y,
        color=color,
        tooltip=["시료명", "측정값", "기준값", alt.Tooltip("마진:Q", format=".3f"), "판정"],
    )
    limit = base.mark_tick(color="#111", thickness=2, size=20, strokeDash=[4, 3]).encode(
        x="기준값:Q", y=y, tooltip=["기준값"]
    )
    with cols[i % 2]:
        st.markdown(f"**{item}** ({unit}) — 막대: 측정값, 점선: 기준값")
        st.altair_chart((bars + limit).properties(height=max(120, 28 * len(g))), use_container_width=True)

# 표 (부적합 줄 빨간색)
def red_row(row):
    style = "background-color:#fde8e8;color:#c62828" if row["판정"] == "부적합" else ""
    return [style] * len(row)

st.dataframe(
    view.style.apply(red_row, axis=1).format({"마진": "{:.3f}"}, na_rep="-"),
    use_container_width=True,
    hide_index=True,
)

# 엑셀 내려받기
st.download_button(
    "결과 엑셀로 내려받기",
    data=calc.to_excel(view),
    file_name=f"{Path(up.name).stem}_결과.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
