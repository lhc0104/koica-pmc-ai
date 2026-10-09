"""AI-KME — Streamlit 화면 (v0.8: 로그인·회원관리·열람 권한, v0.7: 회의록 양식지·이해관계자·사업일정 달력·문서관리).  실행: streamlit run app/ui.py"""
import html
import io
import re
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
import streamlit as st
import yaml
from datetime import date, timedelta
from app import agent, auth, docs_mgmt, feedback, gdrive, minutes_doc, pdm_doc, questioner, rules, schedule, stakeholders, storage, weekly
from app.db import ROOT, connect

APP_NAME = "AI-KME"
APP_FULL = "AI KOICA Monitoring & Evaluation"
COPYRIGHT = ("© 2026 본 프로그램의 저작권은 연세대학교 AI보건정보관리학과 이호철 교수"
             "(LHC0104@YONSEI.AC.KR)에게 있습니다.")
MENUS = ["1. 대쉬보드", "2. 사업개요", "3. 사업일정", "4. 사업관리", "5. 성과관리", "6. 문서관리", "7. AI 사업비서"]
REPORT = "문제보고"
ACCOUNTS = "회원관리"
BRAND_MARK = ('<svg viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
              '<rect x="1.5" y="1.5" width="41" height="41" rx="10" fill="#E8EEF8" stroke="#1F4E9C" stroke-width="1.5"/>'
              '<rect x="10" y="24" width="5" height="10" rx="1.5" fill="#1F4E9C" opacity=".45"/>'
              '<rect x="18" y="17" width="5" height="17" rx="1.5" fill="#1F4E9C" opacity=".7"/>'
              '<rect x="26" y="10" width="5" height="24" rx="1.5" fill="#1F4E9C"/>'
              '<path d="M30 15.5l3.2 3.2L39 12.5" stroke="#1F4E9C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>')

st.set_page_config(page_title=f"{APP_NAME} · {APP_FULL}", page_icon="📊", layout="wide")

# ───────────────────────── 디자인(글자 크기·간격·칸) ─────────────────────────
st.markdown("""
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css");
@import url("https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&display=swap");

/* ── 디자인 토큰 (밝은 작업공간, 강조색 1개, 반경 1종) ── */
:root {
  --ink: #1B2430; --ink-2: #5B6675; --ink-3: #8A97A8;
  --line: #E1E6EF; --line-2: #D5DCE8; --panel: #F7F9FC; --panel-2: #EEF2F9;
  --accent: #1F4E9C; --accent-soft: #E8EEF8;
  --danger: #B3261E; --danger-soft: #FBEAE8; --warn: #9A5B00; --warn-soft: #FFF3DC; --ok: #2E7D32; --ok-soft: #E7F3E8;
  --radius: 10px; --radius-sm: 6px;
}
html, body { font-family: "Pretendard Variable", Pretendard, "Malgun Gothic", "Apple SD Gothic Neo", system-ui, sans-serif; }
html, body, [data-testid="stAppViewContainer"] { font-size: 18px; color: var(--ink); }
.block-container { padding-top: 2.2rem; padding-bottom: 6rem; max-width: 1400px; }
h1 { font-size: 1.9rem !important; font-weight: 800 !important; letter-spacing: -.01em; margin-bottom: .9rem !important; }
h2 { font-size: 1.4rem !important; font-weight: 700 !important; margin-top: 1.6rem !important; }
h3 { font-size: 1.15rem !important; margin-top: 1.2rem !important; }
p, li, label, .stMarkdown { line-height: 1.7 !important; }
[data-testid="stVerticalBlock"] { gap: 1rem; }
[data-testid="stAppDeployButton"], [data-testid="stToolbarActions"] { display: none; }

/* 칸(카드) — 테두리 1px, 그림자 없음, 반경 통일 */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"][style*="border"] {
  border-radius: var(--radius) !important; }
.card-title { font-size: 1.08rem; font-weight: 700; margin-bottom: .2rem; }
.card-meta  { color: var(--ink-2); font-size: .95rem; }
/* 배지: 알약·원색 채움 대신 연한 바탕 + 진한 글자, 작은 반경 */
.badge { display:inline-block; padding: .12rem .55rem; border-radius: var(--radius-sm); font-size: .86rem; font-weight: 700;
         margin-right: .4rem; line-height: 1.5; }
.b-red{background:var(--danger-soft);color:var(--danger)} .b-org{background:var(--warn-soft);color:var(--warn)}
.b-blue{background:var(--accent-soft);color:var(--accent)} .b-gray{background:var(--panel-2);color:var(--ink-2)} .b-green{background:var(--ok-soft);color:var(--ok)}
.kv { padding: .4rem 0 .6rem 0; display:grid; grid-template-columns: 9.5rem 1fr; row-gap:.2rem; }
.kv b { color: var(--accent); }
.kv.wide { grid-template-columns: 14rem 1fr; }

/* 지표 숫자(다른 화면) */
[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800; font-variant-numeric: tabular-nums; }
[data-testid="stMetricLabel"] p { font-size: 1rem !important; }

/* 버튼·입력: 반경 통일, 눌림 피드백 */
.stButton button, .stDownloadButton button, .stFormSubmitButton button { border-radius: var(--radius) !important; transition: background .15s, transform .08s; }
.stButton button:active, .stDownloadButton button:active { transform: translateY(1px); }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background: var(--accent) !important; border-color: var(--accent) !important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] > div > div { border-radius: var(--radius) !important; }

/* 탭 */
.stTabs [role="tab"] { padding: .9rem 1.4rem !important; height: auto !important; }
.stTabs [role="tab"] p, .stTabs [role="tab"] div { font-size: 1.08rem !important; font-weight: 600; }

/* 왼쪽 메뉴 */
section[data-testid="stSidebar"] { min-width: 320px; background: var(--panel); border-right: 1px solid var(--line); }
/* 왼쪽 위 워드마크 AI-KME (v0.7) — 글자만으로 만든 표식: 모니터링 막대 3개 + 평가 체크 */
.brand { display: flex; align-items: center; gap: .7rem; padding: .3rem 0 .2rem .1rem; }
.brand svg { width: 44px; height: 44px; flex: none; }
.brand .wm { font-family: Outfit, "Pretendard Variable", Pretendard, sans-serif; font-size: 1.95rem; font-weight: 800; letter-spacing: -.035em; line-height: 1; color: var(--ink); }
.brand .wm b { color: var(--accent); font-weight: 800; }
.brand .tag { font-family: Outfit, "Pretendard Variable", Pretendard, sans-serif; font-size: .74rem; font-weight: 500; letter-spacing: .02em; color: var(--ink-2); margin-top: .3rem; white-space: nowrap; }
.brand-rule { height: 1px; background: var(--line); margin: .7rem 0 .4rem 0; }
/* 맨 아래 연세대 로고 — 사이드바 내용이 짧아도 바닥에 붙는다 */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > div > div[data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > div[data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div[data-testid="stVerticalBlock"] { min-height: calc(100vh - 6rem); }
.st-key-sb_logo { margin-top: auto !important; padding-bottom: 2.6rem; }
.st-key-sb_logo img { width: 128px; height: auto; display: block; opacity: .9; }
.st-key-sb_logo .lg-cap { font-size: .72rem; color: var(--ink-3); margin-top: .25rem; }
.app-name { white-space: nowrap; font-size: 1.35rem; font-weight: 800; color: var(--accent); letter-spacing: -.01em; line-height: 1.3;
            padding: .4rem 0 .9rem 0; border-bottom: 1px solid var(--line-2); margin-bottom: .6rem; }
section[data-testid="stSidebar"] .stButton button { justify-content: flex-start; text-align: left; padding: .7rem 1rem; min-height: 3rem;
            border-radius: var(--radius) !important; }
section[data-testid="stSidebar"] .stButton button[kind="secondary"] { background: transparent !important; border-color: transparent !important; color: var(--ink) !important; }
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover { background: var(--panel-2) !important; border-color: transparent !important; }
section[data-testid="stSidebar"] .stButton button > div, section[data-testid="stSidebar"] .stButton button span { justify-content: flex-start !important; width: 100%; text-align: left; }
section[data-testid="stSidebar"] .stButton button p { font-size: 1.08rem !important; font-weight: 600; text-align: left; width: 100%; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .35rem; }
section[data-testid="stSidebar"] hr { margin: .6rem 0; }

/* ── 1. 대쉬보드 ── */
.dash-sub { color: var(--ink-2); font-size: 1rem; margin: -.4rem 0 1.1rem 0; }
.stats { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr 1fr; border: 1px solid var(--line); border-radius: var(--radius); background: #fff; overflow: hidden; }
.stats > div { padding: .95rem 1.2rem; border-left: 1px solid var(--line); }
.stats > div:first-child { border-left: 0; }
.stats .n { font-size: 2rem; font-weight: 800; line-height: 1.1; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.stats .n small { font-size: 1rem; font-weight: 600; margin-left: .15rem; color: var(--ink-2); }
.stats .l { color: var(--ink-2); font-size: .92rem; margin-top: .2rem; }
.stats .hot { background: var(--danger-soft); } .stats .hot .n { color: var(--danger); } .stats .hot .l { color: var(--danger); }
.stats .warm .n { color: var(--warn); }
.stats .zero .n { color: var(--ink-3); }
.todo-h { display: flex; align-items: baseline; gap: .5rem; margin: 1.1rem 0 .3rem 0; font-weight: 700; font-size: 1.02rem; }
.todo-h .cnt { color: var(--ink-2); font-weight: 600; font-size: .95rem; }
.todo-h.danger { color: var(--danger); } .todo-h.warn { color: var(--warn); }
.todo { display: grid; grid-template-columns: 5.6rem 1fr auto; column-gap: .9rem; align-items: baseline; padding: .6rem .2rem; border-top: 1px solid var(--line); }
.todo:first-of-type { border-top: 0; }
.todo .d { font-weight: 800; font-variant-numeric: tabular-nums; white-space: nowrap; }
.todo .d.danger { color: var(--danger); } .todo .d.warn { color: var(--warn); } .todo .d.plain { color: var(--ink-2); font-weight: 700; }
.todo .t { font-weight: 600; }
.todo .m { color: var(--ink-2); font-size: .92rem; margin-top: .05rem; }
.todo .k { color: var(--ink-3); font-size: .9rem; white-space: nowrap; }
.side { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.2rem .4rem 1.2rem; }
.side h4 { margin: 0 0 .5rem 0; font-size: 1.02rem; font-weight: 700; }
.side .row { padding: .55rem 0; border-top: 1px solid var(--line); font-size: .98rem; }
.side .row:first-of-type { border-top: 0; }
.side .row b { font-weight: 700; }
.side .row .m { color: var(--ink-2); font-size: .9rem; }
.side .row .neg { color: var(--danger); font-weight: 700; font-variant-numeric: tabular-nums; }
.side .empty { color: var(--ink-3); font-size: .95rem; padding: .4rem 0 .6rem 0; }
.side .gap { height: 1rem; }
.empty-ok { color: var(--ok); background: var(--ok-soft); border-radius: var(--radius); padding: .8rem 1rem; font-weight: 600; }
.util { color: var(--ink-3); font-size: .9rem; }

/* 전체 일정표 · 성과점검표 */
.scroll-x { overflow-x: auto; border: 1px solid var(--line-2); border-radius: var(--radius); padding: .4rem; }
table.gantt, table.pms { border-collapse: collapse; font-size: .92rem; width: 100%; }
table.gantt th, table.gantt td, table.pms th, table.pms td { border: 1px solid #E1E6EF; padding: .45rem .5rem; }
table.gantt th, table.pms th { background: #EEF2F9; font-weight: 700; text-align: center; white-space: nowrap; }
table.gantt td.lab { min-width: 21rem; text-align: left; }
table.gantt td.grp { background: #1F4E9C; color: #fff; font-weight: 700; }
table.gantt td.q { min-width: 1.5rem; padding: 0; }
table.gantt td.on { background: #9DB7E3; } table.gantt td.focus { background: #1F4E9C; } table.gantt td.pm { background: #8A97A8; }
table.gantt th.now, table.gantt td.now { box-shadow: inset 0 0 0 2px #E07B00; }
table.pms td { text-align: right; white-space: nowrap; } table.pms td.l { text-align: left; white-space: normal; min-width: 17rem; }
table.pms tr.t td { background: #F7F9FC; } table.pms td.tbd { color: #B26A00; } table.pms td.ok { color: #2E7D32; font-weight: 700; }
.legend span { display:inline-block; width: 1.1rem; height: .9rem; border-radius: 3px; margin: 0 .35rem 0 1rem; vertical-align: middle; }

/* 회의록 — 연도 탭 · 행렬표 */
[data-testid="stButtonGroup"] button, [data-testid="stSegmentedControl"] button { padding: .7rem 1.4rem !important; border-radius: var(--radius) !important; }
[data-testid="stButtonGroup"] button p, [data-testid="stSegmentedControl"] button p { font-size: 1.08rem !important; font-weight: 700; }
.mt-h { font-weight: 700; background: #EEF2F9; color: #1F4E9C; padding: .6rem .3rem; border-radius: var(--radius-sm); text-align: center; font-size: .95rem; white-space: nowrap; }
.mt-c .nowrap { white-space: nowrap; }
.mt-c { font-size: .97rem; line-height: 1.55; padding: .15rem .3rem; word-break: break-word; }
.mt-c .card-meta { font-size: .88rem; }
.mt-c ul { margin: .2rem 0 0 1rem; padding: 0; }
.mt-c li { margin-bottom: .3rem; }
.mt-c li .badge { font-size: .78rem; padding: .08rem .5rem; margin: 0; }
hr.mt-hr { margin: .35rem 0 .55rem 0; border: 0; border-top: 1px solid #E1E6EF; }
.st-key-sh_grid [data-testid="stPopover"] button { padding: .45rem .5rem !important; min-height: 2.4rem; }
.st-key-sh_grid [data-testid="stPopover"] button p { font-size: .95rem !important; white-space: nowrap; }
.st-key-sh_grid a { color: var(--accent); text-decoration: none; word-break: break-all; }
.mt-cnt { display:inline-block; background: var(--accent-soft); color: var(--accent); border-radius: var(--radius-sm); padding:.05rem .5rem; font-size:.85rem; margin-left:.4rem; font-weight: 700; }

/* 주간업무보고 — 주차 × 구분 칸 */
.wk-h { font-weight: 700; background: #EEF2F9; color: #1F4E9C; padding: .55rem .3rem; border-radius: var(--radius-sm); text-align: center; font-size: .95rem; white-space: nowrap; }
.wk-lab { font-weight: 700; font-size: 1rem; padding-top: .45rem; white-space: nowrap; }
.wk-lab.now { color: #E07B00; }
.wk-dt { color: #5B6675; font-size: .9rem; padding-top: .55rem; white-space: nowrap; }
div[class*="st-key-wkf_"] button { background: #2E7D32 !important; border-color: #2E7D32 !important; color: #fff !important; font-weight: 700; }
div[class*="st-key-wkf_"] button p { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
div[class*="st-key-wkf_"] button:hover { background: #256B29 !important; }
div[class*="st-key-wke_"] button { background: transparent !important; border: 1px dashed #D5DCE8 !important; color: #8A97A8 !important; }
div[class*="st-key-wke_"] button:hover { border-color: #1F4E9C !important; color: #1F4E9C !important; }
div[class*="st-key-wkr_"] button { white-space: nowrap; }
hr.wk-hr { margin: .25rem 0 .35rem 0; border: 0; border-top: 1px solid #EEF2F9; }
.wk-tbl { width: 100%; border-collapse: collapse; font-size: 1rem; }
.wk-tbl th, .wk-tbl td { border: 1px solid #E1E6EF; padding: .5rem .6rem; vertical-align: top; text-align: left; }
.wk-tbl th { background: #EEF2F9; white-space: nowrap; }
.wk-tbl td.r { background: #F7F9FC; font-weight: 700; white-space: nowrap; }

/* 5. 성과관리 › 사업산출물 — PDM 표 · 변화모델 */
table.pdm { border-collapse: collapse; width: 100%; font-size: .95rem; }
table.pdm th, table.pdm td { border: 1px solid #C9D3E3; padding: .5rem .6rem; vertical-align: top; text-align: left; line-height: 1.55; }
table.pdm th { background: #1F4E9C; color: #fff; text-align: center; font-weight: 700; }
table.pdm th small { display: block; font-weight: 400; opacity: .85; }
table.pdm td.sec { background: #EEF2F9; font-weight: 700; color: #1F4E9C; }
table.pdm td.code { white-space: nowrap; font-weight: 700; }
table.pdm td.prop { background: #FFFBEB; }
table.pdm ul { margin: 0 0 0 1rem; padding: 0; }
.tc-box { border: 1px solid #C9D3E3; border-radius: var(--radius); padding: .55rem .7rem; margin: .3rem 0; background: #fff; font-size: .95rem; line-height: 1.5; }
.tc-box b { color: #1F4E9C; }
.tc-imp { background: #1F4E9C; color: #fff; text-align: center; font-weight: 700; padding: .8rem; border-radius: var(--radius); font-size: 1.05rem; }
.tc-out { background: #EEF2F9; font-weight: 700; }
.tc-act { background: #F7F9FC; font-size: .9rem; margin-left: .9rem; }
.tc-arrow { text-align: center; color: #8A97A8; font-size: 1.2rem; line-height: 1; margin: .1rem 0; }
.tc-lab { font-size: .85rem; color: #5B6675; font-weight: 700; margin-top: .6rem; }

/* 성과점검표 — KOICA 성과관리양식 v3.2 배치 */
table.kpms { border-collapse: collapse; font-size: .9rem; }
table.kpms th, table.kpms td { border: 1px solid #9DB0C8; padding: .4rem .5rem; vertical-align: middle; line-height: 1.45; }
table.kpms th { background: #BDD7EE; font-weight: 700; text-align: center; white-space: nowrap; }
table.kpms th.ttl { background: #1F4E9C; color: #fff; font-size: 1rem; text-align: left; padding: .55rem .8rem; }
table.kpms td.hd { background: #F3F6FB; text-align: left; vertical-align: top; }
table.kpms td.grp { background: #EEF2F9; font-weight: 700; min-width: 13rem; }
table.kpms td.ind { font-weight: 700; min-width: 14rem; }
table.kpms td.def { min-width: 17rem; font-size: .86rem; }
table.kpms td.txt { min-width: 9rem; font-size: .86rem; }
table.kpms td.num { text-align: right; white-space: nowrap; }
table.kpms td.kind { background: #F7F9FC; font-weight: 700; white-space: nowrap; text-align: center; }
table.kpms td.tbd { color: #B26A00; text-align: center; }
table.kpms td.ok { color: #2E7D32; font-weight: 700; }
table.kpms td.imp { background: #FFFFFF; font-weight: 600; }
table.kpms tr.rate td { color: #5B6675; font-size: .84rem; }
/* 한 화면에 맞추기 (v0.7): 글자를 px 로 줄이고(기본 글자가 18px라 rem 은 크다) 칸 최소 너비를 풀어 가로 스크롤 없이 */
.scroll-x.fit { padding: .2rem; }
table.kpms.fit { width: 100%; font-size: 11.5px; table-layout: auto; }
table.kpms.fit th, table.kpms.fit td { padding: 3px 4px; line-height: 1.3; }
table.kpms.fit th { white-space: normal; font-size: 11px; }
table.kpms.fit th.ttl { font-size: 13px; padding: 5px 8px; }
table.kpms.fit td.hd { font-size: 11px; } table.kpms.fit td.hd .card-meta { font-size: 10.5px; }
table.kpms.fit td.grp { min-width: 72px; font-size: 11px; } table.kpms.fit td.ind { min-width: 96px; font-size: 11.5px; }
table.kpms.fit td.def { min-width: 110px; font-size: 10.5px; } table.kpms.fit td.txt { min-width: 58px; font-size: 10.5px; }
table.kpms.fit td.kind { font-size: 10.5px; padding: 3px 2px; } table.kpms.fit td.num { font-size: 11.5px; min-width: 34px; }
table.kpms.fit td.imp { font-size: 11.5px; } table.kpms.fit tr.rate td { font-size: 10.5px; }
.wide .block-container { max-width: 100% !important; padding-left: 1.6rem; padding-right: 1.6rem; }

/* 3. 사업일정 › 사업일정 달력 (v0.7) */
.cal { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.cal .wd { background: var(--panel-2); text-align: center; font-weight: 700; font-size: .92rem; padding: .45rem 0; color: var(--ink-2); }
.cal .wd.sun, .cal .d .n.sun { color: var(--danger); } .cal .wd.sat, .cal .d .n.sat { color: var(--accent); }
.cal .d { background: #fff; min-height: 7.4rem; padding: .3rem .35rem .4rem .35rem; }
.cal .d.off { background: var(--panel); } .cal .d.off .n { color: var(--ink-3); }
.cal .d .n { display: inline-block; font-weight: 700; font-size: .92rem; color: var(--ink-2); width: 1.7rem; height: 1.7rem; line-height: 1.7rem; text-align: center; border-radius: 50%; }
.cal .d.today .n { background: var(--accent); color: #fff; }
.cal .ev { display: block; font-size: .8rem; line-height: 1.35; margin: .15rem 0 0 0; padding: .12rem .4rem; border-radius: 4px; background: var(--accent-soft); color: var(--accent);
           white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-left: 3px solid var(--accent); }
.cal .ev .tm { font-weight: 700; margin-right: .25rem; }
.cal .ev.ms { background: var(--panel-2); color: var(--ink-2); border-left-color: var(--ink-3); }
.cal .ev.ms.must { background: var(--danger-soft); color: var(--danger); border-left-color: var(--danger); }
.cal .ev.ms.core { background: var(--warn-soft); color: var(--warn); border-left-color: var(--warn); }
.cal .more { font-size: .74rem; color: var(--ink-3); margin-top: .15rem; }
.cal-title { font-size: 1.45rem; font-weight: 800; letter-spacing: -.01em; text-align: center; }
.b-must { background: var(--danger-soft); color: var(--danger); } .b-core { background: var(--warn-soft); color: var(--warn); }

/* 맨 하단 저작권 */
.footer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 100; background: var(--panel); border-top: 1px solid var(--line);
          color: var(--ink-2); font-size: .9rem; text-align: center; padding: .65rem 1rem .65rem 320px; }
@media (max-width: 900px) { .footer { padding-left: 1rem; } .stats { grid-template-columns: 1fr 1fr; } .todo { grid-template-columns: 4.6rem 1fr; } .todo .k { display: none; } }
</style>
""", unsafe_allow_html=True)


# ───────────────────────── 공통 도우미 ─────────────────────────
def table(sql: str, params: tuple = ()) -> pd.DataFrame:
    with connect(readonly=True) as con:
        return pd.read_sql_query(sql, con, params=params)


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def badge(text, color="blue") -> str:
    return f'<span class="badge b-{color}">{esc(text)}</span>'


def dday_badge(days) -> str:
    if days is None:
        return badge("날짜 확인", "gray")
    if days < 0:
        return badge(f"기한경과 {-days}일", "red")
    return badge(f"D-{days}", "red" if days <= 7 else "org" if days <= 14 else "blue")


def card(title: str, meta: str = "", badges: str = "", body: str = ""):
    """칸 하나 — 제목·배지·부가정보·본문"""
    with st.container(border=True):
        st.markdown(f'{badges}<div class="card-title">{esc(title)}</div>'
                    f'<div class="card-meta">{meta}</div>' + (f"<div>{body}</div>" if body else ""),
                    unsafe_allow_html=True)


