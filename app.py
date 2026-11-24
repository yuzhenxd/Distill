"""MeetingFlow AI - Streamlit 前端：输入 -> 智能提炼 -> 任务看板 -> JSON 导出。

运行：streamlit run app.py
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from agent import (
    MeetingFlowError,
    analyze_meeting,
    decode_text_file,
    deepseek_config,
    ollama_config,
    transcribe_audio,
    DEEPSEEK_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from schemas import PRIORITIES, STATUSES, TaskItem

load_dotenv()

st.set_page_config(page_title="MeetingFlow AI", page_icon="📋", layout="wide")

# ---------------------------------------------------------------- 样式

PRIORITY_COLORS = {"High": "#E5484D", "Medium": "#F5A623", "Low": "#30A46C"}
STATUS_META = {
    "To Do": ("📥 To Do", "#6E7B91"),
    "In Progress": ("🔧 In Progress", "#3B82F6"),
    "Done": ("✅ Done", "#30A46C"),
}

st.markdown(
    """
<style>
.block-container { padding-top: 2rem; }
.mf-card {
    background: var(--background-color, #ffffff);
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 12px;
    padding: 14px 16px 12px;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    border-left: 5px solid var(--mf-priority, #F5A623);
}
.mf-card-title { font-weight: 600; font-size: .95rem; margin-bottom: 8px; line-height: 1.35; }
.mf-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.mf-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: .72rem; font-weight: 600; color: #fff;
}
.mf-badge.assignee { background: #5B5FC7; }
.mf-badge.deadline { background: #8B6F47; }
.mf-quote {
    font-size: .76rem; opacity: .75; border-left: 3px solid rgba(128,128,128,.4);
    padding: 4px 8px; margin: 0; border-radius: 4px; background: rgba(128,128,128,.08);
}
.mf-col-header {
    font-weight: 700; font-size: .9rem; padding: 6px 12px; border-radius: 8px;
    color: #fff; margin-bottom: 10px; display: inline-block;
}
.mf-summary-box {
    border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
    padding: 14px 18px; margin-bottom: 10px; background: rgba(91,95,199,.06);
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- 模拟会议纪要

DEMO_TRANSCRIPT = """【2026-11-24 支付中台 V2.3 版本上线前站会（录音转写）】

王总：各位早，先说正事，今天把 V2.3 上线前的事项全部过一遍。对了昨晚那场球大家看了吗？
李经理：看了看了，最后绝杀太刺激了。咳，回到正题，我这边验收清单已经列好了。
王总：好。张工，支付网关那边什么进度？
张工：联调环境已经通了 80%，还差退款回调。张工下周三前把支付 API 调通，这个我立字据，没问题。
王总：行，那就定下周三。退款回调是重中之重，优先级最高，出了问题就是资损。
李经理：那我这边配合，李经理周五下班前提交验收材料，包括测试报告和回归用例清单。
王总：可以。小刘，监控大盘呢？
小刘：Grafana 面板搭了一半，我争取本周日前把支付成功率和耗时的告警规则配完，这个不算特别急，但上线前得有。
王总：嗯，算中等优先级吧。另外强调一个决定：下周一上线前不再新增需求，谁来提都不行，统一排到 V2.4。
李经理：同意，冻结需求，不然测试来不及。
张工：顺便说一句，中午那家新开的川菜馆要不要试试？
王总：哈哈先开完会。最后一件事，陈姐，用户通知的文案周一早上十点前要给到运营，上线公告要提前挂出去。
陈姐：收到，周一早上十点前给到运营。
王总：好，散会。记住：下周三支付 API、周五验收材料、周一需求冻结，都别掉链子。
"""

# ---------------------------------------------------------------- 会话状态

ss = st.session_state
ss.setdefault("transcript", "")
ss.setdefault("summary", "")
ss.setdefault("decisions", [])
ss.setdefault("tasks", [])  # list[dict]，与 TaskItem 字段一致


def load_demo() -> None:
    ss.transcript = DEMO_TRANSCRIPT


def set_task_status(task_id: str, widget_key: str) -> None:
    for t in ss.tasks:
        if t["id"] == task_id:
            t["status"] = ss[widget_key]


def delete_task(task_id: str) -> None:
    ss.tasks = [t for t in ss.tasks if t["id"] != task_id]


# ---------------------------------------------------------------- 侧边栏：引擎配置

with st.sidebar:
    st.title("📋 MeetingFlow AI")
    st.caption("从开会到执行的最后一公里")
    st.divider()

    st.subheader("推理引擎")
    engine_choice = st.radio(
        "选择推理引擎",
        ["DeepSeek 云端 API（推荐，高精度）", "本地私有化模型（Ollama + Llama 3）"],
        label_visibility="collapsed",
    )
    use_deepseek = engine_choice.startswith("DeepSeek")

    if use_deepseek:
        api_key = st.text_input(
            "DeepSeek API Key",
            value=os.getenv("DEEPSEEK_API_KEY", ""),
            type="password",
            help="自动读取环境变量 DEEPSEEK_API_KEY，也可在此直接粘贴",
        )
        st.caption(f"模型：`{DEEPSEEK_MODEL}` ｜ JSON Mode 已强制开启")
        engine_cfg = deepseek_config(api_key.strip())
    else:
        ollama_model = st.text_input("本地模型名称", value=OLLAMA_MODEL)
        st.caption(f"Base URL：`{OLLAMA_BASE_URL}`")
        st.info("敏感数据不出内网。请先安装 Ollama 并执行 `ollama pull llama3`。", icon="🔒")
        engine_cfg = ollama_config(ollama_model.strip() or OLLAMA_MODEL)

    st.divider()
    st.button("🎬 加载模拟会议纪要", on_click=load_demo, use_container_width=True, type="secondary")
    st.caption("课堂演示：点击上方按钮，再点主区域的「开始智能提炼」。")

# ---------------------------------------------------------------- 输入层

st.header("MeetingFlow AI · 会议转写 → 任务看板")

tab_text, tab_file, tab_audio = st.tabs(["✍️ 粘贴文本", "📄 上传 .txt", "🎙️ 上传音频"])

with tab_text:
    ss.transcript = st.text_area(
        "会议转写文本",
        value=ss.transcript,
        height=240,
        placeholder="把会议录音转写文本粘贴到这里，或在侧边栏点击「加载模拟会议纪要」…",
    )

with tab_file:
    txt_file = st.file_uploader("选择 .txt 会议转写文件", type=["txt"])
    if txt_file is not None:
        ss.transcript = decode_text_file(txt_file.getvalue())
        st.success(f"已读取 `{txt_file.name}`（{len(ss.transcript)} 字），切回「粘贴文本」页可查看。")

with tab_audio:
    audio_file = st.file_uploader("选择音频文件", type=["mp3", "wav"])
    if audio_file is not None and st.button("开始转写音频"):
        try:
            with st.spinner("正在转写音频…"):
                suffix = "." + audio_file.name.rsplit(".", 1)[-1].lower()
                text, real = transcribe_audio(audio_file.getvalue(), suffix)
            ss.transcript = text
            if real:
                st.success("音频转写完成，切回「粘贴文本」页可查看。")
            else:
                st.warning("未安装 faster-whisper，已使用模拟转写结果演示完整链路。")
        except MeetingFlowError as e:
            st.error(str(e))

run = st.button("🚀 开始智能提炼", type="primary", use_container_width=True)

if run:
    try:
        with st.spinner(f"正在调用 {engine_cfg.label}（{engine_cfg.model}）分析会议内容…"):
            result = analyze_meeting(ss.transcript, engine_cfg)
        ss.summary = result.summary
        ss.decisions = result.decisions
        ss.tasks = [t.model_dump() for t in result.tasks]
        st.toast(f"提炼完成：{len(ss.tasks)} 个任务，{len(ss.decisions)} 条决策", icon="✅")
    except MeetingFlowError as e:
        st.error(str(e))

# ---------------------------------------------------------------- 摘要与决策

if ss.summary or ss.decisions:
    col_sum, col_dec = st.columns(2)
    with col_sum:
        st.subheader("📌 会议核心摘要")
        st.markdown(
            f'<div class="mf-summary-box">{html.escape(ss.summary)}</div>',
            unsafe_allow_html=True,
        )
    with col_dec:
        st.subheader("⚖️ 关键决策结论")
        if ss.decisions:
            items = "".join(f"<li>{html.escape(d)}</li>" for d in ss.decisions)
            st.markdown(f'<div class="mf-summary-box"><ul style="margin:0 0 0 1rem;">{items}</ul></div>',
                        unsafe_allow_html=True)
        else:
            st.caption("本次会议未识别到明确决策。")

# ---------------------------------------------------------------- 任务看板


def task_card_html(task: dict) -> str:
    color = PRIORITY_COLORS.get(task["priority"], "#F5A623")
    quote = (
        f'<p class="mf-quote">🗣 {html.escape(task["source_quote"])}</p>'
        if task.get("source_quote")
        else ""
    )
    return (
        f'<div class="mf-card" style="--mf-priority:{color};">'
        f'<div class="mf-card-title">{html.escape(task["title"])}</div>'
        f'<div class="mf-badges">'
        f'<span class="mf-badge assignee">👤 {html.escape(task["assignee"])}</span>'
        f'<span class="mf-badge deadline">⏰ {html.escape(task["deadline"])}</span>'
        f'<span class="mf-badge" style="background:{color};">{task["priority"]}</span>'
        f"</div>{quote}</div>"
    )


def render_task(task: dict) -> None:
    st.markdown(task_card_html(task), unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    status_key = f"status_{task['id']}"
    c1.selectbox(
        "状态",
        STATUSES,
        index=STATUSES.index(task["status"]),
        key=status_key,
        on_change=set_task_status,
        args=(task["id"], status_key),
        label_visibility="collapsed",
    )
    c2.button("🗑️", key=f"del_{task['id']}", on_click=delete_task, args=(task["id"],),
              help="删除该任务", use_container_width=True)


if ss.tasks:
    st.divider()
    head_l, head_r = st.columns([3, 2])
    head_l.subheader("🗂️ 自动化任务看板")
    view = head_r.radio("视图", ["按状态分列", "按负责人筛选"], horizontal=True,
                        label_visibility="collapsed")

    if view == "按状态分列":
        cols = st.columns(3)
        for col, status in zip(cols, STATUSES):
            label, color = STATUS_META[status]
            with col:
                count = sum(1 for t in ss.tasks if t["status"] == status)
                st.markdown(
                    f'<span class="mf-col-header" style="background:{color};">{label} · {count}</span>',
                    unsafe_allow_html=True,
                )
                for task in ss.tasks:
                    if task["status"] == status:
                        render_task(task)
    else:
        assignees = sorted({t["assignee"] for t in ss.tasks})
        picked = st.multiselect("负责人", assignees, default=assignees)
        cols = st.columns(3)
        shown = [t for t in ss.tasks if t["assignee"] in picked]
        for i, task in enumerate(shown):
            with cols[i % 3]:
                render_task(task)
        if not shown:
            st.caption("没有符合筛选条件的任务。")

    # ---- 手动新增任务
    with st.expander("➕ 手动新增任务"):
        with st.form("add_task", clear_on_submit=True):
            f1, f2 = st.columns(2)
            new_title = f1.text_input("任务标题 *")
            new_assignee = f2.text_input("负责人", value="未指定")
            f3, f4, f5 = st.columns(3)
            new_deadline = f3.text_input("截止时间", value="待定")
            new_priority = f4.selectbox("优先级", PRIORITIES, index=1)
            new_status = f5.selectbox("状态", STATUSES, index=0)
            if st.form_submit_button("添加任务", use_container_width=True):
                if new_title.strip():
                    item = TaskItem(
                        title=new_title, assignee=new_assignee, deadline=new_deadline,
                        priority=new_priority, status=new_status, source_quote="（手动添加）",
                    )
                    ss.tasks.append(item.model_dump())
                    st.rerun()
                else:
                    st.warning("任务标题不能为空。")

    # ---------------------------------------------------------------- JSON 导出
    st.divider()
    st.subheader("📤 标准 JSON 导出（可对接飞书 / Trello）")
    export_payload = {
        "meta": {
            "tool": "MeetingFlow AI",
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "task_count": len(ss.tasks),
        },
        "summary": ss.summary,
        "decisions": ss.decisions,
        "tasks": [{k: v for k, v in t.items()} for t in ss.tasks],
    }
    export_json = json.dumps(export_payload, ensure_ascii=False, indent=2)
    e1, e2 = st.columns([1, 3])
    e1.download_button(
        "⬇️ 下载 meetingflow_tasks.json",
        data=export_json.encode("utf-8"),
        file_name="meetingflow_tasks.json",
        mime="application/json",
        use_container_width=True,
    )
    with e2.expander("查看 / 复制 JSON（代码框右上角有复制按钮）"):
        st.code(export_json, language="json")
else:
    st.info("👈 先在侧边栏点击「加载模拟会议纪要」，再点击「开始智能提炼」，10 秒演示完整链路。", icon="💡")