def grid(items: list, render, cols: int = 2):
    for i in range(0, len(items), cols):
        for col, it in zip(st.columns(cols), items[i:i + cols]):
            with col:
                render(it)


def show_df(df: pd.DataFrame, fit: bool = False):
    """fit=True 면 행 수에 맞춰 높이를 늘려 스크롤 없이 보이게(최대 약 22행)"""
    kw = {"height": min(44 * (len(df) + 1) + 6, 1000)} if fit else {}
    st.dataframe(df, width="stretch", hide_index=True, row_height=44, **kw)


# ───────────────────────── 저장(목차별 폴더) ─────────────────────────
for _m in storage.bootstrap():            # 폴더 준비 + 엑셀·클라우드에서 바뀐 파일 자동 반영
    st.toast(_m)
auth.ensure_admin()
storage.permission_check = lambda: (st.session_state.get("auth") or {}).get("role") == auth.ADMIN     # 세션별 수정 권한


# ───────────────────────── 로그인 · 권한 (v0.8) ─────────────────────────
def current_user() -> dict:
    return st.session_state.get("auth") or {}


def is_admin() -> bool:
    return current_user().get("role") == auth.ADMIN


def view_only() -> bool:
    return bool(current_user()) and not is_admin()


EDIT_WORDS = re.compile(r"저장|추가|삭제|지우기|지우기|수정|바꾸기|만들기|반영|올리기|업로드|생성|계산|등록|연결|끊기|가져오기|보내기|입력|옮기기|답변|재설정|적용")
ALLOW_LABELS = {"메모 저장", "비밀번호 변경", "로그인", "로그아웃"}
VIEW_HELP = "열람 권한만 있습니다. 수정하려면 관리자에게 문의하세요."


def _install_view_only_guard():
    """일반(열람) 권한이면 수정 성격의 버튼·업로더·편집표를 비활성화한다 (저장 계층의 check_edit 가 최종 방어선)"""
    from streamlit.delta_generator import DeltaGenerator as DG
    if getattr(DG, "_aikme_guard", False):
        return
    DG._aikme_guard = True

    def wrap_button(orig):
        def f(self, label, *a, **kw):
            key = str(kw.get("key") or "")
            if view_only() and not key.startswith("nav_") and str(label) not in ALLOW_LABELS and EDIT_WORDS.search(str(label)):
                kw["disabled"] = True
                kw["help"] = VIEW_HELP
            return orig(self, label, *a, **kw)
        return f

    def wrap_disabled(orig):
        def f(self, *a, **kw):
            if view_only():
                kw["disabled"] = True
            return orig(self, *a, **kw)
        return f

    for name, w in (("button", wrap_button), ("form_submit_button", wrap_button), ("popover", wrap_button), ("file_uploader", wrap_disabled), ("data_editor", wrap_disabled)):
        setattr(DG, name, w(getattr(DG, name)))
        setattr(st, name, getattr(st._main, name))


_install_view_only_guard()


def login_screen():
    st.markdown("<style>section[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display: none !important; }</style>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.15, 1])
    with mid:
        st.markdown("<div style='height:3.5rem'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="brand" style="justify-content:center">{BRAND_MARK}<div><div class="wm">AI<b>-</b>KME</div><div class="tag">{esc(APP_FULL)}</div></div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="card-title">로그인</div><div class="card-meta">KOICA 필리핀 루존 부카스센터 PMC 사업 — 사업·성과관리</div>', unsafe_allow_html=True)
            with st.form("login", border=False):
                uid = st.text_input("ID", key="login_id", autocomplete="username")
                pw = st.text_input("비밀번호", type="password", key="login_pw", autocomplete="current-password")
                ok = st.form_submit_button("로그인", type="primary", width="stretch")
            if ok:
                user = auth.verify(uid, pw)
                if user:
                    st.session_state["auth"] = user
                    st.rerun()
                st.error("ID 또는 비밀번호가 맞지 않습니다.")
            st.caption("계정이 없으면 관리자(이호철 교수)에게 ID와 비밀번호를 요청하세요. 일반 계정은 열람만, 관리자 계정은 수정까지 할 수 있습니다.")
    st.markdown(f'<div class="footer">{COPYRIGHT}</div>', unsafe_allow_html=True)


if not st.session_state.get("auth"):
    login_screen()
    st.stop()


def accounts_page():
    """회원관리 — 관리자만. 계정 목록 · 추가 · 권한 변경 · 비밀번호 재설정 · 삭제"""
    st.title("회원관리")
    if not is_admin():
        st.warning("관리자만 들어올 수 있는 화면입니다.")
        return
    show_flash()
    me = current_user()["login_id"]
    rows = auth.list_accounts()
    h1, h2 = st.columns([3.6, 1.4], vertical_alignment="center")
    h1.markdown(f'<div class="card-title" style="font-size:1.35rem">계정 <span class="mt-cnt">{len(rows)}개 · 관리자 {auth.count_admins()}명</span></div>'
                '<div class="card-meta">관리자: 수정·추가·삭제 등 모든 권한 · 일반: 열람만(내려받기 가능, 저장·수정 불가). 비밀번호는 암호화(해시)되어 저장되며 되찾을 수 없고 재설정만 됩니다.</div>', unsafe_allow_html=True)
    with h2.popover("계정 추가", width="stretch"):
        with st.form("acc_add", clear_on_submit=True, border=False):
            nid = st.text_input("ID *", placeholder="영문·숫자 3~32자")
            nname = st.text_input("이름(소속)", placeholder="예: 김PL (현지 사무소)")
            npw = st.text_input("초기 비밀번호 *", type="password")
            nrole = st.radio("권한", auth.ROLES, horizontal=True)
            nnote = st.text_input("메모", placeholder="예: KOICA 필리핀사무소 담당")
            if st.form_submit_button("추가", type="primary"):
                ok, msg = auth.create(nid, nname, npw, nrole, nnote)
                st.session_state["flash"] = (ok, msg); st.rerun()
    with st.container(border=True):
        for c, hd in zip(st.columns([1.2, 1.5, 0.9, 1.2, 1.2, 1.0, 1.35, 0.95]), ["ID", "이름(소속)", "권한", "만든 날", "마지막 로그인", "", "", ""]):
            if hd:
                c.markdown(f'<div class="mt-h">{hd}</div>', unsafe_allow_html=True)
        for r in rows:
            st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.2, 1.5, 0.9, 1.2, 1.2, 1.0, 1.35, 0.95], vertical_alignment="center")
            c1.markdown(f'<div class="mt-c"><b>{esc(r["login_id"])}</b>{" <span class=card-meta>(나)</span>" if r["login_id"] == me else ""}</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="mt-c">{esc(r["name"])}' + (f'<br><span class="card-meta">{esc(r["note"])}</span>' if r["note"] else "") + "</div>", unsafe_allow_html=True)
            c3.markdown(f'<div class="mt-c">{badge(r["role"], "blue" if r["role"] == auth.ADMIN else "gray")}</div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="mt-c card-meta">{esc(r["created_at"])}</div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="mt-c card-meta">{esc(r["last_login"] or "-")}</div>', unsafe_allow_html=True)
            with c6.popover("권한", width="stretch"):
                role = st.radio("권한", auth.ROLES, index=auth.ROLES.index(r["role"]), horizontal=True, key=f"acc_role_{r['login_id']}")
                nm = st.text_input("이름(소속)", value=r["name"], key=f"acc_name_{r['login_id']}")
                nt = st.text_input("메모", value=r["note"], key=f"acc_note_{r['login_id']}")
                if st.button("적용", type="primary", key=f"acc_role_btn_{r['login_id']}"):
                    ok, msg = auth.set_role(r["login_id"], role, me) if role != r["role"] else (True, "")
                    if ok:
                        ok, msg2 = auth.set_name(r["login_id"], nm, nt); msg = (msg + " " + msg2).strip()
                    st.session_state["flash"] = (ok, msg); st.rerun()
            with c7.popover("비밀번호", width="stretch"):
                p1 = st.text_input("새 비밀번호", type="password", key=f"acc_pw_{r['login_id']}")
                if st.button("재설정", type="primary", key=f"acc_pw_btn_{r['login_id']}"):
                    ok, msg = auth.set_password(r["login_id"], p1)
                    st.session_state["flash"] = (ok, f"'{r['login_id']}' {msg}" if ok else msg); st.rerun()
            with c8.popover("삭제", width="stretch", disabled=r["login_id"] == me):
                st.caption(f"'{r['login_id']}' 계정을 지웁니다. 되돌릴 수 없습니다.")
                if st.button("지우기", type="primary", key=f"acc_del_{r['login_id']}"):
                    ok, msg = auth.delete(r["login_id"], me)
                    st.session_state["flash"] = (ok, msg); st.rerun()
    st.caption(f"계정 파일: {storage.rel(storage.csv_path('accounts'))} (비밀번호는 해시만 저장). 최상위 관리자 ID·비밀번호는 환경변수 AIKME_ADMIN_ID / AIKME_ADMIN_PW 로도 정할 수 있습니다(표가 비어 있을 때 적용).")

LABELS = {"milestone_id": "일정ID", "meeting_id": "회의ID", "stakeholder_id": "관계자ID", "output_id": "산출물코드", "sub_output_id": "보조산출물코드",
          "mdoc_id": "문서코드", "indicator_id": "지표ID", "center_id": "센터ID", "doc_id": "문서ID", "source_doc_id": "근거문서ID", "pdm_version": "PDM버전",
          "title": "제목", "name": "명칭", "category": "구분", "project_year": "차년도", "due_date": "기한", "next_due": "차기기한",
          "owner": "담당", "status": "상태", "note": "비고", "related_output": "관련 산출물", "meeting_date": "회의일", "meeting_type": "회의유형",
          "participants": "참석자", "summary": "요약", "description": "내용", "org": "기관", "dept": "부서", "person_name": "담당자",
          "position": "직위", "contact": "연락처", "phone": "휴대전화", "email": "이메일", "photo_path": "사진", "valid_from": "시작일", "valid_to": "종료일", "week_start": "주 시작일", "author": "작성자",
          "done": "실적", "plan": "계획", "issues": "이슈", "progress_pct": "진척률(%)", "lead_expert": "책임전문가", "series": "계열",
          "language": "언어", "approval_method": "승인방법", "quality_criteria": "품질기준", "submitted_at": "제출일", "cycle": "주기",
          "level": "수준", "definition": "정의", "formula": "산식", "unit": "단위", "baseline": "기초선", "baseline_year": "기초선연도",
          "target": "목표치", "target_year": "목표연도", "mov": "입증수단", "data_source": "자료원", "frequency": "주기", "period": "기간",
          "value": "값", "verified_by": "검증자", "region": "지역", "province": "주(Province)", "support_type": "지원유형",
          "mother_hospital": "모병원", "month": "월(YYYY-MM)", "metric": "지표", "is_sample": "예시여부",
          "meeting_time": "시각", "activity": "대분류(Activity)", "stakeholder_org": "소분류(이해관계기관)", "location": "장소",
          "agenda": "회의주요안건", "follow_up": "후속조치사항", "file_path": "첨부파일",
          "seq": "순서", "code": "코드", "version": "버전", "reason": "변경 사유", "approved_at": "승인일", "file_name": "파일명", "uploaded_at": "올린 날짜",
          "indicators": "객관적 검증지표", "assumptions": "중요가정", "proposal": "검증지표 추가제안", "stage": "단계",
          "parent_code": "상위코드", "target_basis": "목표치 선정 근거", "collector": "데이터 수집 주체", "origin": "출처", "outcome": "상위 성과",
          "implementer": "수행기관", "deliverable": "산출물 형태",
          **{f"y{y}": f"{y}({y - 2025}차)" for y in range(2026, 2033)}}
OPTIONS = {("milestones", "status"): ["예정", "진행중", "완료", "지연"], ("action_items", "status"): ["미이행", "진행중", "완료"],
           ("sub_outputs", "status"): ["미착수", "작성중", "제출", "보완요청", "승인"], ("pdm_indicators", "level"): ["Impact", "Outcome", "Output"],
           ("meetings", "meeting_type"): storage.MEETING_TYPES,
           ("pdm_matrix", "level"): ["기본정보", "영향(Impact)", "성과(Outcome)", "산출물(Output)", "활동(Activity)", "투입물(Input)", "선행조건(Pre-condition)"],
           ("change_model", "stage"): ["결과(영향)", "변화(성과)", "변화(산출물)", "수단(활동)"],
           ("pdm_versions", "status"): storage.PDM_STATUS}
AUTO_ID = {"id", "action_id", "report_id"}


def open_folder_button(path, key: str):
    if os.name == "nt" and st.button("저장 폴더 열기", key=key):
        os.startfile(path)  # noqa: 윈도우 탐색기로 열기


def show_flash():
    if "flash" in st.session_state:
        ok, msg = st.session_state.pop("flash")
        (st.success if ok else st.error)(msg)


TABLE_LABELS = {("pdm_matrix", "level"): "구분", ("pdm_matrix", "code"): "코드/항목", ("pdm_matrix", "summary"): "요약(Narrative Summary)",
                ("pdm_matrix", "mov"): "검증수단", ("change_model", "content"): "내용", ("pdm_indicators", "level"): "수준(Impact/Outcome/Output)"}


def col_label(t: str, c: str) -> str:
    return TABLE_LABELS.get((t, c)) or LABELS.get(c, c)


def editor_cfg(t: str, df: pd.DataFrame) -> dict:
    """data_editor 열 설정 — 한글 머리글, 선택 목록, 자동번호"""
    cfg = {}
    for c in df.columns:
        lab = col_label(t, c)
        if (t, c) in OPTIONS:
            cfg[c] = st.column_config.SelectboxColumn(lab, options=OPTIONS[(t, c)], required=True)
        elif c in AUTO_ID:
            cfg[c] = st.column_config.NumberColumn("번호(자동)", disabled=True)
        else:
            cfg[c] = st.column_config.Column(lab)
    return cfg


def labeled(df: pd.DataFrame, t: str = "") -> pd.DataFrame:
    """보기용 — 열 이름을 한글로"""
    return df.rename(columns={c: col_label(t, c) for c in df.columns})


def edit_tab(folder_name: str):
    """해당 목차의 데이터를 표에서 고치고 저장 → DB + pmc/<목차>/파일.csv"""
    show_flash()
    tbls = storage.tables_for(folder_name)
    t = st.selectbox("편집할 데이터", tbls, format_func=lambda x: storage.TABLES[x][2], key=f"sel_{folder_name}")
    df = table(f"SELECT * FROM {t}")
    cfg = editor_cfg(t, df)
    ver = st.session_state.get(f"ver_{t}", 0)
    edited = st.data_editor(df, num_rows="dynamic", column_config=cfg, hide_index=True, width="stretch",
                            row_height=44, key=f"ed_{t}_{ver}")
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("저장", type="primary", width="stretch", key=f"save_{t}"):
        ok, msg = storage.save_table(t, edited)
        st.session_state["flash"] = (ok, msg)
        if ok:
            st.session_state[f"ver_{t}"] = ver + 1
            st.rerun()
        st.error(st.session_state.pop("flash")[1])
    with c2:
        open_folder_button(storage.folder(folder_name), key=f"open_{folder_name}")
    st.caption(f"저장 위치: {storage.rel(storage.csv_path(t))}  ·  표 맨 아래 빈 줄에 입력하면 행이 추가됩니다. "
               "이 파일을 엑셀에서 직접 고쳐 저장해도 자동으로 반영됩니다. 날짜는 2026-10-05 형식으로 적어 주세요.")


# ───────────────────────── 4. 사업관리 › 회의록·후속조치 (v0.5) ─────────────────────────
OTHER = "＋ 직접 입력"
MEETING_GRID = [("Activity", 1.4), ("일시", 1.15), ("이해관계기관", 1.3), ("회의주요안건", 2.0), ("회의결과요약", 2.0), ("후속조치사항", 2.0), ("파일다운로드", 1.35)]


def _nl(v) -> str:
    """여러 줄 텍스트 → HTML (줄바꿈 유지)"""
    return esc(v).replace("\n", "<br>")


def _activity_options() -> list[str]:
    acts = table("SELECT activity_id, name FROM activities ORDER BY output_id='PM', activity_id").to_dict("records")
    used = table("SELECT DISTINCT activity FROM meetings WHERE IFNULL(activity,'')<>''")["activity"].tolist()
    opts = [f"{a['activity_id']} {a['name']}" for a in acts]
    return opts + [u for u in used if u not in opts]


def _org_options() -> list[str]:
    sh = table("SELECT org, dept FROM stakeholders ORDER BY stakeholder_id").to_dict("records")
    opts = []
    for r in sh:
        v = (r["org"] + (f" {r['dept']}" if r["dept"] else "")).strip()
        if v and v not in opts:
            opts.append(v)
    for u in table("SELECT DISTINCT stakeholder_org FROM meetings WHERE IFNULL(stakeholder_org,'')<>''")["stakeholder_org"]:
        if u not in opts:
            opts.append(u)
    return opts


def _doc_bytes(builder, rec, actions=None):
    """Word/PDF 만들기 — 패키지가 없거나 실패해도 화면은 계속 동작"""
    try:
        return builder(rec, actions), None
    except ImportError as e:
        return None, f"문서 패키지가 없습니다: pip install python-docx reportlab  ({e})"
    except Exception as e:
        return None, f"문서 생성 오류: {e}"


def _match_option(value: str, options: list[str]) -> str | None:
    """양식지에 적힌 '1.1' · '1.1 KMITS 분석' · 'DOH KMITS' 를 선택 목록의 항목과 맞춰 본다"""
    v = (value or "").strip()
    if not v:
        return None
    if v in options:
        return v
    low = v.lower()
    for o in options:                                  # 번호만 적은 경우: '1.1.1' → '1.1.1 부카스센터 기자재 지원'
        if o.lower() == low or o.lower().startswith(low + " "):
            return o
    code = low.split()[0]
    hits = [o for o in options if o.lower().split()[0].startswith(code)]          # 번호 앞부분만 적은 경우: 하나로 정해질 때만
    if len(hits) != 1:
        hits = [o for o in options if low in o.lower() or o.lower() in low]      # 이름 일부만 적은 경우
    return hits[0] if len(hits) == 1 else None


def apply_minutes_template(up) -> None:
    """[양식 업로드 (자동 채우기)] — 올린 파일을 읽어 입력 칸(mf_*)에 넣는다. 입력 칸 위젯이 만들어지기 전에 불러야 한다."""
    from app import minutes_template
    sig = (up.name, up.size)
    if st.session_state.get("mf_tpl_sig") == sig:
        return
    st.session_state["mf_tpl_sig"] = sig
    try:
        got = minutes_template.parse(up.name, up.getvalue())
    except Exception as ex:
        st.session_state["mf_tpl_msg"] = (False, f"양식을 읽지 못했습니다: {ex}")
        return
    if not got:
        st.session_state["mf_tpl_msg"] = (False, "양식에서 읽어 올 내용을 찾지 못했습니다. 표 왼쪽 칸의 항목 이름(회의명·회의일·참석자…)이 남아 있는지 확인해 주세요.")
        return
    filled = []
    if got.get("meeting_date"):
        st.session_state["mf_date"] = date.fromisoformat(got["meeting_date"]); filled.append("회의일")
    for col, key, label in [("meeting_time", "mf_time", "시각"), ("title", "mf_title", "회의명"), ("location", "mf_loc", "장소"),
                            ("participants", "mf_parts", "참석자"), ("author", "mf_author", "작성자"), ("agenda", "mf_agenda", "주요 안건"),
                            ("summary", "mf_summary", "결과 요약"), ("follow_up", "mf_follow", "후속조치")]:
        if got.get(col):
            st.session_state[key] = got[col]; filled.append(label)
    if got.get("meeting_type") in storage.MEETING_TYPES:
        st.session_state["mf_type"] = got["meeting_type"]; filled.append("구분")
    if got.get("activity"):
        hit = _match_option(got["activity"], _activity_options())
        st.session_state["mf_act"] = hit or OTHER
        if not hit:
            st.session_state["mf_act_txt"] = got["activity"]
        filled.append("대분류")
    if got.get("stakeholder_org"):
        hit = _match_option(got["stakeholder_org"], _org_options())
        st.session_state["mf_org"] = hit or OTHER
        if not hit:
            st.session_state["mf_org_txt"] = got["stakeholder_org"]
        filled.append("소분류")
    st.session_state["mf_tpl_msg"] = (True, f"{up.name} 에서 {len(filled)}개 항목을 채웠습니다: {', '.join(filled)}. 내용을 확인한 뒤 [저장하기]를 누르세요.")


def meeting_form():
    """[회의록 추가] 입력 칸 — 양식 업로드(자동 채우기) / 저장하기 / Word로 다운받기 / PDF로 다운로드"""
    with st.container(border=True):
        st.markdown('<div class="card-title">회의록 추가</div><div class="card-meta">* 표시는 필수입니다. 저장하면 회의록 표와 후속조치, '
                    'AI 사업비서 검색용 문서까지 한 번에 만들어집니다.</div>', unsafe_allow_html=True)
        t1, t2 = st.columns([1.5, 3.4], vertical_alignment="center")
        with t1.popover("양식 업로드 (자동 채우기)", width="stretch"):
            st.markdown("회의록 양식지(Word)를 채워 올리면 아래 칸이 자동으로 채워집니다. 녹음을 AI로 받아 적은 글을 "
                        "양식지에 맞춰 정리한 파일이면 됩니다.")
            tpl = st.file_uploader("채워진 양식지", type=["docx", "txt", "md"], key="mf_tpl", label_visibility="collapsed")
        t2.caption("양식지가 없으면 위 [회의록 양식지 다운로드]로 받으세요. 올린 뒤에도 모든 칸을 고칠 수 있습니다.")
        if tpl is not None:
            apply_minutes_template(tpl)
            if st.session_state.get("mf_tpl_msg"):
                ok, msg = st.session_state["mf_tpl_msg"]
                (st.success if ok else st.warning)(msg)
        else:
            st.session_state.pop("mf_tpl_sig", None); st.session_state.pop("mf_tpl_msg", None)   # 파일을 지우면 다시 올릴 때 또 채운다

        c1, c2, c3 = st.columns([1.1, 0.7, 2.6])
        d = c1.date_input("회의일 *", format="YYYY-MM-DD", key="mf_date")           # 기본값은 오늘, 양식을 올리면 그 날짜
        tm = c2.text_input("시각", placeholder="14:00", key="mf_time")
        title = c3.text_input("회의명 *", placeholder="예: DOH KMITS 착수 협의", key="mf_title")

        c1, c2, c3 = st.columns([1.6, 1, 1.4])
        act_opts = [""] + _activity_options() + [OTHER]
        act = c1.selectbox("대분류 — 과업(Activity)", act_opts, key="mf_act", format_func=lambda x: x or "(선택)")
        if act == OTHER:
            act = c1.text_input("Activity 이름 직접 입력", key="mf_act_txt")
        mtype = c2.radio("중분류 — 회의 구분", storage.MEETING_TYPES, horizontal=True, key="mf_type")
        org_opts = [""] + _org_options() + [OTHER]
        org = c3.selectbox("소분류 — 이해관계기관", org_opts, key="mf_org", format_func=lambda x: x or "(내부회의 · 해당 없음)")
        add_org = True
        if org == OTHER:
            org = c3.text_input("기관명 직접 입력", key="mf_org_txt", placeholder="예: PhilHealth")
            add_org = c3.checkbox("이해관계자 목록에도 추가", value=True, key="mf_org_add")

        c1, c2, c3 = st.columns(3)
        loc = c1.text_input("장소", key="mf_loc")
        parts = c2.text_input("참석자", placeholder="PM, PL, KMITS 담당", key="mf_parts")
        author = c3.text_input("작성자", key="mf_author")
        agenda = st.text_area("회의 주요 안건", height=110, key="mf_agenda", placeholder="한 줄에 하나씩 적어 주세요.")
        summary = st.text_area("회의 결과 요약", height=140, key="mf_summary")
        follow = st.text_area("후속조치사항", height=110, key="mf_follow",
                              placeholder="한 줄에 하나씩:  조치 내용 / 담당 / 기한(2026-10-05)   → 저장하면 후속조치 목록에 등록되어 대쉬보드에서 기한을 챙깁니다.")
        up = st.file_uploader("첨부 파일 (선택) — 원본 회의록·발표자료 등", key="mf_file")

        rec = {"meeting_date": d.isoformat() if d else "", "meeting_time": tm, "title": title, "activity": act or "", "meeting_type": mtype,
               "stakeholder_org": org or "", "location": loc, "participants": parts, "agenda": agenda, "summary": summary,
               "follow_up": follow, "author": author}
        preview_actions = [dict(a, status="예정") for a in storage.parse_follow_up(follow)]
        ready = bool(title.strip())
        stem = minutes_doc.file_stem(rec)
        docx, e1 = _doc_bytes(minutes_doc.build_docx, rec, preview_actions) if ready else (None, None)
        pdf, e2 = _doc_bytes(minutes_doc.build_pdf, rec, preview_actions) if ready else (None, None)

        b1, b2, b3, b4, _ = st.columns([1.05, 1.35, 1.35, 0.8, 2])
        if b1.button("저장하기", type="primary", width="stretch", key="mf_save"):
            if not ready:
                st.error("회의명을 입력해 주세요.")
            else:
                try:
                    mid, msg = storage.add_meeting(rec, (up.name, up.getvalue()) if up else None, add_org=add_org)
                    st.session_state["flash"] = (True, msg)
                    st.session_state["mt_form"] = False
                    st.session_state["mt_year"] = f"{rec['meeting_date'][:4]}년"     # 저장한 회의의 연도 탭으로 이동
                    for k in [k for k in st.session_state if k.startswith("mf_") or k == "mt_year_ctl"]:
                        del st.session_state[k]
                    st.rerun()
                except Exception as ex:
                    st.error(f"저장하지 못했습니다: {ex}")
        b2.download_button("Word로 다운받기", docx or b"", f"{stem}.docx", minutes_doc.DOCX_MIME, width="stretch", key="mf_docx",
                           disabled=not (ready and docx))
        b3.download_button("PDF로 다운로드", pdf or b"", f"{stem}.pdf", minutes_doc.PDF_MIME, width="stretch", key="mf_pdf",
                           disabled=not (ready and pdf))
        if b4.button("닫기", width="stretch", key="mf_cancel"):
            st.session_state["mt_form"] = False
            st.session_state.pop("mf_tpl_sig", None); st.session_state.pop("mf_tpl_msg", None)
            st.rerun()
        if e1 or e2:
            st.warning(e1 or e2)
        if not ready:
            st.caption("회의명을 입력하고 Enter(또는 다른 칸 클릭)하면 저장·다운로드 버튼이 활성화됩니다.")


def meeting_matrix(rows: list[dict]):
    """연도별 회의록 행렬표 — 1열 Activity · 2열 일시 · 3열 이해관계기관 · 4열 주요안건 · 5열 결과요약 · 6열 후속조치 · 7열 파일다운로드"""
    widths = [w for _, w in MEETING_GRID]
    with st.container(border=True):
        for c, (name, _) in zip(st.columns(widths), MEETING_GRID):
            c.markdown(f'<div class="mt-h">{name}</div>', unsafe_allow_html=True)
        if not rows:
            st.markdown('<div class="card-meta" style="padding:1rem .3rem">이 연도에 등록된 회의록이 없습니다. 오른쪽 위 [회의록 추가]로 등록하거나, 채워진 양식지를 올려 자동으로 채우세요.</div>',
                        unsafe_allow_html=True)
        for m in rows:
            st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
            cols = st.columns(widths, vertical_alignment="top")
            acts = storage.meeting_actions(m["meeting_id"])
            internal = m["meeting_type"] == "내부회의"
            cols[0].markdown(f'<div class="mt-c"><b>{esc(m["activity"] or "(미지정)")}</b><br>{badge(m["meeting_type"] or "-", "blue" if internal else "org")}'
                             f'<span class="card-meta">{esc(m["meeting_id"])}</span></div>', unsafe_allow_html=True)
            cols[1].markdown(f'<div class="mt-c"><b class="nowrap">{esc(m["meeting_date"])}</b><br>{esc(m["meeting_time"] or "")}'
                             + (f'<br><span class="card-meta">{esc(m["location"])}</span>' if m["location"] else "") + "</div>", unsafe_allow_html=True)
            cols[2].markdown(f'<div class="mt-c">{esc(m["stakeholder_org"] or ("PMC 내부" if internal else "-"))}'
                             + (f'<br><span class="card-meta">참석: {esc(m["participants"])}</span>' if m["participants"] else "") + "</div>", unsafe_allow_html=True)
            cols[3].markdown(f'<div class="mt-c"><b>{esc(m["title"])}</b><br>{_nl(m["agenda"] or "")}</div>', unsafe_allow_html=True)
            cols[4].markdown(f'<div class="mt-c">{_nl(m["summary"] or "")}</div>', unsafe_allow_html=True)
            if acts:
                items = "".join(f'<li>{esc(a["description"])} <span class="card-meta">({esc(a["owner"] or "담당 미정")}'
                                f'{" · " + esc(a["due_date"]) if a["due_date"] else ""})</span> '
                                f'{badge(a["status"], "green" if a["status"] == "완료" else "red" if (rules.days_left(a["due_date"]) or 0) < 0 and a["status"] != "완료" else "gray")}</li>'
                                for a in acts)
                cols[5].markdown(f'<div class="mt-c"><ul>{items}</ul></div>', unsafe_allow_html=True)
            else:
                cols[5].markdown(f'<div class="mt-c">{_nl(m["follow_up"] or "-")}</div>', unsafe_allow_html=True)
            with cols[6]:
                docx, err = _doc_bytes(minutes_doc.build_docx, m, acts)
                st.download_button("Word", docx or b"", f"{minutes_doc.file_stem(m)}.docx", minutes_doc.DOCX_MIME,
                                   key=f"dl_{m['meeting_id']}", width="stretch", disabled=not docx, help=err or "회의록을 Word 파일로 내려받습니다")
                fp = ROOT / str(m["file_path"]) if m["file_path"] else None
                if fp and fp.exists():
                    st.download_button("첨부", fp.read_bytes(), fp.name, key=f"att_{m['meeting_id']}", width="stretch", help=fp.name)


def meetings_tab():
    show_flash()
    ms = table("SELECT * FROM meetings ORDER BY meeting_date DESC, meeting_time DESC, meeting_id DESC").fillna("").to_dict("records")
    h1, h2, h3 = st.columns([3.2, 1.5, 1.3], vertical_alignment="center")
    h1.markdown(f'<div class="card-title" style="font-size:1.35rem">회의록 · 후속조치 <span class="mt-cnt">{len(ms)}건</span></div>', unsafe_allow_html=True)
    from app import minutes_template
    if "mt_tpl_bytes" not in st.session_state:                       # 접속마다 한 번 만들고 pmc/4_사업관리/양식/ 에도 적어 둔다
        st.session_state["mt_tpl_bytes"] = minutes_template.template_bytes()
    h2.download_button("회의록 양식지 다운로드", st.session_state["mt_tpl_bytes"], minutes_template.TEMPLATE_NAME, minutes_template.DOCX_MIME,
                       width="stretch", key="mt_tpl_dl",
                       help="Word 양식지입니다. 녹음을 AI로 받아 적은 글을 이 양식에 맞춰 정리한 뒤 [회의록 추가]에 올리면 자동으로 채워집니다.")
    if h3.button("회의록 추가", type="primary", width="stretch", key="mt_add"):
        st.session_state["mt_form"] = not st.session_state.get("mt_form", False)
    if st.session_state.get("mt_form"):
        meeting_form()

    counts = {}
    for m in ms:
        counts[str(m["meeting_date"])[:4]] = counts.get(str(m["meeting_date"])[:4], 0) + 1
    years = sorted({str(y) for y in weekly.years()} | {y for y in counts if y})      # 2026~2031 고정 + 자료가 있는 다른 연도
    labels = [f"{y}년" for y in years]
    fmt = {f"{y}년": f"{y}년 ({counts.get(y, 0)}건)" for y in years}
    default = st.session_state.get("mt_year") if st.session_state.get("mt_year") in labels else (f"{date.today().year}년" if f"{date.today().year}년" in labels else labels[0])
    sel = st.segmented_control("연도", labels, default=default, format_func=lambda x: fmt[x], key="mt_year_ctl", label_visibility="collapsed") or default
    st.session_state["mt_year"] = sel
    year = sel[:4]
    rows = [m for m in ms if str(m["meeting_date"])[:4] == year]

    ALL = "전체"
    f1, f2, f3, f4 = st.columns([1.6, 1, 1.3, 1.6])
    f_act = f1.selectbox("대분류 — 과업(Activity)", [ALL] + _activity_options(), key="mt_f_act")
    f_kind = f2.selectbox("중분류 — 회의 구분", [ALL] + storage.MEETING_TYPES, key="mt_f_kind")
    f_org = f3.selectbox("소분류 — 이해관계기관", [ALL] + _org_options(), key="mt_f_org")
    q = f4.text_input("검색", placeholder="회의명·안건·결과·후속조치에서 찾기", key="mt_q")
    if f_act != ALL:
        rows = [m for m in rows if m["activity"] == f_act]
    if f_kind != ALL:
        rows = [m for m in rows if m["meeting_type"] == f_kind]
    if f_org != ALL:
        rows = [m for m in rows if m["stakeholder_org"] == f_org]
    if q.strip():
        ql = q.strip().lower()
        rows = [m for m in rows if ql in " ".join(str(m.get(c) or "") for c in ("title", "activity", "stakeholder_org", "agenda", "summary", "follow_up", "participants")).lower()]
    st.markdown(f'<div class="card-meta" style="margin:.2rem 0 .4rem 0">{year}년 회의록 {len(rows)}건 · 최근 회의가 위에 옵니다.</div>', unsafe_allow_html=True)
    meeting_matrix(rows)
    st.caption("회의록·후속조치를 고치거나 지우려면 [데이터 편집·저장] 탭의 '회의록'·'회의 후속조치' 표를 이용하세요. "
               f"파일은 {storage.rel(storage.csv_path('meetings'))} 와 {storage.rel(storage.minutes_dir())} 에 저장됩니다.")


# ───────────────────────── 4. 사업관리 › 이해관계자 (v0.7) ─────────────────────────
def _sh_photo_cell(r: dict):
    """사진 칸 — 없으면 [업로드], 있으면 [사진보기] (보기 창 안에서 바꾸기·지우기)"""
    sid, f = r["stakeholder_id"], stakeholders.photo_file(r)
    if f is None:
        with st.popover("업로드", width="stretch"):
            up = st.file_uploader("사진 파일 (jpg·png)", type=["jpg", "jpeg", "png", "gif", "webp"], key=f"sh_up_{sid}", label_visibility="collapsed")
            if up is not None:
                ok, msg = stakeholders.save_photo(sid, up.name, up.getvalue())
                st.session_state["flash"] = (ok, msg if not ok else f"{sid} 사진을 저장했습니다.")
                st.rerun()
        return
    with st.popover("사진보기", width="stretch"):
        st.image(str(f), caption=f"{r.get('person_name') or r.get('org')} · {f.name}", width=320)
        up = st.file_uploader("다른 사진으로 바꾸기", type=["jpg", "jpeg", "png", "gif", "webp"], key=f"sh_re_{sid}")
        if up is not None:
            ok, msg = stakeholders.save_photo(sid, up.name, up.getvalue())
            st.session_state["flash"] = (ok, msg if not ok else f"{sid} 사진을 바꿨습니다.")
            st.rerun()
        if st.button("사진 지우기", key=f"sh_del_{sid}"):
            stakeholders.delete_photo(sid)
            st.session_state["flash"] = (True, f"{sid} 사진을 지웠습니다.")
            st.rerun()


def _sh_note_cell(r: dict):
    """비고 칸 — 버튼을 누르면 메모 칸이 열린다. 저장하면 바로 파일에 반영"""
    sid, note = r["stakeholder_id"], str(r.get("note") or "")
    with st.popover("비고 ●" if note.strip() else "비고", width="stretch", help=note[:200] if note.strip() else "메모를 남길 수 있습니다"):
        txt = st.text_area("비고", value=note, height=200, width=560, key=f"sh_note_{sid}", placeholder="연락 이력, 성향, 주의할 점 등 자유롭게 적어 두세요.")
        c1, c2 = st.columns([1, 2])
        if c1.button("저장", type="primary", key=f"sh_note_save_{sid}", width="stretch"):
            ok, msg = storage.update_cell(stakeholders.TABLE, "stakeholder_id", sid, "note", txt.strip())
            st.session_state["flash"] = (ok, msg)
            st.rerun()
        if note.strip():
            c2.caption(f"{len(note)}자")


def stakeholders_view(data: list[dict], extras: list[str]):
    """보기 모드 — 한 사람 한 줄, 맨 끝에 비고·사진 버튼"""
    heads = ["구분", "기관 · 부서", "담당자 · 직위", "휴대전화", "이메일"] + extras + ["비고", "사진"]
    widths = [0.85, 1.55, 1.25, 1.1, 1.45] + [1.0] * len(extras) + [1.0, 1.3]
    with st.container(border=True, key="sh_grid"):
        for c, h in zip(st.columns(widths), heads):
            c.markdown(f'<div class="mt-h">{esc(h)}</div>', unsafe_allow_html=True)
        if not data:
            st.markdown('<div class="card-meta" style="padding:1rem .3rem">등록된 이해관계자가 없습니다. [수정하기] › [행 추가]로 등록하세요.</div>', unsafe_allow_html=True)
        for r in data:
            st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
            cols = st.columns(widths, vertical_alignment="center")
            cols[0].markdown(f'<div class="mt-c">{esc(r.get("category") or "-")}<br><span class="card-meta">{esc(r["stakeholder_id"])}</span></div>', unsafe_allow_html=True)
            cols[1].markdown(f'<div class="mt-c"><b>{esc(r.get("org") or "")}</b>' + (f'<br>{esc(r["dept"])}' if r.get("dept") else "") + "</div>", unsafe_allow_html=True)
            period = " ~ ".join(x for x in (str(r.get("valid_from") or ""), str(r.get("valid_to") or "")) if x) if (r.get("valid_from") or r.get("valid_to")) else ""
            cols[2].markdown(f'<div class="mt-c"><b>{esc(r.get("person_name") or "")}</b>' + (f' <span class="card-meta">{esc(r["position"])}</span>' if r.get("position") else "")
                             + (f'<br><span class="card-meta">{esc(period)}</span>' if period else "") + "</div>", unsafe_allow_html=True)
            cols[3].markdown(f'<div class="mt-c"><span class="nowrap">{esc(r.get("phone") or "")}</span></div>', unsafe_allow_html=True)
            em = str(r.get("email") or "")
            cols[4].markdown(f'<div class="mt-c">{f"<a href=\"mailto:{esc(em)}\">{esc(em)}</a>" if em else ""}</div>', unsafe_allow_html=True)
            for k, c in enumerate(extras):
                cols[5 + k].markdown(f'<div class="mt-c">{_nl(str(r.get(c) or ""))}</div>', unsafe_allow_html=True)
            with cols[5 + len(extras)]:
                _sh_note_cell(r)
            with cols[6 + len(extras)]:
                _sh_photo_cell(r)


def stakeholders_edit(extras: list[str]):
    """편집 모드 — [행 추가][선택 행 삭제][열 추가][열 삭제] + 엑셀형 편집표 + [저장하기][취소]"""
    ver = st.session_state.get("sh_ver", 0)
    cols = stakeholders.EDIT_COLS + extras
    if "sh_base" not in st.session_state:
        df = pd.DataFrame(stakeholders.rows())
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df = df[cols] if len(df) else pd.DataFrame(columns=cols)
        df.insert(0, "삭제", False)
        st.session_state["sh_base"] = df
    base = st.session_state["sh_base"]

    st.markdown('<div class="card-meta">칸을 눌러 바로 고칠 수 있습니다. 행을 지우려면 왼쪽 [삭제]에 표시한 뒤 [선택 행 삭제]. '
                '[열 추가]·[열 삭제]는 누르는 즉시 파일에 반영되고, 나머지는 [저장하기]를 눌러야 저장됩니다.</div>', unsafe_allow_html=True)
    cfg = {"삭제": st.column_config.CheckboxColumn("삭제", width="small", default=False),
           "stakeholder_id": st.column_config.TextColumn("관계자ID", help="비워 두면 저장할 때 자동으로 번호가 붙습니다", width="small"),
           "valid_from": st.column_config.TextColumn("시작일", help="YYYY-MM-DD"), "valid_to": st.column_config.TextColumn("종료일", help="YYYY-MM-DD"),
           "note": st.column_config.TextColumn("비고", width="large")}
    for c in cols:
        cfg.setdefault(c, st.column_config.TextColumn(stakeholders.label(c)))
    edited = st.data_editor(base, num_rows="fixed", column_config=cfg, hide_index=True, width="stretch", row_height=44,
                            height=min(44 * (len(base) + 1) + 8, 900), key=f"sh_ed_{ver}")

    b1, b2, b3, b4, _, b5, b6 = st.columns([1, 1.25, 1, 1, 1.2, 1.1, 0.8], vertical_alignment="center")
    if b1.button("행 추가", key="sh_add_row", width="stretch"):
        new = {c: "" for c in edited.columns}
        new.update({"삭제": False, "stakeholder_id": stakeholders.next_id([str(x) for x in edited["stakeholder_id"]]), "valid_from": date.today().isoformat()})
        st.session_state["sh_base"] = pd.concat([edited, pd.DataFrame([new])], ignore_index=True)
        st.session_state["sh_ver"] = ver + 1
        st.rerun()
    if b2.button("선택 행 삭제", key="sh_del_rows", width="stretch"):
        sel = edited["삭제"].fillna(False).astype(bool)
        if not sel.any():
            st.warning("지울 행의 [삭제] 칸에 먼저 표시해 주세요.")
        else:
            st.session_state["sh_base"] = edited[~sel].reset_index(drop=True)
            st.session_state["sh_ver"] = ver + 1
            st.rerun()
    with b3.popover("열 추가", width="stretch"):
        name = st.text_input("새 열 이름", placeholder="예: 직통전화, 담당 업무", key="sh_new_col")
        if st.button("추가", type="primary", key="sh_new_col_btn"):
            ok, msg = storage.add_column(stakeholders.TABLE, name)
            if ok:
                col = msg.split("'")[1]
                edited[col] = ""
                st.session_state["sh_base"] = edited
                st.session_state["sh_ver"] = ver + 1
                st.session_state["flash"] = (True, msg)
                st.rerun()
            st.error(msg)
    with b4.popover("열 삭제", width="stretch"):
        if not extras:
            st.caption("지울 수 있는 열이 없습니다. 기본 열(구분·기관·담당자·휴대전화·이메일 등)은 지울 수 없습니다.")
        else:
            col = st.selectbox("지울 열", extras, key="sh_drop_col")
            sure = st.checkbox("이 열의 내용도 함께 지워집니다. 확인했습니다.", key="sh_drop_sure")
            if st.button("지우기", type="primary", disabled=not sure, key="sh_drop_btn"):
                ok, msg = storage.drop_column(stakeholders.TABLE, col)
                if ok:
                    st.session_state["sh_base"] = edited.drop(columns=[col], errors="ignore")
                    st.session_state["sh_ver"] = ver + 1
                st.session_state["flash"] = (ok, msg)
                st.rerun()
    if b5.button("저장하기", type="primary", key="sh_save", width="stretch"):
        ok, msg = stakeholders.save(edited.drop(columns=["삭제"]))
        if ok:
            st.session_state["flash"] = (True, msg)
            st.session_state["sh_edit"] = False
            st.session_state.pop("sh_base", None)
            st.session_state["sh_ver"] = ver + 1
            st.rerun()
        st.error(msg)
    if b6.button("취소", key="sh_cancel", width="stretch"):
        st.session_state["sh_edit"] = False
        st.session_state.pop("sh_base", None)
        st.rerun()


def stakeholders_tab():
    show_flash()
    data, extras = stakeholders.rows(), stakeholders.extra_columns()
    orgs = len({r.get("org") for r in data if r.get("org")})
    h1, h2, h3 = st.columns([3.4, 1.4, 1.2], vertical_alignment="center")
    h1.markdown(f'<div class="card-title" style="font-size:1.35rem">이해관계자 <span class="mt-cnt">{len(data)}명 · {orgs}개 기관</span></div>', unsafe_allow_html=True)
    try:
        xlsx, xerr = stakeholders.build_xlsx(), None
    except Exception as ex:                                   # openpyxl 이 없어도 화면은 계속
        xlsx, xerr = b"", f"엑셀을 만들지 못했습니다: {ex}"
    h2.download_button("엑셀로 다운로드", xlsx, f"이해관계자_{date.today():%Y%m%d}.xlsx", stakeholders.XLSX_MIME, width="stretch", key="sh_xlsx",
                       disabled=not xlsx, help=xerr or "명단 전체(비고·사진 포함)를 엑셀 파일로 내려받습니다")
    editing = st.session_state.get("sh_edit", False)
    if not editing and h3.button("수정하기", type="primary", width="stretch", key="sh_edit_btn"):
        st.session_state["sh_edit"] = True
        st.session_state.pop("sh_base", None)
        st.rerun()
    if editing:
        stakeholders_edit(extras)
    else:
        stakeholders_view(data, extras)
        st.caption(f"파일: {storage.rel(storage.csv_path('stakeholders'))} · 사진: {storage.rel(stakeholders.photo_dir())} — 엑셀에서 열을 더해 저장해도 그대로 반영됩니다.")


# ───────────────────────── 4. 사업관리 › 주간업무보고 (v0.5) ─────────────────────────
@st.dialog("주간업무 입력", width="large")
def weekly_entry_dialog(monday: date, role: str):
    """칸 버튼을 누르면 뜨는 간이 입력창 — 이미 입력된 내용이 있으면 채워서 보여준다"""
    cur = weekly.get_entry(monday, role) or {}
    st.markdown(f'{badge(role, "blue")}{badge(weekly.label(monday, True), "gray")}<div class="card-meta">{esc(weekly.range_text(monday))}'
                + (f' · 마지막 저장 {esc(cur.get("updated_at"))}' if cur else "") + "</div>", unsafe_allow_html=True)
    k = f"{monday.isoformat()}_{role}"
    c1, c2 = st.columns(2)
    author = c1.text_input("작성자 이름", value=cur.get("author", ""), key=f"we_a_{k}")
    position = c2.text_input("직책", value=cur.get("position", ""), key=f"we_p_{k}")
    content = st.text_area(f"{weekly.label(monday)} 활동내용", value=cur.get("content", ""), height=240, key=f"we_c_{k}",
                           placeholder="이번 주에 한 일·진행 상황·다음 주 계획·이슈를 적어 주세요.")
    b1, b2, b3, _ = st.columns([1, 1, 1, 2])
    if b1.button("저장", type="primary", width="stretch", key=f"we_s_{k}"):
        if not content.strip():
            st.error("활동내용을 입력해 주세요. (칸을 비우려면 [지우기])")
        else:
            st.session_state["flash"] = (True, weekly.save_entry(monday, role, author, position, content))
            st.rerun()
    if cur and b2.button("지우기", width="stretch", key=f"we_d_{k}"):
        st.session_state["flash"] = (True, weekly.delete_entry(monday, role))
        st.rerun()
    if b3.button("닫기", width="stretch", key=f"we_x_{k}"):
        st.rerun()


@st.dialog("주간업무보고 리포트", width="large")
def weekly_report_dialog(monday: date):
    """그 주차의 모든 칸을 리포트 형식으로 — 화면 미리보기 + Word/PDF 다운로드"""
    rows = weekly.report_rows(monday)
    title, period = weekly.label(monday, True), weekly.range_text(monday)
    st.markdown(f'<div class="card-title" style="font-size:1.3rem">주간업무보고 — {esc(title)}</div><div class="card-meta">{esc(period)}</div>', unsafe_allow_html=True)
    h = ['<table class="wk-tbl"><tr><th>구분</th><th>작성자</th><th>직책</th><th>활동내용</th></tr>']
    for r in rows:
        h.append(f'<tr><td class="r">{esc(r["role"])}</td><td>{esc(r["author"])}</td><td>{esc(r["position"])}</td><td>{_nl(r["content"]) or "-"}</td></tr>')
    st.markdown("".join(h) + "</table>", unsafe_allow_html=True)
    filled = sum(1 for r in rows if r["content"])
    st.caption(f"{len(rows)}칸 중 {filled}칸 입력됨. 비어 있는 칸은 '-'로 나갑니다.")
    docx, e1 = _doc_bytes(lambda t, rr: minutes_doc.build_weekly_docx(t, rr, period), title, rows)
    pdf, e2 = _doc_bytes(lambda t, rr: minutes_doc.build_weekly_pdf(t, rr, period), title, rows)
    stem = weekly.file_stem(monday)
    b1, b2, b3, _ = st.columns([1.3, 1.3, 0.8, 1.6])
    b1.download_button("Word로 다운받기", docx or b"", f"{stem}.docx", minutes_doc.DOCX_MIME, width="stretch", disabled=not docx, key=f"wr_docx_{monday}")
    b2.download_button("PDF로 다운로드", pdf or b"", f"{stem}.pdf", minutes_doc.PDF_MIME, width="stretch", disabled=not pdf, key=f"wr_pdf_{monday}")
    if b3.button("닫기", width="stretch", key=f"wr_x_{monday}"):
        st.rerun()
    if e1 or e2:
        st.warning(e1 or e2)


def weekly_tab():
    show_flash()
    cols_cfg = weekly.cfg()["columns"]
    h1, h2 = st.columns([4, 1.3], vertical_alignment="center")
    h1.markdown('<div class="card-title" style="font-size:1.35rem">주간업무보고</div>'
                '<div class="card-meta">칸을 누르면 입력창이 뜹니다. 내용이 있는 칸은 초록색으로 표시되고, 마지막 열 [리포트]로 그 주차 보고서를 만듭니다.</div>', unsafe_allow_html=True)
    years = [f"{y}년" for y in weekly.years()]
    default = f"{date.today().year}년" if f"{date.today().year}년" in years else years[0]
    sel = st.segmented_control("연도", years, default=default, key="wk_year_ctl", label_visibility="collapsed") or default
    year = int(sel[:4])
    weeks = weekly.weeks_of_year(year)
    data = weekly.entries_by_week(year)
    this_monday = weekly.monday_of(date.today())
    widths = [1.0, 1.75] + [1.0] * len(cols_cfg) + [0.95]
    with st.container(border=True):
        for c, name in zip(st.columns(widths), ["주차", "해당 일자"] + cols_cfg + ["리포트"]):
            c.markdown(f'<div class="wk-h">{esc(name)}</div>', unsafe_allow_html=True)
        if not weeks:
            st.info("이 연도에는 표시할 주차가 없습니다. config/settings.yaml 의 weekly.start 를 확인해 주세요.")
        for mon in weeks:
            ws = mon.isoformat()
            st.markdown('<hr class="wk-hr">', unsafe_allow_html=True)
            cs = st.columns(widths, vertical_alignment="center")
            now = mon == this_monday
            cs[0].markdown(f'<div class="wk-lab {"now" if now else ""}">{esc(weekly.label(mon))}{" ★" if now else ""}</div>', unsafe_allow_html=True)
            cs[1].markdown(f'<div class="wk-dt">{esc(weekly.range_text(mon))}</div>', unsafe_allow_html=True)
            e = data.get(ws, {})
            for c, role in zip(cs[2:], cols_cfg):
                cur = e.get(role)
                kind = "wkf" if cur else "wke"
                with c.container(key=f"{kind}_{ws}_{role}"):
                    lab = ("✓ " + (cur["author"] or "작성").replace("[예시] ", "")[:5]) if cur else "＋"
                    if st.button(lab, key=f"wkb_{ws}_{role}", width="stretch", help=f"{weekly.label(mon)} · {role}" + (f" · {cur['author']}" if cur else " · 입력")):
                        weekly_entry_dialog(mon, role)
            with cs[-1].container(key=f"wkr_{ws}"):
                if st.button("리포트", key=f"wkrb_{ws}", width="stretch", disabled=not e, help="이 주차 보고서 미리보기·Word·PDF"):
                    weekly_report_dialog(mon)
    st.caption(f"칸 이름(PM·PAO·현지직원·국내활동)은 config/settings.yaml 의 weekly.columns 에서 바꿀 수 있습니다. "
               f"저장 위치: {storage.rel(storage.csv_path('weekly_entries'))} · 주차별 검색용 문서: {storage.rel(weekly.docs_dir())}")


# ───────────────────────── 5. 성과관리 › 사업산출물 (v0.5): PDM 폴더 원문을 엑셀형 표로 + 우측 하단 수정하기 ─────────────────────────
def excel_table(key: str, tbl: str, view=None, edit_df=None, save_fn=None, caption: str = ""):
    """보기 모드: 표(또는 view()) + 우측 하단 [수정하기] → 편집 모드: 엑셀형 편집표(행 추가·수정) + [저장][취소]"""
    flag, ver = f"edit_{key}", st.session_state.get(f"ver_{key}", 0)
    if not st.session_state.get(flag):
        if view is not None:
            view()
        else:
            show_df(labeled(table(f"SELECT * FROM {tbl}"), tbl), fit=True)
        _, b = st.columns([5, 1.25])
        if b.button("수정하기", key=f"btn_{key}", width="stretch"):
            st.session_state[flag] = True
            st.rerun()
        if caption:
            st.caption(caption)
        return
    df = edit_df() if edit_df is not None else table(f"SELECT * FROM {tbl}")
    st.markdown('<div class="card-meta">엑셀처럼 칸을 눌러 고치고, 맨 아래 빈 줄에 입력하면 행이 추가됩니다. 행을 지우려면 왼쪽 체크 후 Delete 키. 여러 줄은 Shift+Enter.</div>', unsafe_allow_html=True)
    edited = st.data_editor(df, num_rows="dynamic", column_config=editor_cfg(tbl, df), hide_index=True, width="stretch", row_height=44,
                            height=min(44 * (len(df) + 2) + 6, 900), key=f"ed_{key}_{ver}")
    _, b1, b2 = st.columns([4, 1.25, 1])
    if b1.button("저장", type="primary", key=f"save_{key}", width="stretch"):
        ok, msg = (save_fn or (lambda d: storage.save_table(tbl, d)))(edited)
        if ok:
            st.session_state["flash"] = (True, msg)
            st.session_state[flag] = False
            st.session_state[f"ver_{key}"] = ver + 1
            st.rerun()
        st.error(msg)
    if b2.button("취소", key=f"cancel_{key}", width="stretch"):
        st.session_state[flag] = False
        st.rerun()


def pdm_matrix_view(version: int = 1):
    """사업논리모형(PDM) — 원문 양식 그대로(요약·검증지표·검증수단·중요가정) + 제안서의 '검증지표 추가제안' 열"""
    rows = storage.pdm_rows(version).fillna("").to_dict("records")
    info = [r for r in rows if r["level"] == "기본정보"]
    if info:
        st.markdown('<div class="kv wide">' + "".join(f"<b>{esc(r['code'])}</b><span>{esc(r['summary'])}{(' <span class=card-meta>· ' + esc(r['note']) + '</span>') if r['note'] else ''}</span>" for r in info) + "</div>",
                    unsafe_allow_html=True)
    h = ['<div class="scroll-x"><table class="pdm"><tr><th style="width:24%">Narrative Summary<small>요약</small></th><th style="width:24%">Objectively Verifiable Indicators<small>객관적 검증지표</small></th>'
         '<th style="width:16%">Means of Verification<small>검증수단</small></th><th style="width:18%">Important Assumptions<small>중요가정</small></th><th style="width:18%">검증지표 추가제안<small>제안서 양식</small></th></tr>']
    for lv, title in [("영향(Impact)", "Impacts (영향)"), ("성과(Outcome)", "Outcomes (성과)"), ("산출물(Output)", "Outputs (산출물)")]:
        sec = [r for r in rows if r["level"] == lv]
        if not sec:
            continue
        h.append(f'<tr><td class="sec" colspan="5">{esc(title)}</td></tr>')
        for r in sec:
            h.append(f'<tr><td>{("<b>" + esc(r["code"]) + ".</b> ") if r["code"] else ""}{_nl(r["summary"])}</td><td>{_nl(r["indicators"])}</td>'
                     f'<td>{_nl(r["mov"])}</td><td>{_nl(r["assumptions"])}</td><td class="prop">{_nl(r["proposal"]) or "<span class=card-meta>(제안 작성란)</span>"}</td></tr>')
    acts = [r for r in rows if r["level"] == "활동(Activity)"]
    inputs = [r for r in rows if r["level"] == "투입물(Input)"]
    pres = [r for r in rows if r["level"] == "선행조건(Pre-condition)"]
    if acts or inputs or pres:
        h.append('<tr><td class="sec">Activities (활동)</td><td class="sec" colspan="2">Inputs (투입물)</td><td class="sec">Pre-conditions (선행조건)</td><td class="sec">검증지표 추가제안</td></tr>')
        a = "<br>".join(f"<b>{esc(r['code'])}.</b> {esc(r['summary'])}" for r in acts)
        i = "".join(f"<b>{esc(r['code'])}</b><br>{_nl(r['summary'])}<br>" for r in inputs)
        pr = "<br>".join(_nl(r["summary"]) for r in pres)
        pp = "<br>".join(_nl(r["proposal"]) for r in acts + inputs + pres if r["proposal"])
        h.append(f'<tr><td>{a}</td><td colspan="2">{i}</td><td>{pr}</td><td class="prop">{pp or "<span class=card-meta>(제안 작성란)</span>"}</td></tr>')
    h.append("</table></div>")
    st.markdown("".join(h), unsafe_allow_html=True)


def change_model_view():
    """사업변화모델 — 결과(영향) → 변화(성과) → 변화(산출물) → 수단(활동) 트리"""
    rows = table("SELECT * FROM change_model ORDER BY seq, id").fillna("").to_dict("records")
    by_parent = {}
    for r in rows:
        by_parent.setdefault(r["parent_code"], []).append(r)
    roots = [r for r in rows if r["stage"] == "결과(영향)"] or [r for r in rows if not r["parent_code"]]
    for root in roots:
        st.markdown(f'<div class="tc-lab">결과(영향)</div><div class="tc-imp">{esc(root["content"])}</div><div class="tc-arrow">▲</div>', unsafe_allow_html=True)
        outs = by_parent.get(root["code"], [])
        st.markdown('<div class="tc-lab">변화(성과) → 변화(산출물) → 수단(활동)</div>', unsafe_allow_html=True)
        for col, o in zip(st.columns(max(len(outs), 1)), outs):
            html_ = [f'<div class="tc-box tc-out"><b>{esc(o["code"])}.</b> {esc(o["content"])}</div>']
            for n, op in enumerate(by_parent.get(o["code"], [])):
                html_.append(('<div class="tc-arrow">▲</div>' if n == 0 else '<div style="height:.5rem"></div>') + f'<div class="tc-box"><b>{esc(op["code"])}</b> {esc(op["content"])}</div>')
                for a in by_parent.get(op["code"], []):
                    html_.append(f'<div class="tc-box tc-act">↳ <b>{esc(a["code"])}</b> {esc(a["content"])}</div>')
            col.markdown("".join(html_), unsafe_allow_html=True)
    orphans = [r for r in rows if r["parent_code"] and r["parent_code"] not in {x["code"] for x in rows}]
    if orphans:
        st.warning("상위코드가 맞지 않아 트리에 못 넣은 항목: " + ", ".join(f"{r['code']} {r['content'][:20]}" for r in orphans))


def pdm_source_files_view():
    files = storage.pdm_source_files()
    if not files:
        st.info("pmc/99. pre/2. PDM 폴더에 파일이 없습니다.")
        return
    img_only = {"PDF-안.pdf", "사업논리모형(PDM)제안.pdf", "0. 작성필요 문서.pdf"}
    what = {"1. PDM.pdf": "사업논리모형(PDM) 원문 — 위 '사업논리모형(PDM)' 표의 출처", "2. 성과점검표.pdf": "모니터링 매트릭스·연간 성과점검표 — '성과점검표' 표의 출처",
            "3. 사업변화모델.pdf": "결과·변화·수단 트리 — '사업변화모델' 표의 출처", "사업논리모형(PDM)제안.pdf": "제안서 초안 페이지(그림) — '검증지표 추가제안' 칸이 비어 있음",
            "PDF-안.pdf": "제안서 초안 페이지(그림)", "0. 작성필요 문서.pdf": "제안서에서 작성해야 할 문서 목록(그림) — Output 2.2·3.1·3.2 각 12P + PDM 제안",
            "성과관리양식_v3.2_final.xlsx": "KOICA 성과관리양식 v3.2 (개요 · 1. PDM · 2. 성과점검표) — [성과점검표] 탭 배치의 원본"}
    for f in files:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.1], vertical_alignment="center")
            c1.markdown(f'<div class="card-title">{esc(f.name)}</div><div class="card-meta">{esc(what.get(f.name, ""))} · {f.stat().st_size // 1024} KB'
                        + (" · 글자가 없는 그림 PDF라 AI 검색 색인에서는 제외됨" if f.name in img_only else " · AI 사업비서 검색에 색인됨") + "</div>", unsafe_allow_html=True)
            c2.download_button("⬇️ 내려받기", f.read_bytes(), f.name, key=f"pdmf_{f.name}", width="stretch")
    open_folder_button(files[0].parent, key="open_pdm_src")


def pdm_section(ns: str = "pdm"):
    """사업논리모형(PDM) — 버전 탭 · [새로운 버전 추가](마지막 버전 복사 → 바로 수정) · 버전 정보 · 표 · 내려받기 · 근거자료 업로드
    ns: 위젯 키 접두어 — 같은 화면의 두 탭([사업산출물]·[PDM 지표])에서 각각 그릴 수 있게 한다"""
    vers = storage.pdm_versions()
    nums = [v["version"] for v in vers]
    cur = st.session_state.get(f"{ns}_ver") if st.session_state.get(f"{ns}_ver") in nums else nums[-1]
    meta_of = {v["version"]: v for v in vers}
    col_s = {"초안": "org", "검토중": "blue", "확정": "green"}

    h1, h2 = st.columns([4, 1.4], vertical_alignment="center")
    with h1:
        sel = st.segmented_control("버전", nums, default=cur, key=f"{ns}_ver_ctl_{cur}_{len(nums)}",       # 선택이 바뀌면 새 위젯으로 다시 그려 강조 표시가 항상 맞게
                                   format_func=lambda v: f"v{v} · {meta_of[v]['status'] or '초안'}" + (f" ({meta_of[v]['created_at']})" if meta_of[v]["created_at"] else ""),
                                   label_visibility="collapsed") or cur
    if sel != cur:                                                   # 버전을 바꾸면 편집 모드는 닫는다
        st.session_state[f"edit_{ns}"] = False
    cur = sel
    st.session_state[f"{ns}_ver"] = cur
    if h2.button("새로운 버전 추가", type="primary", width="stretch", key=f"{ns}_add",
                 help=f"v{nums[-1]}의 내용을 그대로 복사해 v{nums[-1] + 1}을 만들고 바로 수정 상태로 엽니다"):
        new = storage.pdm_add_version()
        st.session_state[f"{ns}_ver"] = new
        st.session_state[f"edit_{ns}"] = True
        st.session_state["flash"] = (True, f"v{new}을(를) 만들었습니다 (v{new - 1} 복사본). 내용을 고친 뒤 [저장]을 누르세요.")
        st.rerun()

    meta = meta_of[cur]
    editing = st.session_state.get(f"edit_{ns}", False)
    meta_in = {}
    with st.container(border=True):
        if editing:                                                  # 편집 모드: 버전 정보도 같이 고친다
            c1, c2, c3, c4 = st.columns([1, 1.2, 1, 1])
            meta_in["status"] = c1.selectbox("상태", storage.PDM_STATUS, index=storage.PDM_STATUS.index(meta["status"]) if meta["status"] in storage.PDM_STATUS else 0, key=f"{ns}_pv_st_{cur}")
            meta_in["author"] = c2.text_input("작성자", value=meta["author"] or "", key=f"{ns}_pv_au_{cur}")
            meta_in["approved_at"] = c3.text_input("승인일", value=meta["approved_at"] or "", placeholder="2026-12-01", key=f"{ns}_pv_ap_{cur}")
            meta_in["note"] = c4.text_input("비고", value=meta["note"] or "", key=f"{ns}_pv_no_{cur}")
            meta_in["reason"] = st.text_area("변경 사유 · 주요 변경 내용", value=meta["reason"] or "", height=80, key=f"{ns}_pv_re_{cur}")
        else:
            st.markdown(f'{badge(f"v{cur}")}{badge(meta["status"] or "초안", col_s.get(meta["status"], "gray"))}'
                        f'<span class="card-meta">생성 {esc(meta["created_at"] or "-")} · 작성자 {esc(meta["author"] or "-")} · 승인일 {esc(meta["approved_at"] or "-")}'
                        + (f' · {esc(meta["note"])}' if meta["note"] else "") + "</span>"
                        f'<div style="margin-top:.4rem"><b>변경 사유</b> {_nl(meta["reason"] or "(없음)")}</div>', unsafe_allow_html=True)

    excel_table(ns, "pdm_matrix", view=lambda: pdm_matrix_view(cur), edit_df=lambda: storage.pdm_rows(cur).drop(columns=["version"]),
                save_fn=lambda df: storage.pdm_save_version(cur, df, meta_in),
                caption=f"v1 출처: pmc/99. pre/2. PDM/1. PDM.pdf (2026-01-15 작성본). 모든 버전은 {storage.rel(storage.csv_path('pdm_matrix'))} 한 파일에 '버전' 열로 구분되어 저장되고, "
                        f"버전 이력은 {storage.rel(storage.csv_path('pdm_versions'))} 에 남습니다. '검증지표 추가제안' 열은 노란 칸으로 표시됩니다.")

    if not editing:                                                  # ⬇️ 이 버전 내려받기 (Excel · Word · PDF)
        rows_ = storage.pdm_rows(cur).fillna("").to_dict("records")
        stem = pdm_doc.file_stem(cur, meta)
        x, e1 = _doc_bytes(lambda a, b: pdm_doc.build_xlsx(cur, a, b, vers, storage.pdm_evidence(cur)), rows_, meta)
        w, e2 = _doc_bytes(lambda a, b: pdm_doc.build_docx(cur, a, b), rows_, meta)
        f, e3 = _doc_bytes(lambda a, b: pdm_doc.build_pdf(cur, a, b), rows_, meta)
        d0, d1, d2, d3, _ = st.columns([1.6, 1.15, 1.15, 1.15, 1.2], vertical_alignment="center")
        d0.markdown(f'<div class="card-title" style="margin:0">⬇️ v{cur} 내려받기</div><div class="card-meta">PDM 양식 그대로</div>', unsafe_allow_html=True)
        d1.download_button("Excel", x or b"", f"{stem}.xlsx", pdm_doc.XLSX_MIME, key=f"{ns}_dl_x_{cur}", width="stretch", disabled=not x)
        d2.download_button("Word", w or b"", f"{stem}.docx", minutes_doc.DOCX_MIME, key=f"{ns}_dl_w_{cur}", width="stretch", disabled=not w)
        d3.download_button("PDF", f or b"", f"{stem}.pdf", minutes_doc.PDF_MIME, key=f"{ns}_dl_p_{cur}", width="stretch", disabled=not f)
        if e1 or e2 or e3:
            st.warning(e1 or e2 or e3)

    if not editing and cur == nums[-1] and cur > 1:                 # 마지막 버전만 지울 수 있다
        _, d1, d2 = st.columns([4, 1.4, 1.25])
        ok_del = d1.checkbox(f"v{cur} 삭제 확인", key=f"{ns}_pdm_delok_{cur}")
        if d2.button(f"v{cur} 삭제", key=f"{ns}_pdm_del_{cur}", width="stretch", disabled=not ok_del):
            ok, msg = storage.pdm_delete_version(cur)
            st.session_state["flash"] = (ok, msg)
            st.session_state[f"{ns}_ver"] = cur - 1
            st.rerun()

    # ── 하단: 버전 근거자료 ──
    st.markdown(f'<div class="card-title" style="margin-top:1rem"> v{cur} 근거자료</div>'
                '<div class="card-meta">이 버전을 만들거나 바꾼 근거(회의록·공문·조사 결과·검토 의견 등)를 올려 두세요. 올린 파일은 AI 사업비서 검색에도 포함됩니다.</div>',
                unsafe_allow_html=True)
    with st.container(border=True):
        with st.form(f"{ns}_pdm_ev_form_{cur}", clear_on_submit=True, border=False):
            ups = st.file_uploader("근거 파일 (여러 개 가능)", accept_multiple_files=True, key=f"{ns}_pdm_ev_up_{cur}")
            note = st.text_input("설명 (선택)", placeholder="예: 2027-03 PSC 회의에서 지표 1-1 정의 수정 합의", key=f"{ns}_pdm_ev_note_{cur}")
            if st.form_submit_button("근거자료 저장", type="primary"):
                if ups:
                    n = storage.pdm_add_evidence(cur, [(u.name, u.getvalue()) for u in ups], note.strip())
                    st.session_state["flash"] = (True, f"근거자료 {n}개를 저장했습니다 → {storage.rel(storage.pdm_evidence_dir(cur))}")
                    st.rerun()
                st.error("파일을 선택해 주세요.")
        evs = storage.pdm_evidence(cur)
        for e in evs:
            c1, c2, c3 = st.columns([4, 1, 0.7], vertical_alignment="center")
            c1.markdown(f'<div class="mt-c"> <b>{esc(e["file_name"])}</b>' + (f' — {esc(e["note"])}' if e["note"] else "")
                        + f'<br><span class="card-meta">{esc(e["uploaded_at"])}</span></div>', unsafe_allow_html=True)
            fp = ROOT / str(e["file_path"]) if e["file_path"] else None
            if fp and fp.exists():
                c2.download_button("⬇️ 내려받기", fp.read_bytes(), fp.name, key=f"{ns}_ev_dl_{e['id']}", width="stretch")
            else:
                c2.caption("파일 없음")
            if c3.button("삭제", key=f"{ns}_ev_del_{e['id']}", help="이 근거자료 삭제", width="stretch"):
                storage.pdm_delete_evidence(e["id"])
                st.rerun()
        if not evs:
            st.caption("아직 올린 근거자료가 없습니다.")
        open_folder_button(storage.pdm_evidence_dir(cur), key=f"{ns}_open_pdm_ev_{cur}")


# ───────────────────────── 5. 성과관리 › 성과점검표 (KOICA 성과관리양식 v3.2 — '2. 성과점검표' 시트 배치) ─────────────────────────
PMS_COLS = [("지표명", "name"), ("지표 정의", "definition"), ("기초선 (Baseline)", "baseline"), ("목표치 (Target)", "target"), ("목표치 선정 근거", "target_basis"),
            ("데이터 출처", "data_source"), ("성과 측정 시기", "frequency"), ("데이터 수집 주체", "collector")]


def _g(v, unit: str = "") -> str:
    """숫자 표시: 25 → '25', 12.5 → '12.5', 없으면 ''"""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return ""
    try:
        return format(float(v), "g")
    except (TypeError, ValueError):
        return esc(v)


def wide_page():
    """표가 넓은 화면(3. 사업일정·5. 성과관리)은 본문 너비 제한(1400px)을 푼다"""
    st.markdown('<style>.block-container { max-width: 100% !important; padding-left: 1.6rem; padding-right: 1.6rem; }</style>', unsafe_allow_html=True)


def pms_view(fit: bool = True):
    """엑셀 양식 그대로: 왼쪽 '1. 모니터링 매트릭스'(지표 정의, 기초선·목표치 우측에 연도별(2027~2031) 목표치 칸 포함) + 오른쪽 '2. 연간 성과점검표'(구분 × 1~7차년도 · 누적 달성률 · 비고)
    fit=True 면 글자를 줄여 한 화면에 들어가게, False 면 원본 배치(가로 스크롤)"""
    meta = storage.pms_meta()
    grp = storage.pms_groups()
    ind = table("SELECT * FROM pdm_indicators ORDER BY CASE level WHEN 'Impact' THEN 0 WHEN 'Outcome' THEN 1 ELSE 2 END, indicator_id").to_dict("records")
    tg = {(r["indicator_id"], int(r["year"])): r for r in table("SELECT * FROM indicator_targets").to_dict("records")}
    av = {(r["indicator_id"], int(r["period"])): r for r in table("SELECT * FROM indicator_values").to_dict("records") if str(r["period"]).isdigit() and len(str(r["period"])) == 4}
    years = storage.YEARS
    interim_years = [] if fit else years[1:-1]  # 기초선(첫해)·목표치(끝해) 사이의 연도별 목표치 칸(2027~2031) — 한 화면 모드에서는 생략(③ 연간 목표치 행에 같은 값)
    matrix_cols = 9 + len(interim_years)   # 라벨 + PMS_COLS(8) + 연도별 목표치 칸
    annual_cols = 11
    total_cols = matrix_cols + annual_cols

    def num(v):
        return None if v is None or (isinstance(v, float) and pd.isna(v)) else float(v)

    def cell_target(iid, y):
        r = tg.get((iid, y))
        if r is None:
            return "<td></td>"
        v = num(r["target"])
        return f'<td class="num">{_g(v)}</td>' if v is not None else ('<td class="tbd">TBD</td>' if str(r.get("note") or "").upper().startswith("TBD") else "<td></td>")

    def cell_target_rs(iid, y):
        """연도별(2027~2031) 목표치 칸 — 매트릭스 쪽, 지표당 3행 병합. 값 자체는 ③ 연간 성과점검표 편집표(y{연도})에서 고친다."""
        r = tg.get((iid, y))
        if r is None:
            return '<td rowspan="3"></td>'
        v = num(r["target"])
        if v is not None:
            return f'<td rowspan="3" class="num">{_g(v)}</td>'
        return f'<td rowspan="3" class="tbd">TBD</td>' if str(r.get("note") or "").upper().startswith("TBD") else '<td rowspan="3"></td>'

    def head_rows(label):
        h = [f'<tr><th rowspan="2">{esc(label)}</th>'
             + "".join(f'<th rowspan="2">{esc(k)}</th>' for k, c in PMS_COLS[:2])
             + '<th rowspan="1">기초선 (Baseline)</th><th rowspan="1">목표치 (Target)</th>'
             + (f'<th colspan="{len(interim_years)}">연도별 목표치 (Target by Year)</th>' if interim_years else "")
             + "".join(f'<th rowspan="2">{esc(k)}</th>' for k, c in PMS_COLS[4:])
             + '<th rowspan="2">구분</th>' + "".join(f"<th>{i + 1}차년도</th>" for i in range(len(years)))
             + '<th rowspan="2">누적 달성률(%)</th><th rowspan="2">비고<br><small>(N/A 사유, 목표치 미달성 사유 등)</small></th></tr>']
        h.append(f"<tr><th>{years[0]}</th><th>{years[-1]}</th>" + "".join(f"<th>{y}</th>" for y in interim_years)
                 + "".join(f"<th>{y}</th>" for y in years) + "</tr>")
        return "".join(h)

    dates = " · ".join(f"{i}차년도 작성일: <b>{esc(meta.get(f'{i}차년도 작성일') or '____')}</b>" for i in range(1, len(years) + 1))
    h = [f'<div class="scroll-x{" fit" if fit else ""}"><table class="kpms{" fit" if fit else ""}">',
         f'<tr><th class="ttl" colspan="{matrix_cols}">1. 모니터링 매트릭스 (Monitoring Matrix)</th><th class="ttl" colspan="{annual_cols}">2. 연간 성과점검표 (Annual Performance Monitoring)</th></tr>',
         f'<tr><td class="hd" colspan="{matrix_cols}"><b>사업명(기간/예산):</b> {esc(meta.get("사업명(기간/예산)"))}<br>'
         '<span class="card-meta">백분율 지표는 반드시 정수값 데이터로 함께 명기, 기초선 및 목표치 수집데이터는 정수(N) 표기 · 기초선·목표치 우측 연도별(2027~2031) 목표치는 ③ 연간 성과점검표에서 고칩니다</span></td>'
         f'<td class="hd" colspan="{annual_cols}">{dates}<br><span class="card-meta">당해 연도 실적(performance data) 및 연간 목표치 작성</span></td></tr>']
    # 영향
    h.append(head_rows("영향 (Impacts)"))
    h.append(f'<tr><td class="imp" colspan="{total_cols}">{esc(grp["impact"])}</td></tr>')
    # 성과 · 산출물
    for level, label in (("Outcome", "성과 (Outcomes)"), ("Output", "산출물 (Outputs)")):
        rows = [r for r in ind if r["level"] == level]
        if not rows:
            continue
        h.append(head_rows(label))
        groups: dict[str, list] = {}
        for r in rows:
            if level == "Outcome":
                k = str(r["indicator_id"]).split("-")[0].strip()
                gname = f"{k}. {grp['outcomes'].get(k, '')}".strip(". ")
            else:
                k = str(r.get("output_id") or str(r["indicator_id"]).split("-")[0]).strip()
                gname = f"{k}. {grp['outputs'].get(k, '')}".strip(". ")
            groups.setdefault(gname, []).append(r)
        for gname, rs in groups.items():
            first_g = True
            for r in rs:
                iid, unit = r["indicator_id"], str(r.get("unit") or "")
                tgt, base = num(r["target"]), num(r["baseline"])
                actual = [num((av.get((iid, y)) or {}).get("value")) for y in years]
                vals = [v for v in actual if v is not None]
                cum = None if not vals or not tgt else (vals[-1] if unit == "%" else sum(vals)) / tgt * 100
                span = 3 * len(rs)
                left = (f'<td class="grp" rowspan="{span}">{esc(gname)}</td>' if first_g else "")
                first_g = False
                left += (f'<td class="ind" rowspan="3">{esc(iid)}. {esc(r["name"])}</td><td class="def" rowspan="3">{_nl(r.get("definition") or "")}</td>'
                         f'<td rowspan="3" class="{"tbd" if base is None else "num"}">{"TBD" if base is None else _g(base)}</td>'
                         f'<td rowspan="3" class="{"tbd" if tgt is None else "num"}">{"TBD" if tgt is None else _g(tgt)}</td>'
                         + "".join(cell_target_rs(iid, y) for y in interim_years)
                         + f'<td class="txt" rowspan="3">{_nl(r.get("target_basis") or "")}</td><td class="txt" rowspan="3">{_nl(r.get("data_source") or r.get("mov") or "")}</td>'
                         f'<td class="txt" rowspan="3">{_nl(r.get("frequency") or "")}</td><td class="txt" rowspan="3">{_nl(r.get("collector") or "")}</td>')
                h.append(f'<tr>{left}<td class="kind">연간 실적치</td>' + "".join(f'<td class="num">{_g(v)}</td>' for v in actual)
                         + f'<td rowspan="3" class="{"ok" if cum is not None and cum >= 100 else "num"}">{"" if cum is None else format(cum, ".0f") + "%"}</td>'
                         f'<td class="txt" rowspan="3">{_nl(r.get("remark") or "")}</td></tr>')
                h.append('<tr><td class="kind">연간 목표치</td>' + "".join(cell_target(iid, y) for y in years) + "</tr>")
                cells = []
                for y, v in zip(years, actual):
                    ty = num((tg.get((iid, y)) or {}).get("target"))
                    cells.append(f'<td class="num">{format(v / ty * 100, ".0f") + "%" if v is not None and ty else ""}</td>')
                h.append('<tr class="rate"><td class="kind">연간 달성률</td>' + "".join(cells) + "</tr>")
    h.append("</table></div>")
    st.markdown("".join(h), unsafe_allow_html=True)
    st.markdown('<div class="legend card-meta" style="margin-top:.3rem">TBD = 기초선 조사 시 확정 · 빈칸(Null) = 해당 연도가 데이터 수집시기가 아님 · 누적 달성률 = 실적 합계(백분율 지표는 최근 실적) ÷ 목표치</div>', unsafe_allow_html=True)


def pms_section(ns: str = "pms"):
    """성과점검표 보기 + 우측 하단 [수정하기] → 기본정보 · 모니터링 매트릭스 · 연간 실적/목표치 편집표 → [저장]"""
    flag, ver = f"edit_{ns}", st.session_state.get(f"ver_{ns}", 0)
    if not st.session_state.get(flag):
        v1, v2 = st.columns([3.2, 3], vertical_alignment="center")
        mode = v1.segmented_control("보기", ["한 화면에 맞추기", "원본 배치 (가로 스크롤)"], default="한 화면에 맞추기", key=f"fit_{ns}", label_visibility="collapsed")
        fit = mode != "원본 배치 (가로 스크롤)"
        if fit:
            v2.caption("한 화면 모드에서는 연도별(2027~2031) 목표치 칸을 생략합니다 — 같은 값이 오른쪽 '연간 목표치' 행에 있습니다.")
        pms_view(fit=fit)
        _, b = st.columns([5, 1.25])
        if b.button("수정하기", key=f"btn_{ns}", width="stretch"):
            st.session_state[flag] = True
            st.rerun()
        st.caption("KOICA 성과관리양식 v3.2의 '2. 성과점검표' 시트와 같은 배치입니다. 사업명·작성일, 지표 정의(모니터링 매트릭스), 연간 목표치·실적치·비고는 [수정하기]에서 한 번에 고칩니다. "
                   f"저장 위치: {storage.rel(storage.csv_path('pdm_indicators'))} · {storage.rel(storage.csv_path('indicator_targets'))} · {storage.rel(storage.csv_path('indicator_values'))} · {storage.rel(storage.csv_path('pms_meta'))}")
        return

    meta = storage.pms_meta()
    st.markdown('<div class="card-title">① 기본정보</div>', unsafe_allow_html=True)
    new_meta = {"사업명(기간/예산)": st.text_input("사업명(기간/예산)", value=meta.get("사업명(기간/예산)", ""), key=f"{ns}_m_title")}
    cols = st.columns(len(storage.YEARS))
    for i, c in enumerate(cols, 1):
        new_meta[f"{i}차년도 작성일"] = c.text_input(f"{i}차년도 작성일", value=meta.get(f"{i}차년도 작성일", ""), placeholder=f"{storage.YEARS[i - 1] + 1}-01-31", key=f"{ns}_m_d{i}")

    st.markdown('<div class="card-title" style="margin-top:.8rem">② 모니터링 매트릭스 — 지표명·정의·기초선·목표치·근거·출처·시기·주체·비고</div>'
                '<div class="card-meta">엑셀처럼 칸을 눌러 고치고, 맨 아래 빈 줄에 입력하면 지표가 추가됩니다(지표ID·수준·지표명은 필수). 기초선·목표치를 비우면 TBD로 표시됩니다.</div>', unsafe_allow_html=True)
    ind = table("SELECT * FROM pdm_indicators ORDER BY CASE level WHEN 'Impact' THEN 0 WHEN 'Outcome' THEN 1 ELSE 2 END, indicator_id")
    order = ["indicator_id", "level", "output_id", "name", "definition", "baseline", "target", "target_basis", "data_source", "frequency", "collector", "remark",
             "unit", "formula", "baseline_year", "target_year", "mov", "pdm_version", "origin"]
    ind = ind[[c for c in order if c in ind.columns] + [c for c in ind.columns if c not in order]]
    ed_ind = st.data_editor(ind, num_rows="dynamic", column_config=editor_cfg("pdm_indicators", ind), hide_index=True, width="stretch", row_height=44,
                            height=min(44 * (len(ind) + 2) + 6, 900), key=f"ed_{ns}_ind_{ver}")

    st.markdown('<div class="card-title" style="margin-top:.8rem">③ 연간 성과점검표 — 지표별 연간 목표치 · 연간 실적치 (1~7차년도)</div>'
                '<div class="card-meta">숫자만 입력합니다. 빈칸은 Null(수집시기 아님) 또는 TBD로 표시되고, 연간 달성률·누적 달성률은 자동 계산됩니다.</div>', unsafe_allow_html=True)
    yl = storage.indicator_years_long()
    ycfg = {"indicator_id": st.column_config.Column("지표ID", disabled=True), "name": st.column_config.Column("지표명", disabled=True, width="large"),
            "kind": st.column_config.Column("구분", disabled=True)}
    for i, y in enumerate(storage.YEARS, 1):
        ycfg[f"y{y}"] = st.column_config.NumberColumn(f"{i}차년도 ({y})", format="%g")
    ed_years = st.data_editor(yl, num_rows="fixed", column_config=ycfg, hide_index=True, width="stretch", row_height=40,
                              height=min(40 * (len(yl) + 2) + 6, 900), key=f"ed_{ns}_years_{ver}")

    _, b1, b2 = st.columns([4, 1.25, 1])
    if b1.button("저장", type="primary", key=f"save_{ns}", width="stretch"):
        storage.save_pms_meta(new_meta)
        ok, msg = storage.save_table("pdm_indicators", ed_ind)
        if ok:
            ok, msg2 = storage.save_indicator_years(ed_years)
            msg = f"{msg} · {msg2}"
        if ok:
            st.session_state["flash"] = (True, "성과점검표를 저장했습니다 — " + msg)
            st.session_state[flag] = False
            st.session_state[f"ver_{ns}"] = ver + 1
            st.rerun()
        st.error(msg)
    if b2.button("취소", key=f"cancel_{ns}", width="stretch"):
        st.session_state[flag] = False
        st.rerun()


def outputs_tab():
    """[5. 성과관리 › 사업산출물] — PDM 폴더 원문(사업산출물·PDM·성과점검표·사업변화모델·원문 파일)을 엑셀형 표로 보고 고친다"""
    show_flash()
    secs = ["사업산출물 (6개)", "사업논리모형 (PDM)", "성과점검표", "사업변화모델", "원문 파일 (2. PDM 폴더)"]
    sec = st.segmented_control("구분", secs, default=secs[0], key="po_sec", label_visibility="collapsed") or secs[0]
    if sec == secs[0]:
        def _v():
            show_df(labeled(table("SELECT o.output_id, o.name, o.outcome, o.description, o.implementer, o.deliverable, o.lead_expert, o.progress_pct, "
                                  "(SELECT COUNT(*) FROM sub_outputs s WHERE s.output_id=o.output_id) AS 보조산출물수, "
                                  "(SELECT COUNT(*) FROM sub_outputs s WHERE s.output_id=o.output_id AND s.status IN ('제출','승인')) AS 제출완료 FROM outputs o"), "outputs"), fit=True)
        excel_table("outputs", "outputs", view=_v, caption=f"저장 위치: {storage.rel(storage.csv_path('outputs'))} · 6개 산출물의 명칭·설명·수행기관·산출물 형태·책임전문가·진척률(%)")
    elif sec == secs[1]:
        pdm_section()
    elif sec == secs[2]:
        pms_section(ns="pms2")
    elif sec == secs[3]:
        excel_table("tc", "change_model", view=change_model_view, edit_df=lambda: table("SELECT * FROM change_model ORDER BY seq, id"),
                    caption=f"출처: pmc/99. pre/2. PDM/3. 사업변화모델.pdf → {storage.rel(storage.csv_path('change_model'))}. 항목을 추가할 때는 상위코드(parent_code)에 위 단계의 코드를 적으면 트리에 연결됩니다.")
    else:
        pdm_source_files_view()


# ───────────────────────── 왼쪽 메뉴 ─────────────────────────
def logo_html() -> str:
    """config/logo.png(.jpg/.svg)가 있으면 사이드바 맨 아래에 작게 표시 — 연세대학교 시그니처(공식 UI 파일)"""
    import base64
    import mimetypes
    for p in sorted((ROOT / "config").glob("logo.*")):
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"):
            mime = mimetypes.guess_type(p.name)[0] or "image/png"
            b64 = base64.b64encode(p.read_bytes()).decode()
            return f'<img src="data:{mime};base64,{b64}" alt="연세대학교"><div class="lg-cap">AI보건정보관리학과</div>'
    return ""


def brand_html() -> str:
    return (f'<div class="brand">{BRAND_MARK}<div><div class="wm">AI<b>-</b>KME</div><div class="tag">{esc(APP_FULL)}</div></div></div>'
            '<div class="brand-rule"></div>')



# ───────────────────────── 6. 문서관리 (v0.7) ─────────────────────────
def _dm_go(rel_path: str):
    st.session_state["dm_path"] = rel_path
    st.session_state["dm_q_reset"] = True          # 검색칸은 위젯이 만들어지기 전에만 비울 수 있어 다음 실행 때 비운다


def _dm_file_row(f: dict, show_folder: bool = False, key: str = ""):
    """문서함 파일 한 줄: 이름·종류 | 크기 | 날짜 | 내려받기 | 더보기(이름 바꾸기·옮기기·드라이브로 보내기·지우기)"""
    c1, c2, c3, c4, c5 = st.columns([3.6, 0.8, 1.2, 1.0, 0.9], vertical_alignment="center")
    where = f'<br><span class="card-meta">{esc(f["folder"])}</span>' if show_folder else ""
    idx = '<span class="card-meta"> · AI 검색</span>' if f["indexed"] else ""
    c1.markdown(f'<div class="mt-c"><b>{esc(f["name"])}</b> {badge(f["kind"], "gray")}{idx}{where}</div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="mt-c card-meta">{docs_mgmt.fmt_size(f["size"])}</div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="mt-c card-meta">{f["mtime"]:%Y-%m-%d %H:%M}</div>', unsafe_allow_html=True)
    try:
        c4.download_button("내려받기", f["path"].read_bytes(), f["name"], key=f"dm_dl_{key}", width="stretch")
    except OSError:
        c4.caption("읽기 실패")
    with c5.popover("더보기", width="stretch"):
        new = st.text_input("이름 바꾸기", value=f["name"], key=f"dm_rn_{key}")
        if st.button("바꾸기", key=f"dm_rn_btn_{key}") and new != f["name"]:
            ok, msg = docs_mgmt.rename(f["rel"], new)
            st.session_state["flash"] = (ok, msg); st.rerun()
        dest = st.selectbox("다른 폴더로 옮기기", docs_mgmt.all_folders(), key=f"dm_mv_{key}", format_func=lambda x: x or "(문서함 맨 위)")
        if st.button("옮기기", key=f"dm_mv_btn_{key}"):
            ok, msg = docs_mgmt.move(f["rel"], dest)
            st.session_state["flash"] = (ok, msg); st.rerun()
        if st.session_state.get("gd_connected"):
            if st.button("Google 드라이브로 보내기", key=f"dm_gd_{key}", help="드라이브 탭에서 열어 둔 폴더에 올립니다"):
                try:
                    r = gdrive.upload(st.session_state.get("gd_folder") or "root", f["name"], f["path"].read_bytes())
                    _gd_children.clear()
                    st.session_state["flash"] = (True, f"'{r['name']}' 을(를) Google 드라이브에 올렸습니다.")
                except Exception as ex:
                    st.session_state["flash"] = (False, f"드라이브에 올리지 못했습니다: {ex}")
                st.rerun()
        st.divider()
        if st.button("지우기", key=f"dm_del_{key}", type="primary"):
            ok, msg = docs_mgmt.delete(f["rel"])
            st.session_state["flash"] = (ok, msg); st.rerun()


def docs_local_tab():
    show_flash()
    st.session_state.setdefault("dm_path", "")
    if st.session_state.pop("dm_q_reset", False):
        st.session_state["dm_q"] = ""
    cur = st.session_state["dm_path"]
    if not docs_mgmt.resolve(cur).is_dir():
        cur = st.session_state["dm_path"] = ""
    n_f, n_d = docs_mgmt.count_all()
    h1, h2 = st.columns([2.6, 1.6], vertical_alignment="center")
    h1.markdown(f'<div class="card-title" style="font-size:1.35rem">사업 문서함 <span class="mt-cnt">파일 {n_f}개 · 폴더 {n_d}개</span></div>', unsafe_allow_html=True)
    q = h2.text_input("찾기", key="dm_q", placeholder="파일 이름으로 찾기", label_visibility="collapsed")

    nav, main = st.columns([1.05, 3.2], gap="medium")
    with nav:
        tops, _ = docs_mgmt.listing("")
        st.markdown('<div class="mt-h" style="text-align:left;padding-left:.7rem">폴더</div>', unsafe_allow_html=True)
        if st.button("문서함 전체", key="dm_nav_root", width="stretch", type="primary" if cur == "" and not q else "secondary"):
            _dm_go(""); st.rerun()
        for d in tops:
            on = cur == d["rel"] or cur.startswith(d["rel"] + "/")
            if st.button(f'{d["name"]}  ({d["count"]})', key=f'dm_nav_{d["rel"]}', width="stretch", type="primary" if on and not q else "secondary"):
                _dm_go(d["rel"]); st.rerun()
        with st.popover("새 폴더", width="stretch"):
            st.caption(f"'{cur.split('/')[-1] if cur else '문서함 맨 위'}' 안에 만듭니다.")
            nm = st.text_input("폴더 이름", key="dm_newdir", placeholder="예: 2026년 분기보고")
            if st.button("만들기", type="primary", key="dm_newdir_btn"):
                ok, msg = docs_mgmt.make_folder(cur, nm)
                st.session_state["flash"] = (ok, msg)
                if ok:
                    _dm_go((cur + "/" if cur else "") + docs_mgmt.safe_name(nm))
                st.rerun()
        open_folder_button(docs_mgmt.root(), key="dm_open")

    with main:
        if q.strip():
            hits = docs_mgmt.search(q)
            st.markdown(f'<div class="card-meta" style="margin-bottom:.4rem">"{esc(q)}" 검색 결과 {len(hits)}건</div>', unsafe_allow_html=True)
            with st.container(border=True):
                if not hits:
                    st.markdown('<div class="card-meta" style="padding:.6rem .3rem">찾는 파일이 없습니다.</div>', unsafe_allow_html=True)
                for i, f in enumerate(hits):
                    if i:
                        st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
                    _dm_file_row(f, show_folder=True, key=f"s{i}")
            return
        # 경로 표시줄 — 각 단계가 버튼
        parts = [p for p in cur.split("/") if p]
        crumbs = st.columns([1.1] + [1.4] * len(parts) + [2.2, 1.2], vertical_alignment="center") if parts else st.columns([1.1, 5.2, 1.2], vertical_alignment="center")
        if crumbs[0].button("문서함", key="dm_bc_root", width="stretch"):
            _dm_go(""); st.rerun()
        for i, p in enumerate(parts):
            if crumbs[i + 1].button(f"› {p}", key=f"dm_bc_{i}", width="stretch", disabled=i == len(parts) - 1):
                _dm_go("/".join(parts[:i + 1])); st.rerun()
        if cur:
            with crumbs[-1].popover("폴더 관리", width="stretch"):
                new = st.text_input("폴더 이름 바꾸기", value=parts[-1], key="dm_dir_rn")
                if st.button("바꾸기", key="dm_dir_rn_btn") and new != parts[-1]:
                    ok, msg = docs_mgmt.rename(cur, new)
                    st.session_state["flash"] = (ok, msg)
                    if ok:
                        _dm_go("/".join(parts[:-1] + [docs_mgmt.safe_name(new)]))
                    st.rerun()
                st.divider()
                if st.button("이 폴더 지우기", key="dm_dir_del", type="primary", help="안에 든 파일과 함께 pmc/_휴지통 으로 옮깁니다"):
                    ok, msg = docs_mgmt.delete(cur)
                    st.session_state["flash"] = (ok, msg)
                    if ok:
                        _dm_go("/".join(parts[:-1]))
                    st.rerun()
        folders, files = docs_mgmt.listing(cur)
        if folders:
            cols = st.columns(4)
            for i, d in enumerate(folders):
                if cols[i % 4].button(f'{d["name"]}  ({d["count"]})', key=f'dm_sub_{d["rel"]}', width="stretch"):
                    _dm_go(d["rel"]); st.rerun()
        with st.container(border=True):
            for c, h, w in zip(st.columns([3.6, 0.8, 1.2, 1.0, 0.9]), ["파일", "크기", "수정일", "", ""], [1] * 5):
                if h:
                    c.markdown(f'<div class="mt-h">{h}</div>', unsafe_allow_html=True)
            if not files:
                st.markdown('<div class="card-meta" style="padding:.8rem .3rem">이 폴더에 파일이 없습니다. 아래에 파일을 끌어다 놓거나 [파일 선택]으로 올리세요.</div>', unsafe_allow_html=True)
            for i, f in enumerate(files):
                st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
                _dm_file_row(f, key=f"f{i}")
        with st.form("dm_upload", clear_on_submit=True, border=True):
            ups = st.file_uploader(f"여기에 파일을 끌어다 놓으면 '{parts[-1] if parts else '문서함 맨 위'}' 폴더에 저장됩니다", accept_multiple_files=True, key="dm_up")
            if st.form_submit_button("이 폴더에 저장", type="primary") and ups:
                n, names = docs_mgmt.save_files(cur, [(u.name, u.getvalue()) for u in ups])
                st.session_state["flash"] = (True, f"{n}개 파일을 저장했습니다: {', '.join(names[:5])}{' …' if n > 5 else ''}")
                st.rerun()
        st.caption(f"저장 위치: {storage.rel(docs_mgmt.root())} — .hwpx .docx .pdf .md .txt 는 AI 사업비서가 검색할 수 있게 자동으로 색인됩니다. "
                   "회의록은 4. 사업관리, PDM 근거자료는 5. 성과관리에 그대로 둡니다.")


_gd_children = st.cache_data(ttl=120, show_spinner=False)(gdrive.children)
_gd_recent = st.cache_data(ttl=120, show_spinner=False)(gdrive.recent)
_gd_shared = st.cache_data(ttl=120, show_spinner=False)(gdrive.shared_with_me)
_gd_search = st.cache_data(ttl=120, show_spinner=False)(gdrive.search)
_gd_drives = st.cache_data(ttl=600, show_spinner=False)(gdrive.shared_drives)
_gd_crumb = st.cache_data(ttl=600, show_spinner=False)(gdrive.breadcrumb)


def _gd_clear():
    for f in (_gd_children, _gd_recent, _gd_shared, _gd_search, _gd_drives, _gd_crumb):
        f.clear()


def gdrive_setup_card(s: dict):
    """연결 전 안내 — 무엇이 준비됐고 무엇이 남았는지"""
    yes, no = badge("준비됨", "green"), badge("아직", "gray")
    with st.container(border=True):
        st.markdown('<div class="card-title">Google 드라이브와 아직 연결되지 않았습니다</div>'
                    '<div class="card-meta">연결하면 이 화면에서 드라이브 전체를 둘러보고, 사업 문서함과 파일을 바로 주고받을 수 있습니다. '
                    '두 방법 중 하나만 준비하면 됩니다.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown(f'<div class="card-title" style="font-size:1.05rem">방법 1 · 내 Google 계정으로 로그인 <span class="card-meta">(PC에서 쓸 때 권장)</span></div>'
                        f'<div class="mt-c">내 드라이브·공유 문서함 전체가 보입니다.<br>'
                        f'1) Google Cloud Console › API 및 서비스 › 사용자 인증 정보 › OAuth 클라이언트 ID(데스크톱 앱) 만들기 → JSON 내려받기<br>'
                        f'2) 그 파일을 <code>config/google_oauth_client.json</code> 으로 저장 {yes if s["oauth_client"] else no}<br>'
                        f'3) 아래 [Google 계정으로 연결] → 브라우저에서 로그인 {yes if s["token"] else no}</div>', unsafe_allow_html=True)
            if st.button("Google 계정으로 연결", type="primary", disabled=not (s["installed"] and s["oauth_client"]), key="gd_login",
                         help="브라우저가 열리고 로그인 창이 뜹니다. 'Google에서 확인하지 않은 앱' 경고가 나오면 '고급 › 이동'을 누르세요." if s["oauth_client"] else "config/google_oauth_client.json 이 먼저 필요합니다"):
                with st.spinner("브라우저에서 로그인해 주세요…"):
                    try:
                        svc, mode = gdrive.connect(interactive=True)
                        st.session_state["flash"] = (svc is not None, "연결했습니다." if svc else "로그인이 완료되지 않았습니다.")
                    except Exception as ex:
                        st.session_state["flash"] = (False, f"연결하지 못했습니다: {ex}")
                _gd_clear(); st.rerun()
        with c2:
            st.markdown(f'<div class="card-title" style="font-size:1.05rem">방법 2 · 서비스 계정 <span class="card-meta">(Streamlit Cloud 등 서버)</span></div>'
                        f'<div class="mt-c">서비스 계정에 공유한 폴더만 보입니다.<br>'
                        f'1) <code>.env</code> 에 <code>GOOGLE_SERVICE_ACCOUNT_JSON</code>(파일 경로 또는 JSON) {yes if s["service_account"] else no}<br>'
                        f'2) <code>GOOGLE_DRIVE_FOLDER_ID</code> = 사업 폴더 ID {yes if s["project_folder"] else no}<br>'
                        f'3) 드라이브에서 그 폴더를 서비스 계정 이메일에 공유</div>', unsafe_allow_html=True)
        if s["error"]:
            st.warning(s["error"])
        if st.button("연결 상태 다시 확인", key="gd_recheck"):
            _gd_clear(); st.rerun()


def _gd_item_row(f: dict, key: str, local_folder: str):
    c1, c2, c3, c4, c5 = st.columns([3.4, 0.8, 1.2, 1.0, 1.3], vertical_alignment="center")
    if f["is_folder"]:
        if c1.button(f'{f["name"]}', key=f"gd_open_{key}", width="stretch", help="폴더 열기"):
            st.session_state.update(gd_folder=f["id"], gd_view="folder", gd_q_reset=True); st.rerun()
        c2.markdown(f'<div class="mt-c card-meta">폴더</div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="mt-c card-meta">{esc(f["modified"])}</div>', unsafe_allow_html=True)
        if f["link"]:
            c4.link_button("웹에서 열기", f["link"], width="stretch")
        return
    c1.markdown(f'<div class="mt-c"><b>{esc(f["name"])}</b> {badge(f["kind"], "gray")}'
                + (f'<span class="card-meta"> · {esc(f["owner"])}</span>' if f["owner"] else "") + "</div>", unsafe_allow_html=True)
    c2.markdown(f'<div class="mt-c card-meta">{gdrive.fmt_size(f["size"]) if f["size"] else ""}</div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="mt-c card-meta">{esc(f["modified"])}</div>', unsafe_allow_html=True)
    if f["link"]:
        c4.link_button("웹에서 열기", f["link"], width="stretch")
    if c5.button("문서함으로 가져오기", key=f"gd_get_{key}", width="stretch", help=f"사업 문서함 '{local_folder or '맨 위'}' 폴더에 저장합니다"):
        try:
            name, data = gdrive.download(f)
            n, names = docs_mgmt.save_files(local_folder, [(name, data)])
            st.session_state["flash"] = (True, f"'{names[0]}' 을(를) 사업 문서함 '{local_folder or '맨 위'}' 에 저장했습니다.")
        except Exception as ex:
            st.session_state["flash"] = (False, f"가져오지 못했습니다: {ex}")
        st.rerun()


def docs_drive_tab():
    show_flash()
    s = gdrive.status()
    st.session_state["gd_connected"] = s["connected"]
    if not s["connected"]:
        gdrive_setup_card(s)
        return
    home = s["project_folder"] or ("root" if s["mode"] == "oauth" else "")
    st.session_state.setdefault("gd_folder", home)
    st.session_state.setdefault("gd_view", "folder")
    if st.session_state.pop("gd_q_reset", False):
        st.session_state["gd_q"] = ""
    h1, h2, h3 = st.columns([2.6, 1.6, 0.9], vertical_alignment="center")
    h1.markdown(f'<div class="card-title" style="font-size:1.35rem">Google 드라이브 <span class="mt-cnt">{esc(s["user"] or s["email"])}</span>'
                f'<span class="card-meta"> · {"내 계정 로그인" if s["mode"] == "oauth" else "서비스 계정"}</span></div>', unsafe_allow_html=True)
    q = h2.text_input("드라이브에서 찾기", key="gd_q", placeholder="드라이브 전체에서 파일 이름으로 찾기", label_visibility="collapsed")
    if h3.button("새로 고침", key="gd_refresh", width="stretch"):
        _gd_clear(); st.rerun()

    nav, main = st.columns([1.05, 3.2], gap="medium")
    with nav:
        st.markdown('<div class="mt-h" style="text-align:left;padding-left:.7rem">바로가기</div>', unsafe_allow_html=True)
        view, cur = st.session_state["gd_view"], st.session_state["gd_folder"]
        if s["project_folder"] and st.button("사업 폴더", key="gd_nav_proj", width="stretch", type="primary" if view == "folder" and cur == s["project_folder"] else "secondary"):
            st.session_state.update(gd_folder=s["project_folder"], gd_view="folder"); st.rerun()
        if s["mode"] == "oauth" and st.button("내 드라이브", key="gd_nav_root", width="stretch", type="primary" if view == "folder" and cur == "root" else "secondary"):
            st.session_state.update(gd_folder="root", gd_view="folder"); st.rerun()
        for d in _gd_drives():
            if st.button(d["name"], key=f'gd_nav_drv_{d["id"]}', width="stretch", type="primary" if view == "folder" and cur == d["id"] else "secondary", help="공유 드라이브"):
                st.session_state.update(gd_folder=d["id"], gd_view="folder"); st.rerun()
        if st.button("나와 공유됨", key="gd_nav_shared", width="stretch", type="primary" if view == "shared" else "secondary"):
            st.session_state["gd_view"] = "shared"; st.rerun()
        if st.button("최근 파일", key="gd_nav_recent", width="stretch", type="primary" if view == "recent" else "secondary"):
            st.session_state["gd_view"] = "recent"; st.rerun()
        st.markdown('<div class="mt-h" style="text-align:left;padding-left:.7rem;margin-top:.8rem">가져올 위치</div>', unsafe_allow_html=True)
        local_folder = st.selectbox("사업 문서함 폴더", docs_mgmt.all_folders(), key="gd_local_folder", format_func=lambda x: x or "(문서함 맨 위)", label_visibility="collapsed")
        if s["mode"] == "oauth" and st.button("연결 끊기", key="gd_logout", help="저장된 로그인 토큰을 지웁니다"):
            gdrive.disconnect(); _gd_clear(); st.session_state.pop("gd_folder", None); st.rerun()

    with main:
        try:
            if q.strip():
                items, title = _gd_search(q), f'"{q}" 검색 결과'
            elif st.session_state["gd_view"] == "recent":
                items, title = _gd_recent(40), "최근 파일"
            elif st.session_state["gd_view"] == "shared":
                items, title = _gd_shared(100), "나와 공유됨"
            else:
                cur = st.session_state["gd_folder"]
                crumbs = _gd_crumb(cur, frozenset({s["project_folder"]} if s["project_folder"] else set())) if cur else []
                items, title = (_gd_children(cur) if cur else []), ""
                if crumbs:
                    cols = st.columns([1.5] * len(crumbs) + [max(1, 7 - 1.5 * len(crumbs))], vertical_alignment="center")
                    for i, c in enumerate(crumbs):
                        if cols[i].button(("› " if i else "") + c["name"], key=f"gd_bc_{i}", width="stretch", disabled=i == len(crumbs) - 1):
                            st.session_state.update(gd_folder=c["id"], gd_view="folder"); st.rerun()
        except Exception as ex:
            st.error(f"드라이브를 읽지 못했습니다: {ex}")
            return
        if title:
            st.markdown(f'<div class="card-meta" style="margin:.2rem 0 .4rem 0">{esc(title)} {len(items)}건</div>', unsafe_allow_html=True)
        with st.container(border=True):
            for c, h in zip(st.columns([3.4, 0.8, 1.2, 1.0, 1.3]), ["이름", "크기", "수정일", "", ""]):
                if h:
                    c.markdown(f'<div class="mt-h">{h}</div>', unsafe_allow_html=True)
            if not items:
                st.markdown('<div class="card-meta" style="padding:.8rem .3rem">표시할 항목이 없습니다.</div>', unsafe_allow_html=True)
            for i, f in enumerate(items):
                st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
                _gd_item_row(f, key=f"{st.session_state['gd_view']}_{i}", local_folder=local_folder)
        if st.session_state["gd_view"] == "folder" and st.session_state["gd_folder"] and not q.strip():
            u1, u2 = st.columns([3, 1.2], gap="medium")
            with u1.form("gd_upload", clear_on_submit=True, border=True):
                ups = st.file_uploader("이 드라이브 폴더에 올리기", accept_multiple_files=True, key="gd_up")
                if st.form_submit_button("드라이브에 올리기", type="primary") and ups:
                    ok_n, errs = 0, []
                    for u in ups:
                        try:
                            gdrive.upload(st.session_state["gd_folder"], u.name, u.getvalue(), u.type or "application/octet-stream"); ok_n += 1
                        except Exception as ex:
                            errs.append(f"{u.name}: {ex}")
                    _gd_clear()
                    st.session_state["flash"] = (not errs, f"{ok_n}개 파일을 올렸습니다." + (" 실패: " + "; ".join(errs) if errs else ""))
                    st.rerun()
            with u2.popover("드라이브에 새 폴더", width="stretch"):
                nm = st.text_input("폴더 이름", key="gd_newdir")
                if st.button("만들기", type="primary", key="gd_newdir_btn") and nm.strip():
                    try:
                        gdrive.make_folder(st.session_state["gd_folder"], nm.strip()); _gd_clear()
                        st.session_state["flash"] = (True, f"'{nm.strip()}' 폴더를 만들었습니다.")
                    except Exception as ex:
                        st.session_state["flash"] = (False, f"폴더를 만들지 못했습니다: {ex}")
                    st.rerun()
        st.caption("사업 문서함의 파일을 드라이브로 보내려면 [사업 문서함] 탭 › 파일의 [더보기] › [Google 드라이브로 보내기] — 여기서 열어 둔 폴더에 올라갑니다.")


def docs_page():
    st.title("6. 문서관리")
    t1, t2 = st.tabs(["사업 문서함", "Google 드라이브"])
    with t1:
        docs_local_tab()
    with t2:
        docs_drive_tab()



# ───────────────────────── 3. 사업일정 › 일정 입력/수정 · 사업일정 달력 (v0.7) ─────────────────────────
MS_COLS = ["milestone_id", "title", "category", "project_year", "due_date", "owner", "status", "priority", "related_output", "note", "due_rule"]
MS_XLSX = {"milestone_id": "일정ID", "title": "일정명", "category": "구분", "project_year": "차년도", "due_date": "기한", "owner": "담당", "status": "상태",
           "priority": "중요도", "related_output": "관련 산출물", "note": "비고", "due_rule": "기한 규칙"}
MS_ALIAS = {"일정id": "milestone_id", "id": "milestone_id", "마일스톤id": "milestone_id", "일정명": "title", "일정": "title", "제목": "title", "구분": "category",
            "차년도": "project_year", "기한": "due_date", "날짜": "due_date", "일자": "due_date", "담당": "owner", "담당자": "owner", "상태": "status",
            "중요도": "priority", "관련산출물": "related_output", "비고": "note", "기한규칙": "due_rule"}


def priority_badge(p: str) -> str:
    p = str(p or "일반")
    return f'<span class="badge {"b-must" if p == "필수" else "b-core" if p == "핵심" else "b-gray"}">{esc(p)}</span>'


def milestones_xlsx() -> bytes:
    """엑셀 양식 — 현재 마일스톤이 들어 있어 엑셀에서 고쳐 다시 올리면 된다"""
    import io
    df = table(f"SELECT {','.join(MS_COLS)} FROM milestones ORDER BY due_date").rename(columns=MS_XLSX)
    guide = pd.DataFrame({"작성 안내": ["일정ID가 있는 행은 그 일정을 고치고, 비어 있으면 새 일정으로 추가됩니다.",
                                   "기한은 2026-12-01 처럼 적습니다. 일정명·기한은 꼭 적어 주세요.",
                                   "중요도는 필수 / 핵심 / 일반 중 하나, 상태는 예정 / 진행중 / 완료 / 지연 중 하나입니다.",
                                   "구분 예: 공정, 보고, 회의, 파견·출장.  차년도는 1~7.",
                                   "다 채우면 3. 사업일정 › 전체 일정표 › [입력/수정] › [엑셀 업로드]에 올리세요."]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="마일스톤", index=False)
        guide.to_excel(xw, sheet_name="작성 안내", index=False)
        ws = xw.sheets["마일스톤"]
        for col, w in zip("ABCDEFGHIJK", (10, 48, 10, 8, 12, 10, 8, 8, 14, 30, 24)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
    return buf.getvalue()


def milestones_from_xlsx(data: bytes) -> tuple[pd.DataFrame, str]:
    """올린 엑셀 → 마일스톤 열 이름으로 맞춘 표.  (표, 안내문)"""
    import io
    raw = pd.read_excel(io.BytesIO(data), sheet_name=0, dtype=str).fillna("")
    cols = {}
    for c in raw.columns:
        k = re.sub(r"[\s_()\-·.*]+", "", str(c)).lower()
        if k in MS_ALIAS:
            cols[c] = MS_ALIAS[k]
        elif k in MS_COLS:
            cols[c] = k
    df = raw.rename(columns=cols)
    if "title" not in df.columns or "due_date" not in df.columns:
        raise ValueError("'일정명'과 '기한' 열이 있어야 합니다. [엑셀 양식 다운로드]로 받은 양식을 쓰면 됩니다.")
    df = df[[c for c in MS_COLS if c in df.columns]].copy()
    for c in MS_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[MS_COLS]
    df = df[df["title"].astype(str).str.strip() != ""]
    df["due_date"] = df["due_date"].map(lambda v: storage._norm_date(str(v).strip()[:10]) if v else "")
    df["priority"] = df["priority"].map(lambda v: v if v in storage.PRIORITIES else "일반")
    df["status"] = df["status"].map(lambda v: v if v in ("예정", "진행중", "완료", "지연") else "예정")
    df["project_year"] = df["project_year"].map(lambda v: re.sub(r"[^\d]", "", str(v)))
    bad = df[~df["due_date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
    if len(bad):
        raise ValueError(f"기한을 읽지 못한 행이 {len(bad)}개 있습니다 (예: '{bad.iloc[0]['title']}'). 2026-12-01 형식으로 적어 주세요.")
    return df.reset_index(drop=True), f"{len(df)}건을 읽었습니다."


def milestones_editor():
    """[입력/수정] — 행 추가·삭제, 중요도(필수/핵심/일반), 엑셀 양식 다운로드·업로드, 저장"""
    ver = st.session_state.get("ms_ver", 0)
    if "ms_base" not in st.session_state:
        df = table(f"SELECT {','.join(MS_COLS)} FROM milestones ORDER BY due_date").astype(object).fillna("")
        df["project_year"] = df["project_year"].map(lambda v: "" if v in ("", None) else str(int(float(v))) if str(v).replace(".", "").isdigit() else str(v))
        df["priority"] = df["priority"].replace("", "일반")
        df.insert(0, "삭제", False)
        st.session_state["ms_base"] = df
    base = st.session_state["ms_base"]
    with st.container(border=True):
        st.markdown('<div class="card-title">일정 입력/수정</div><div class="card-meta">칸을 눌러 바로 고칩니다. 행을 지우려면 [삭제]에 표시한 뒤 [선택 행 삭제]. '
                    '엑셀로 한꺼번에 넣으려면 [엑셀 양식 다운로드] → 채우기 → [엑셀 업로드]. 마지막에 [저장하기]를 눌러야 저장됩니다.</div>', unsafe_allow_html=True)
        cfg = {"삭제": st.column_config.CheckboxColumn("삭제", width="small", default=False),
               "milestone_id": st.column_config.TextColumn("일정ID", width="small", help="비워 두면 저장할 때 자동으로 번호가 붙습니다"),
               "title": st.column_config.TextColumn("일정명", width="large", required=True),
               "category": st.column_config.TextColumn("구분", width="small", help="공정 / 보고 / 회의 / 파견·출장"),
               "project_year": st.column_config.TextColumn("차년도", width="small"),
               "due_date": st.column_config.TextColumn("기한", width="medium", help="YYYY-MM-DD", required=True),
               "owner": st.column_config.TextColumn("담당", width="small"),
               "status": st.column_config.SelectboxColumn("상태", options=["예정", "진행중", "완료", "지연"], width="small", required=True),
               "priority": st.column_config.SelectboxColumn("중요도", options=storage.PRIORITIES, width="small", required=True, help="필수 > 핵심 > 일반"),
               "related_output": st.column_config.TextColumn("관련 산출물", width="small"),
               "note": st.column_config.TextColumn("비고", width="medium"),
               "due_rule": st.column_config.TextColumn("기한 규칙", width="medium", help="'계약 체결 후 1개월 이내' 같은 규칙이 있으면 [기한 다시 계산]에 쓰입니다")}
        edited = st.data_editor(base, num_rows="fixed", column_config=cfg, hide_index=True, width="stretch", row_height=40,
                                height=min(40 * (len(base) + 1) + 8, 640), key=f"ms_ed_{ver}")
        b1, b2, b3, b4, _, b5, b6 = st.columns([1, 1.25, 1.5, 1.2, 0.6, 1.1, 0.8], vertical_alignment="center")
        if b1.button("행 추가", key="ms_add_row", width="stretch"):
            new = {c: "" for c in edited.columns}
            new.update({"삭제": False, "milestone_id": storage.next_milestone_id([str(x) for x in edited["milestone_id"]]), "status": "예정", "priority": "일반",
                        "due_date": date.today().isoformat(), "project_year": str(max(1, min(7, date.today().year - 2025)))})
            st.session_state["ms_base"] = pd.concat([edited, pd.DataFrame([new])], ignore_index=True)
            st.session_state["ms_ver"] = ver + 1
            st.rerun()
        if b2.button("선택 행 삭제", key="ms_del_rows", width="stretch"):
            sel = edited["삭제"].fillna(False).astype(bool)
            if not sel.any():
                st.warning("지울 행의 [삭제] 칸에 먼저 표시해 주세요.")
            else:
                st.session_state["ms_base"] = edited[~sel].reset_index(drop=True)
                st.session_state["ms_ver"] = ver + 1
                st.rerun()
        try:
            b3.download_button("엑셀 양식 다운로드", milestones_xlsx(), f"마일스톤_{date.today():%Y%m%d}.xlsx", stakeholders.XLSX_MIME, key="ms_xlsx_dl", width="stretch",
                               help="지금 일정이 들어 있는 엑셀입니다. 고치거나 줄을 더해 [엑셀 업로드]에 올리세요.")
        except Exception as ex:
            b3.caption(f"엑셀 생성 실패: {ex}")
        with b4.popover("엑셀 업로드", width="stretch"):
            up = st.file_uploader("마일스톤 엑셀 (.xlsx)", type=["xlsx", "xls", "csv"], key="ms_up")
            how = st.radio("반영 방법", ["편집표에 더하기 (같은 일정ID는 덮어쓰기)", "편집표를 엑셀 내용으로 바꾸기"], key="ms_up_how")
            if up is not None:
                try:
                    if up.name.lower().endswith(".csv"):
                        raw = pd.read_csv(io.BytesIO(up.getvalue()), dtype=str, keep_default_na=False, encoding="utf-8-sig")
                        tmp = io.BytesIO(); raw.to_excel(tmp, index=False); new_df, msg = milestones_from_xlsx(tmp.getvalue())
                    else:
                        new_df, msg = milestones_from_xlsx(up.getvalue())
                    have = set(edited["milestone_id"].astype(str))
                    n_upd = sum(1 for i in new_df["milestone_id"] if str(i).strip() and str(i) in have)
                    st.caption(f"{msg} 기존 일정 {n_upd}건 갱신, 새 일정 {len(new_df) - n_upd}건 추가")
                    st.dataframe(new_df.rename(columns=MS_XLSX).head(8), hide_index=True, height=240)
                    if st.button("편집표에 반영", type="primary", key="ms_up_apply"):
                        cur = edited.drop(columns=["삭제"])
                        ids = [str(x) for x in cur["milestone_id"]]
                        new_df = new_df.copy()
                        for i in new_df.index:
                            if not str(new_df.at[i, "milestone_id"]).strip():
                                nid = storage.next_milestone_id(ids); new_df.at[i, "milestone_id"] = nid; ids.append(nid)
                        if how.startswith("편집표를"):
                            merged = new_df
                        else:
                            keep = cur[~cur["milestone_id"].astype(str).isin(set(new_df["milestone_id"].astype(str)))]
                            merged = pd.concat([keep, new_df], ignore_index=True)
                        merged = merged.sort_values("due_date").reset_index(drop=True)
                        merged.insert(0, "삭제", False)
                        st.session_state["ms_base"] = merged
                        st.session_state["ms_ver"] = ver + 1
                        st.session_state["flash"] = (True, f"엑셀 {len(new_df)}건을 편집표에 반영했습니다. 확인 후 [저장하기]를 누르세요.")
                        st.rerun()
                except Exception as ex:
                    st.error(f"엑셀을 읽지 못했습니다: {ex}")
        if b5.button("저장하기", type="primary", key="ms_save", width="stretch"):
            df = edited.drop(columns=["삭제"]).copy()
            ids = [str(x) for x in df["milestone_id"] if str(x).strip()]
            for i in df.index:
                if not str(df.at[i, "milestone_id"] or "").strip():
                    nid = storage.next_milestone_id(ids); df.at[i, "milestone_id"] = nid; ids.append(nid)
            df["priority"] = df["priority"].fillna("").replace("", "일반")
            ok, msg = storage.save_table("milestones", df)
            if ok:
                st.session_state["flash"] = (True, msg)
                st.session_state["ms_edit"] = False
                st.session_state.pop("ms_base", None)
                st.session_state["ms_ver"] = ver + 1
                st.rerun()
            st.error(msg)
        if b6.button("닫기", key="ms_close", width="stretch"):
            st.session_state["ms_edit"] = False
            st.session_state.pop("ms_base", None)
            st.rerun()


def calendar_tab():
    """사업일정 — 월 달력 (1일~말일) + 일정 추가/삭제 (일정·일시·장소·참석자)"""
    import calendar as _cal
    show_flash()
    today = date.today()
    st.session_state.setdefault("cal_ym", (today.year, today.month))
    y, m = st.session_state["cal_ym"]
    n1, n2, n3, n4, _, n5, n6 = st.columns([0.75, 0.75, 0.75, 2.0, 0.9, 1.45, 1.1], vertical_alignment="center")
    if n1.button("이전 달", key="cal_prev", width="stretch"):
        st.session_state["cal_ym"] = (y - 1, 12) if m == 1 else (y, m - 1); st.rerun()
    if n2.button("오늘", key="cal_today", width="stretch"):
        st.session_state["cal_ym"] = (today.year, today.month); st.rerun()
    if n3.button("다음 달", key="cal_next", width="stretch"):
        st.session_state["cal_ym"] = (y + 1, 1) if m == 12 else (y, m + 1); st.rerun()
    n4.markdown(f'<div class="cal-title">{y}년 {m}월</div>', unsafe_allow_html=True)
    show_ms = n5.toggle("마일스톤 표시", value=True, key="cal_show_ms", help="마일스톤 기한을 달력에 함께 보여 줍니다")
    with n6.popover("일정 추가", width="stretch"):
        with st.form("cal_add", clear_on_submit=True, border=False):
            title = st.text_input("일정 *", placeholder="예: DOH KMITS 협의")
            c1, c2 = st.columns([1.3, 1])
            d = c1.date_input("일시 — 날짜 *", value=date(y, m, min(today.day, _cal.monthrange(y, m)[1])) if (y, m) != (today.year, today.month) else today, format="YYYY-MM-DD")
            tm = c2.text_input("시각", placeholder="14:00 (종일이면 비움)")
            c3, c4 = st.columns([1.3, 1])
            d2 = c3.date_input("마지막 날 (여러 날 일정일 때)", value=None, format="YYYY-MM-DD")
            tm2 = c4.text_input("끝나는 시각", placeholder="16:00")
            loc = st.text_input("장소")
            parts = st.text_input("참석자", placeholder="PM, PL, KMITS 담당")
            note = st.text_input("메모 (선택)")
            if st.form_submit_button("추가", type="primary"):
                ok, msg = storage.add_event({"title": title, "start_date": d.isoformat() if d else "", "start_time": tm, "end_date": d2.isoformat() if d2 else "",
                                             "end_time": tm2, "location": loc, "participants": parts, "note": note})
                st.session_state["flash"] = (ok, msg)
                if ok and d:
                    st.session_state["cal_ym"] = (d.year, d.month)
                st.rerun()

    last = _cal.monthrange(y, m)[1]
    d0, d1 = f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}"
    evs = storage.events_between(d0, d1)
    by_day: dict[int, list] = {k: [] for k in range(1, last + 1)}
    for e in evs:
        s = max(date.fromisoformat(e["start_date"]), date(y, m, 1))
        en = date.fromisoformat(e["end_date"]) if e["end_date"] else date.fromisoformat(e["start_date"])
        en = min(en, date(y, m, last))
        cur = s
        while cur <= en:
            tm = e["start_time"] if cur == date.fromisoformat(e["start_date"]) else ""
            by_day[cur.day].append(("ev", tm, e["title"], e))
            cur += timedelta(days=1)
    ms_rows = []
    if show_ms:
        ms_rows = table("SELECT milestone_id, title, due_date, status, priority FROM milestones WHERE due_date BETWEEN ? AND ? ORDER BY due_date", (d0, d1)).to_dict("records")
        for r in ms_rows:
            by_day[int(r["due_date"][8:10])].append(("ms", "", r["title"], r))
    first_wd = (date(y, m, 1).weekday() + 1) % 7            # 일요일 시작
    h = ['<div class="cal">'] + [f'<div class="wd {"sun" if i == 0 else "sat" if i == 6 else ""}">{w}</div>' for i, w in enumerate("일월화수목금토")]
    h += ['<div class="d off"></div>'] * first_wd
    for day in range(1, last + 1):
        dt = date(y, m, day)
        wd = (dt.weekday() + 1) % 7
        cls = "d" + (" today" if dt == today else "")
        items = by_day[day]
        chips = []
        for kind, tm, title, rec in items[:4]:
            if kind == "ev":
                chips.append(f'<span class="ev" title="{esc(title)}{(" · " + esc(rec["location"])) if rec.get("location") else ""}">'
                             f'{f"<span class=tm>{esc(tm)}</span>" if tm else ""}{esc(title)}</span>')
            else:
                pc = "must" if rec.get("priority") == "필수" else "core" if rec.get("priority") == "핵심" else ""
                chips.append(f'<span class="ev ms {pc}" title="마일스톤 기한 · {esc(rec.get("priority") or "일반")} · {esc(rec.get("status") or "")}">기한 · {esc(title)}</span>')
        if len(items) > 4:
            chips.append(f'<div class="more">+{len(items) - 4}건 더</div>')
        h.append(f'<div class="{cls}"><span class="n {"sun" if wd == 0 else "sat" if wd == 6 else ""}">{day}</span>{"".join(chips)}</div>')
    tail = (7 - (first_wd + last) % 7) % 7
    h += ['<div class="d off"></div>'] * tail + ["</div>"]
    st.markdown("".join(h), unsafe_allow_html=True)
    st.markdown('<div class="legend card-meta" style="margin-top:.4rem"><span style="background:#E8EEF8;border-left:3px solid #1F4E9C"></span>사업일정'
                '<span style="background:#EEF2F9;border-left:3px solid #8A97A8"></span>마일스톤 기한<span style="background:#FBEAE8;border-left:3px solid #B3261E"></span>필수'
                '<span style="background:#FFF3DC;border-left:3px solid #9A5B00"></span>핵심</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="card-title" style="margin-top:1rem">{m}월 일정 <span class="mt-cnt">{len(evs)}건</span></div>', unsafe_allow_html=True)
    with st.container(border=True):
        for c, hd in zip(st.columns([1.3, 2.6, 1.6, 2.0, 0.8]), ["일시", "일정", "장소", "참석자", ""]):
            if hd:
                c.markdown(f'<div class="mt-h">{hd}</div>', unsafe_allow_html=True)
        if not evs:
            st.markdown('<div class="card-meta" style="padding:.8rem .3rem">이달에 등록된 일정이 없습니다. 오른쪽 위 [일정 추가]로 등록하세요.</div>', unsafe_allow_html=True)
        for e in evs:
            st.markdown('<hr class="mt-hr">', unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns([1.3, 2.6, 1.6, 2.0, 0.8], vertical_alignment="center")
            when = e["start_date"][5:].replace("-", "/") + (f" {e['start_time']}" if e["start_time"] else "")
            if e["end_date"] and e["end_date"] != e["start_date"]:
                when += f" ~ {e['end_date'][5:].replace('-', '/')}"
            if e["end_time"]:
                when += f" ~{e['end_time']}" if not (e["end_date"] and e["end_date"] != e["start_date"]) else f" {e['end_time']}"
            c1.markdown(f'<div class="mt-c"><b class="nowrap">{esc(when)}</b></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="mt-c"><b>{esc(e["title"])}</b>' + (f'<br><span class="card-meta">{esc(e["note"])}</span>' if e["note"] else "") + "</div>", unsafe_allow_html=True)
            c3.markdown(f'<div class="mt-c">{esc(e["location"] or "")}</div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="mt-c">{esc(e["participants"] or "")}</div>', unsafe_allow_html=True)
            if c5.button("삭제", key=f"cal_del_{e['id']}", width="stretch"):
                ok, msg = storage.delete_event(int(e["id"]))
                st.session_state["flash"] = (ok, msg); st.rerun()
    st.caption(f"일정은 {storage.rel(storage.csv_path('events'))} 에 저장됩니다. 마일스톤 기한은 [전체 일정표 › 입력/수정]에서 고칩니다.")


st.session_state.setdefault("page", MENUS[0])
with st.sidebar:
    st.markdown(brand_html(), unsafe_allow_html=True)
    for m in MENUS:
        if st.button(m, key=f"nav_{m}", width="stretch", type="primary" if st.session_state.page == m else "secondary"):
            st.session_state.page = m
            st.rerun()
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    st.divider()
    if st.button(REPORT, key="nav_report", width="stretch",
                 type="primary" if st.session_state.page == REPORT else "secondary"):
        st.session_state.page = REPORT
        st.rerun()
    st.caption("사용 중 문제가 생기면 메모를 남겨 주세요.")
    if is_admin() and st.button(ACCOUNTS, key="nav_accounts", width="stretch", type="primary" if st.session_state.page == ACCOUNTS else "secondary"):
        st.session_state.page = ACCOUNTS
        st.rerun()
    _u = current_user()
    with st.popover(f"{_u.get('login_id', '')} · {_u.get('role', '')}", width="stretch"):
        st.markdown(f'<div class="mt-c"><b>{esc(_u.get("name") or _u.get("login_id"))}</b><br><span class="card-meta">{esc(_u.get("role"))} 권한'
                    f'{" — 열람만 가능" if view_only() else " — 수정·추가 가능"}</span></div>', unsafe_allow_html=True)
        with st.form("my_pw", clear_on_submit=True, border=False):
            op = st.text_input("현재 비밀번호", type="password")
            np_ = st.text_input("새 비밀번호", type="password")
            if st.form_submit_button("비밀번호 변경"):
                ok, msg = auth.set_password(_u["login_id"], np_, old_pw=op)
                (st.success if ok else st.error)(msg)
        if st.button("로그아웃", key="logout", width="stretch"):
            for k in ("auth", "page"):
                st.session_state.pop(k, None)
            st.rerun()
    with st.container(key="sb_logo"):
        st.markdown(logo_html(), unsafe_allow_html=True)
page = st.session_state.page
if page == ACCOUNTS and not is_admin():
    page = st.session_state.page = MENUS[0]


# ───────────────────────── 1. 대쉬보드 ─────────────────────────
def dash_date_line(today: date) -> str:
    """오늘 날짜와 사업 차년도 한 줄"""
    wd = "월화수목금토일"[today.weekday()]
    yr = today.year - 2025
    yr_txt = f"사업 {yr}차년도" if 1 <= yr <= 7 else "사업기간 2026-2032"
    return f"{today.year}년 {today.month}월 {today.day}일 {wd}요일, {yr_txt}"


def dash_stats(overdue: int, week: int, month: int, anomalies: int, actions: int, tbd: int) -> str:
    """요약 띠: 첫 칸(기한 경과)이 가장 크고, 0이면 회색으로 가라앉는다"""
    def cell(n, label, cls=""):
        state = "zero" if n == 0 else cls
        return f'<div class="{state}"><div class="n">{n}<small>건</small></div><div class="l">{esc(label)}</div></div>'
    return ('<div class="stats">' + cell(overdue, "기한이 지난 항목", "hot") + cell(week, "7일 안에 마감", "warm")
            + cell(month, "30일 안에 마감") + cell(actions + anomalies, "확인이 필요한 것") + cell(tbd, "미확정 지표") + "</div>")


def dash_todo(rows: list, today: date) -> None:
    """기한 목록: 지난 것 → 7일 → 30일 순. 한 줄 = 남은 일수 / 항목 / 구분"""
    groups = [("기한이 지났습니다", [r for r in rows if r["D-day"] < 0], "danger"),
              ("이번 주 (7일 안)", [r for r in rows if 0 <= r["D-day"] <= 7], "warn"),
              ("이번 달 (30일 안)", [r for r in rows if 7 < r["D-day"] <= 30], "")]
    if not rows:
        st.markdown('<div class="empty-ok">30일 안에 마감되는 항목이 없습니다.</div>', unsafe_allow_html=True)
        return
    html_ = []
    for title, items, cls in groups:
        if not items:
            continue
        html_.append(f'<div class="todo-h {cls}">{esc(title)}<span class="cnt">{len(items)}건</span></div>')
        for r in items:
            d = r["D-day"]
            dtxt = f"{-d}일 지남" if d < 0 else ("오늘" if d == 0 else f"D-{d}")
            dcls = "danger" if d < 0 else "warn" if d <= 7 else "plain"
            meta = f"{esc(r['기한'])} 까지, 담당 {esc(r['담당'] or '미지정')}, {esc(r['상태'])}"
            pri = r.get("중요도") or ""
            ptag = f' <span class="badge {"b-must" if pri == "필수" else "b-core"}">{esc(pri)}</span>' if pri in ("필수", "핵심") else ""
            html_.append(f'<div class="todo"><div class="d {dcls}">{esc(dtxt)}</div>'
                         f'<div><div class="t">{esc(r["항목"])}{ptag}</div><div class="m">{meta}</div></div>'
                         f'<div class="k">{esc(r["구분"])}</div></div>')
    st.markdown("".join(html_), unsafe_allow_html=True)


def dash_side(a: dict) -> None:
    """오른쪽 패널: 확인이 필요한 것 (후속조치, 센터 실적, 지표)"""
    h = ['<div class="side">']
    h.append("<h4>미이행 후속조치</h4>")
    acts = a["후속조치"]
    if not acts:
        h.append('<div class="empty">미이행 후속조치가 없습니다.</div>')
    for r in acts[:6]:
        due = f'<span class="neg">{esc(r["due_date"])} 기한 지남</span>' if r["overdue"] else f'{esc(r["due_date"] or "기한 미정")} 까지'
        h.append(f'<div class="row"><b>{esc(r["description"])}</b><div class="m">{esc(r["meeting"] or "")} / 담당 {esc(r["owner"] or "미지정")} / {due}</div></div>')
    if len(acts) > 6:
        h.append(f'<div class="empty">외 {len(acts) - 6}건은 [4. 사업관리]에서 보세요.</div>')

    h.append('<div class="gap"></div><h4>센터 실적 이상치</h4>')
    if not a["이상치"]:
        h.append('<div class="empty">전월 대비 급감한 센터가 없습니다.</div>')
    for r in a["이상치"]:
        h.append(f'<div class="row"><b>{esc(r["name"])}</b> <span class="neg">{r["change_pct"]}%</span>'
                 f'<div class="m">{esc(r["month"])} {esc(r["metric"])} {r["prev"]:,.0f} → {r["value"]:,.0f}</div></div>')

    h.append('<div class="gap"></div><h4>기초선·목표치 미확정 지표</h4>')
    tbd = a["기초선누락"]
    if not tbd:
        h.append('<div class="empty">모든 지표의 기초선과 목표치가 정해졌습니다.</div>')
    for r in tbd[:4]:
        h.append(f'<div class="row"><b>{esc(r["indicator_id"])}</b> {esc(r["name"])}<div class="m">{esc(r["missing"])} 미확정</div></div>')
    if len(tbd) > 4:
        h.append(f'<div class="empty">외 {len(tbd) - 4}개 지표는 [5. 성과관리 › 성과점검표]에서 보세요.</div>')
    h.append("</div>")
    st.markdown("".join(h), unsafe_allow_html=True)


if page == MENUS[0]:
    today = date.today()
    a = rules.all_alerts()
    snap = storage.folder("1_대쉬보드") / f"점검결과_{today.isoformat()}.csv"
    if not snap.exists():                  # 하루 한 번 자동 저장 → 7년간 점검 이력이 쌓인다
        storage.save_alert_snapshot(a)

    st.title("대쉬보드")
    st.markdown(f'<div class="dash-sub">{esc(dash_date_line(today))}</div>', unsafe_allow_html=True)

    due = a["기한"]
    n_over = sum(1 for r in due if r["D-day"] < 0)
    n_week = sum(1 for r in due if 0 <= r["D-day"] <= 7)
    n_month = sum(1 for r in due if 7 < r["D-day"] <= 30)
    st.markdown(dash_stats(n_over, n_week, n_month, len(a["이상치"]), len(a["후속조치"]), len(a["기초선누락"])),
                unsafe_allow_html=True)

    main, side = st.columns([1.55, 1], gap="large")
    with main:
        st.header("챙길 일")
        dash_todo(due, today)
        if st.button("전체 일정 보기", key="dash_go_schedule"):
            st.session_state.page = MENUS[2]
            st.rerun()
    with side:
        st.header("확인이 필요한 것")
        dash_side(a)

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    u1, u2, u3 = st.columns([1.1, 1, 3.4])
    if u1.button("점검결과 저장", key="dash_save", width="stretch"):
        sp = storage.save_alert_snapshot(a)
        st.success(f"저장했습니다: {storage.rel(sp)}") if sp else st.error("파일이 엑셀에서 열려 있습니다. 닫고 다시 눌러 주세요.")
    with u2:
        open_folder_button(storage.folder("1_대쉬보드"), key="open_dash")
    u3.markdown('<div class="util" style="padding-top:.6rem">점검결과는 매일 처음 열 때 pmc/1_대쉬보드 폴더에 날짜별로 자동 저장됩니다.</div>', unsafe_allow_html=True)

# ───────────────────────── 2. 사업개요 ─────────────────────────
elif page == MENUS[1]:
    st.title("2. 사업개요")
    view_tab, ed_tab = st.tabs(["개요 보기", "데이터 편집·저장"])
    ov = yaml.safe_load(storage.overview_path().read_text(encoding="utf-8")) or {}

    with view_tab:
        with st.container(border=True):
            st.markdown('<div class="kv">' + "".join(f"<b>{esc(k)}</b><span>{esc(v)}</span>" for k, v in ov.items()) + "</div>",
                        unsafe_allow_html=True)

        st.header("6개 사업산출물")
        outs = table("SELECT o.*, (SELECT COUNT(*) FROM sub_outputs s WHERE s.output_id=o.output_id) AS n_sub FROM outputs o").to_dict("records")

        def _out(o):
            with st.container(border=True):
                st.markdown(f'{badge("산출물 " + str(o["output_id"]))}{badge("PMC 직접수행" if str(o.get("implementer") or "").startswith("PMC") else "현지기관 수행", "org" if str(o.get("implementer") or "").startswith("PMC") else "gray")}'
                            f'<div class="card-title">{esc(o["name"])}</div>'
                            f'<div class="card-meta">{esc(o.get("outcome") or "")}<br>{esc(o["description"] or "")}<br>'
                            f'수행: {esc(o.get("implementer") or "")}<br>산출물 형태: {esc(o.get("deliverable") or "")}<br>'
                            f'보조산출물 {o["n_sub"]}종 · 책임 {esc(o["lead_expert"] or "미지정")}</div>', unsafe_allow_html=True)
                pct = float(o["progress_pct"] or 0)
                st.progress(min(max(pct, 0) / 100, 1.0), text=f"진척률 {pct:.0f}%")
        grid(outs, _out, cols=2)

        st.header("대상 센터")
        ct = table("SELECT support_type, COUNT(*) n FROM centers GROUP BY 1 ORDER BY 2 DESC")
        for col, r in zip(st.columns(max(len(ct), 1)), ct.to_dict("records")):
            with col, st.container(border=True):
                st.metric(r["support_type"] or "미분류", f"{r['n']}개소")

        st.header("전문가 투입계획 (M/D)")
        ex = table("SELECT role AS 분야, category AS 구분, grade AS 등급, person_name AS 성명, md_domestic AS 국내, md_overseas AS 국외, md_total AS 계, duties AS 주요업무 FROM experts")
        show_df(ex)

        st.header("주요 이해관계자")
        sh = table("SELECT category, GROUP_CONCAT(org || CASE WHEN dept<>'' THEN ' ' || dept ELSE '' END, ' · ') AS orgs "
                   "FROM stakeholders GROUP BY category").to_dict("records")
        grid(sh, lambda r: card(r["category"], esc(r["orgs"])), cols=3)

    with ed_tab:
        show_flash()
        st.subheader("사업 기본정보")
        ov_df = st.data_editor(pd.DataFrame({"항목": list(ov.keys()), "내용": [str(v) for v in ov.values()]}), num_rows="dynamic",
                               hide_index=True, width="stretch", row_height=44, key="ed_overview")
        if st.button("기본정보 저장", type="primary"):
            new = {str(r["항목"]).strip(): str(r["내용"] or "").strip() for r in ov_df.to_dict("records")
                   if str(r["항목"] or "").strip() not in ("", "None")}
            storage.overview_path().write_text(yaml.safe_dump(new, allow_unicode=True, sort_keys=False), encoding="utf-8")
            st.session_state["flash"] = (True, f"저장했습니다 → {storage.rel(storage.overview_path())}")
            st.rerun()
        st.caption(f"저장 위치: {storage.rel(storage.overview_path())}")
        st.subheader("산출물 · 센터")
        edit_tab("2_사업개요")

# ───────────────────────── 3. 사업일정 ─────────────────────────
elif page == MENUS[2]:
    wide_page()
    st.title("3. 사업일정")
    t0, tc, t1, t2, t3 = st.tabs(["전체 일정표 (2026~2032)", "사업일정", "마일스톤", "제출 일정 (산출물·관리문서)", "데이터 편집·저장"])
    ms = table("SELECT * FROM milestones ORDER BY due_date")
    if "priority" in ms.columns:
        ms["priority"] = ms["priority"].fillna("").replace("", "일반")
    today = date.today()
    with t0:
        show_flash()
        g1, g2 = st.columns([4.6, 1.2], vertical_alignment="center")
        g1.markdown(f'<div class="card-title" style="font-size:1.35rem">전체 일정표 <span class="mt-cnt">마일스톤 {len(ms)}건</span></div>', unsafe_allow_html=True)
        if g2.button("닫기" if st.session_state.get("ms_edit") else "입력/수정", type="secondary" if st.session_state.get("ms_edit") else "primary", width="stretch", key="ms_edit_btn",
                     help="마일스톤(일정)을 추가·삭제·수정하고 엑셀로 올립니다"):
            st.session_state["ms_edit"] = not st.session_state.get("ms_edit", False)
            st.session_state.pop("ms_base", None)
            st.rerun()
        if st.session_state.get("ms_edit"):
            milestones_editor()
        acts = table("SELECT a.*, o.name AS out_name FROM activities a LEFT JOIN outputs o USING(output_id) ORDER BY a.output_id='PM', a.activity_id").to_dict("records")
        years = list(range(2026, 2033))
        nowq = (today.year, (today.month - 1) // 3 + 1)
        h = ['<div class="scroll-x"><table class="gantt"><tr><th rowspan="2">구분 (활동내역)</th>'] + [f'<th colspan="4">{y}</th>' for y in years] + ["</tr><tr>"]
        h += [f'<th class="{"now" if (y, k) == nowq else ""}">{k}</th>' for y in years for k in range(1, 5)] + ["</tr>"]
        last = None
        for a in acts:
            if a["output_id"] != last:
                last = a["output_id"]
                title = "사업관리" if last == "PM" else f'사업산출물 {last}. {a["out_name"] or ""}'
                h.append(f'<tr><td class="grp" colspan="29">{esc(title)}</td></tr>')
            sq, eq, fq = schedule.parse_q(a["start_q"]), schedule.parse_q(a["end_q"]), schedule.parse_q(a["focus_end_q"])
            h.append(f'<tr><td class="lab"><b>{esc(a["activity_id"])}</b> {esc(a["name"])}</td>')
            for y in years:
                for k in range(1, 5):
                    on = sq and eq and sq <= (y, k) <= eq
                    cls = "" if not on else "pm" if last == "PM" else "focus" if (not fq or (y, k) <= fq) else "on"
                    h.append(f'<td class="q {cls} {"now" if (y, k) == nowq else ""}"></td>')
            h.append("</tr>")
        h.append("</table></div>")
        st.markdown("".join(h), unsafe_allow_html=True)
        st.markdown('<div class="legend card-meta"><span style="background:#1F4E9C"></span>집중 추진<span style="background:#9DB7E3"></span>후속 지원·모니터링'
                    '<span style="background:#8A97A8"></span>사업관리<span style="box-shadow: inset 0 0 0 2px #E07B00"></span>현재 분기</div>', unsafe_allow_html=True)
        st.caption("RFP '라. 추진일정' 표를 그대로 옮긴 것입니다(분기 단위). 고치려면 [데이터 편집·저장]에서 '활동별 일정'의 시작·종료 분기(예: 2027Q1)를 바꾸세요.")
        with st.expander("활동별 수행기관과 PMC 역할"):
            show_df(pd.DataFrame(acts)[["activity_id", "name", "implementer", "pmc_role", "note"]].rename(
                columns={"activity_id": "활동", "name": "활동명", "implementer": "수행기관", "pmc_role": "PMC 역할", "note": "비고"}))

        with st.container(border=True):
            st.markdown('<div class="card-title">계약체결일 기준 기한 다시 계산</div><div class="card-meta">보조산출물·관리문서·마일스톤 가운데 '
                        "'계약 체결 후 ○주/개월', '○차년도 ○분기', '매년 ○월 ○일' 규칙이 있는 미완료 항목의 기한을 다시 계산합니다. 직접 고친 기한도 규칙 값으로 바뀝니다.</div>", unsafe_allow_html=True)
            ov = yaml.safe_load(storage.overview_path().read_text(encoding="utf-8")) or {}
            try:
                cur = date.fromisoformat(str(ov.get("계약체결일", "")))
            except ValueError:
                cur = date(2026, 11, 1)
            c1, c2 = st.columns([1, 2])
            cd = c1.date_input("계약체결일", value=cur, format="YYYY-MM-DD")
            if c1.button("기한 다시 계산", type="primary", width="stretch"):
                ov["계약체결일"] = cd.isoformat()
                storage.overview_path().write_text(yaml.safe_dump(ov, allow_unicode=True, sort_keys=False), encoding="utf-8")
                ch = schedule.recalc(cd)
                st.success(f"계약체결일 {cd} 기준으로 다시 계산했습니다 — 보조산출물 {ch['sub_outputs']}건, 관리문서 {ch['management_docs']}건, 마일스톤 {ch['milestones']}건 변경")
    with tc:
        calendar_tab()
    with t1:
        c1, c2, c3, c4 = st.columns([1.6, 1.6, 1.4, 1])
        ys = sorted({d[:4] for d in ms["due_date"]})
        sel_y = c1.multiselect("연도", ys, default=[y for y in ys if y in (str(today.year), str(today.year + 1))], placeholder="전체")
        cats = c2.multiselect("구분", sorted(ms["category"].dropna().unique()), placeholder="전체")
        pri = c3.multiselect("중요도", storage.PRIORITIES, placeholder="전체")
        hide_done = c4.toggle("완료 숨기기", value=True)
        view = ms[(ms["category"].isin(cats)) | (len(cats) == 0)]
        view = view[(view["due_date"].str[:4].isin(sel_y)) | (len(sel_y) == 0)]
        if pri:
            view = view[view["priority"].isin(pri)]
        if hide_done:
            view = view[view["status"] != "완료"]

        def _ms(r):
            d = rules.days_left(r["due_date"])
            card(r["title"], f"{esc(r['due_date'])} · 담당 {esc(r['owner'] or '미지정')}" + (f" · {esc(r['note'])}" if r["note"] else ""),
                 (badge("완료", "green") if r["status"] == "완료" else dday_badge(d)) + priority_badge(r.get("priority")) + badge(r["category"], "gray") + badge(f"{r['project_year']}차년도", "gray"))
        grid(view.to_dict("records"), _ms)
    with t2:
        sub = table("SELECT '보조산출물' AS 구분, sub_output_id AS 코드, name AS 항목, due_date AS 기한, language AS 언어, owner AS 담당, status AS 상태, due_rule AS 규칙 "
                    "FROM sub_outputs WHERE due_date<>'' UNION ALL "
                    "SELECT '관리문서', mdoc_id, name, next_due, language, owner, status, due_rule FROM management_docs WHERE next_due<>'' ORDER BY 기한")
        ys2 = sorted({d[:4] for d in sub["기한"]})
        sel2 = st.multiselect("연도", ys2, default=[y for y in ys2 if y in (str(today.year), str(today.year + 1))], placeholder="전체", key="suby")
        sub = sub[(sub["기한"].str[:4].isin(sel2)) | (len(sel2) == 0)]
        nodate = table("SELECT COUNT(*) n FROM sub_outputs WHERE due_date='' OR due_date IS NULL")["n"][0]
        st.caption(f"날짜가 정해진 항목만 보입니다. '모니터링 후 2주 이내'처럼 사건 기준인 보조산출물 {nodate}종은 [5. 성과관리 › 보조산출물]에서 확인하고, 사건이 생기면 기한을 입력하세요.")

        def _sub(r):
            d = rules.days_left(r["기한"])
            done = r["상태"] in ("제출", "승인", "완료")
            card(r["항목"], f"기한 {esc(r['기한'])} ← {esc(r['규칙'] or '직접 입력')} · {esc(r['언어'])} · 담당 {esc(r['담당'] or '미지정')}",
                 (badge(r["상태"], "green") if done else dday_badge(d) + badge(r["상태"], "gray")) + badge(f"{r['구분']} {r['코드']}", "gray"))
        grid(sub.to_dict("records"), _sub)
    with t3:
        edit_tab("3_사업일정")
        st.caption("보조산출물·관리문서의 제출 기한은 [5. 성과관리]의 편집 탭에서 고칩니다.")

# ───────────────────────── 4. 사업관리 ─────────────────────────
elif page == MENUS[3]:
    st.title("4. 사업관리")
    t = st.tabs(["회의록·후속조치", "이해관계자", "주간업무보고", "문서 (RFP·PDM·2차자료)", "위험관리", "데이터 편집·저장"])
    with t[0]:
        meetings_tab()
    with t[1]:
        stakeholders_tab()
    with t[2]:
        weekly_tab()
    with t[3]:
        show_df(table("SELECT doc_id AS 문서ID, title AS 제목, doc_type AS 유형, doc_date AS 일자, source_org AS 출처, file_path AS 파일 FROM documents"))
        with st.container(border=True):
            st.markdown('<div class="card-title">문서 올리기</div>', unsafe_allow_html=True)
            with st.form("upload_docs", clear_on_submit=True, border=False):
                ups = st.file_uploader("회의록·보고서·2차자료 파일", accept_multiple_files=True)
                if st.form_submit_button("문서 폴더에 저장", type="primary") and ups:
                    for u in ups:
                        (storage.docs_dir() / Path(u.name).name).write_bytes(u.getbuffer())
                    n = storage.sync_docs(force=True)
                    st.success(f"{len(ups)}개 파일을 저장했습니다 → {storage.rel(storage.docs_dir())} (검색 색인 {n}건)")
            st.caption("AI 사업비서가 읽는 형식: .hwpx .docx .pdf(글자 PDF) .md .txt — 구형 .hwp와 그림으로 된 PDF는 읽지 못하니 .hwpx나 글자 PDF로 저장해 넣어 주세요. "
                       "pmc/99. pre 같은 참고자료 폴더(하위폴더 포함)에 넣은 파일도 자동으로 색인됩니다.")
            open_folder_button(storage.docs_dir(), key="open_docs")
    with t[4]:
        st.caption("출발점으로 PDM의 '중요가정'을 위험 항목으로 옮겨 두었습니다. 수준·상태·대응방안은 [데이터 편집·저장]의 '위험관리대장'에서 고칩니다.")
        lv = {"상": "red", "중": "org", "하": "blue"}
        grid(table("SELECT * FROM risks ORDER BY CASE level WHEN '상' THEN 0 WHEN '중' THEN 1 ELSE 2 END, risk_id").to_dict("records"),
             lambda r: card(r["description"], f"출처 {esc(r['source'])} · 담당 {esc(r['owner'] or '미지정')}" + (f"<br>대응: {esc(r['mitigation'])}" if r["mitigation"] else ""),
                            badge("위험 " + str(r["level"]), lv.get(r["level"], "gray")) + badge(r["status"], "red" if r["status"] == "발생" else "gray") + badge(r["risk_id"], "gray")))
    with t[5]:
        edit_tab("4_사업관리")

# ───────────────────────── 5. 성과관리 ─────────────────────────
elif page == MENUS[4]:
    wide_page()
    st.title("5. 성과관리")
    t = st.tabs(["성과점검표", "사업산출물", "보조산출물", "관리문서", "PDM 지표 (사업논리모형)", "센터별 월별 실적", "데이터 편집·저장"])
    with t[0]:                                   # KOICA 성과관리양식 v3.2 '2. 성과점검표' 배치
        show_flash()
        pms_section(ns="pms")
    with t[1]:
        outputs_tab()
    with t[2]:
        so = table("SELECT sub_output_id AS 코드, output_id AS 산출물, series AS 계열, name AS 보조산출물, due_rule AS [생산시점(RFP)], due_date AS 기한, language AS 언어, "
                   "owner AS 담당, status AS 상태, approval_method AS 승인방법, quality_criteria AS 품질기준 FROM sub_outputs")
        so["_k"] = pd.to_numeric(so["코드"].str.extract(r"(\d+)\D*$")[0], errors="coerce").fillna(0)   # a.10 이 a.2 뒤에 오도록
        so = so.sort_values(["계열", "_k"]).drop(columns="_k")
        ser = st.pills("계열", sorted(so["계열"].unique()), selection_mode="multi", default=None, key="ser")
        show_df(so[so["계열"].isin(ser)] if ser else so)
        st.caption(f"총 {len(so)}종 (RFP 보조산출물 표 기준). 승인방법·품질기준은 POD/OD에서 옮겨 적어야 합니다.")
    with t[3]:
        show_df(table("SELECT mdoc_id AS 코드, name AS 관리문서, due_rule AS [제출시점(RFP)], next_due AS 차기기한, cycle AS 주기, language AS 언어, contents AS 포함사항, "
                      "owner AS 담당, status AS 상태 FROM management_docs ORDER BY mdoc_id"))
    with t[4]:                                   # [사업산출물 › 사업논리모형(PDM)]과 같은 화면 (버전·수정·내려받기·근거자료)
        show_flash()
        pdm_section(ns="pdmtab")
    with t[5]:
        df = table("SELECT month, center_id, value FROM center_monthly WHERE metric='이용자수'")
        if df.empty:
            st.info("적재된 센터 실적이 없습니다.")
        else:
            st.subheader("센터별 월별 이용자 수")
            st.line_chart(df.pivot(index="month", columns="center_id", values="value"), height=460)
    with t[6]:
        edit_tab("5_성과관리")
        st.caption("사업산출물(6개)·사업논리모형(PDM)·성과점검표·사업변화모델은 [사업산출물] 탭의 [수정하기]로도 고칠 수 있습니다.")

# ───────────────────────── 6. 문서관리 ─────────────────────────
elif page == MENUS[5]:
    docs_page()

# ───────────────────────── 7. AI 사업비서 ─────────────────────────
elif page == MENUS[6]:
    st.title("7. AI 사업비서")
    chat_tab, q_tab = st.tabs(["묻고 답하기", "AI 점검 질문"])
    with chat_tab:
        if not agent.has_key():
            st.warning(".env 파일에 ANTHROPIC_API_KEY를 설정하면 사용할 수 있습니다.")
        st.session_state.setdefault("view", [])
        st.session_state.setdefault("history", [])
        bank = yaml.safe_load((ROOT / "prompts" / "question_bank.yaml").read_text(encoding="utf-8"))
        with st.expander("예시 질문 — 누르면 바로 질문합니다"):
            for stage, qs in bank.items():
                st.markdown(f"**{stage}**")
                for i, q in enumerate(qs):
                    if st.button(q, key=f"ex_{stage}_{i}"):
                        st.session_state.pending = q
        box = st.container(height=430, border=True)
        typed = st.chat_input("사업에 대해 물어보세요 (국문/영문)")
        q = typed or st.session_state.pop("pending", None)
        with box:
            if not st.session_state.view and not q:
                st.markdown('<div class="card-meta">아직 대화가 없습니다. 아래 입력창에 질문을 적어 보세요.</div>', unsafe_allow_html=True)
            for role, text in st.session_state.view:
                st.chat_message(role).markdown(text)
            if q:
                st.chat_message("user").markdown(q)
                with st.spinner("사업자료를 확인하는 중…"):
                    try:
                        res = agent.ask(q, st.session_state.history)
                        st.session_state.history, ans = res["messages"], res["answer"]
                        with st.expander(f"조회 내역 ({len(res['tool_calls'])}건)"):
                            st.json(res["tool_calls"])
                    except Exception as e:
                        ans = f"오류가 발생했습니다: {e}"
                st.chat_message("assistant").markdown(ans)
                st.session_state.view += [("user", q), ("assistant", ans)]
        c1, c2, c3 = st.columns([1.2, 1, 3])
        if c1.button("이 대화 저장", width="stretch", disabled=not st.session_state.view):
            st.success(f"저장했습니다 → {storage.rel(storage.save_conversation(st.session_state.view))}")
        with c2:
            open_folder_button(storage.folder("7_AI사업비서"), key="open_ai")
        c3.caption("모든 질문·답변은 pmc/7_AI사업비서/질의응답기록.csv 에 자동으로 쌓입니다.")
    with q_tab:
        st.markdown("자동 점검에서 발견된 빈칸·이상 징후를 AI가 담당자에게 질문합니다. 답변은 지식베이스에 남아 보고서의 근거가 됩니다.")
        c1, c2 = st.columns([1, 2])
        use_llm = c2.checkbox("LLM으로 질문 문장 다듬기", value=False, disabled=not agent.has_key())
        if c1.button("새 질문 생성", type="primary", width="stretch"):
            st.success(f"{questioner.generate(use_llm)}건 생성했습니다.")
        for r in table("SELECT * FROM ai_questions ORDER BY status, id").to_dict("records"):
            with st.container(border=True):
                done = r["status"] == "답변완료"
                st.markdown(f'{badge(r["trigger_type"], "org")}{badge("→ " + str(r["assignee"]), "gray")}{badge(r["status"], "green" if done else "blue")}'
                            f'<div class="card-title" style="font-weight:600">{esc(r["question"])}</div>', unsafe_allow_html=True)
                if done:
                    st.info(r["answer"])
                else:
                    txt = st.text_area("답변", key=f"a{r['id']}", label_visibility="collapsed", placeholder="답변을 적어 주세요")
                    if st.button("답변 저장", key=f"b{r['id']}") and txt.strip():
                        questioner.answer(int(r["id"]), txt.strip())
                        st.rerun()

# ───────────────────────── 회원관리 (v0.8, 관리자) ─────────────────────────
elif page == ACCOUNTS:
    accounts_page()

# ───────────────────────── 문제보고 ─────────────────────────
else:
    st.title("문제보고")
    st.markdown("사용하다가 문제가 생기거나 고치고 싶은 부분을 메모로 남겨 주세요. 저장된 메모는 아래에 칸별로 쌓이고, "
                f"`{storage.rel(storage.csv_path('issue_reports'))}` 파일에도 저장됩니다.")
    with st.container(border=True):
        with st.form("report", clear_on_submit=True, border=False):
            c1, c2, c3 = st.columns(3)
            author = c1.text_input("작성자 (선택)")
            menu = c2.selectbox("관련 메뉴", MENUS + ["기타"])
            kind = c3.selectbox("유형", ["오류", "개선 요청", "데이터 수정", "기타"])
            content = st.text_area("메모", height=160, placeholder="어떤 화면에서 무엇을 했을 때 어떤 문제가 있었는지 적어 주세요.")
            if st.form_submit_button("메모 저장", type="primary"):
                if content.strip():
                    feedback.add(author.strip(), menu, kind, content.strip())
                    st.success("저장했습니다.")
                else:
                    st.error("메모 내용을 입력해 주세요.")

    reports = feedback.all_reports()
    h1, h2 = st.columns([3, 1])
    h1.header(f"저장된 메모 ({len(reports)}건)")
    if reports:
        h2.download_button("엑셀용 CSV 내려받기", pd.DataFrame(reports).to_csv(index=False).encode("utf-8-sig"),
                           "issue_reports.csv", "text/csv", width="stretch")
    color = {"접수": "blue", "처리중": "org", "완료": "green"}

    def _rep(r):
        with st.container(border=True):
            st.markdown(f'{badge("#" + str(r["id"]), "gray")}{badge(r["kind"], "red" if r["kind"] == "오류" else "blue")}{badge(r["status"], color.get(r["status"], "gray"))}'
                        f'<div class="card-meta">{esc(r["created_at"])} · {esc(r["menu"])} · {esc(r["author"] or "익명")}</div>'
                        f'<div style="white-space:pre-wrap; margin-top:.5rem">{esc(r["content"])}</div>', unsafe_allow_html=True)
            new = st.selectbox("처리 상태", feedback.STATUSES, index=feedback.STATUSES.index(r["status"]), key=f"st_{r['id']}")
            if new != r["status"]:
                feedback.set_status(r["id"], new)
                st.rerun()
    grid(reports, _rep)

st.markdown(f'<div class="footer">{COPYRIGHT}</div>', unsafe_allow_html=True)
