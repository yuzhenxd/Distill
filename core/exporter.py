import json
import urllib.request

from .i18n import tr


def to_json(meeting: dict) -> str:
    r = meeting["result"]
    data = {
        "title": meeting["title"],
        "created_at": meeting["created_at"],
        "source": meeting["source"],
        "meeting_summary": r["meeting_summary"],
        "key_decisions": r["key_decisions"],
        "action_items": [{k: v for k, v in t.items() if k != "id"} for t in r["action_items"]],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def to_markdown(meeting: dict) -> str:
    r = meeting["result"]
    lines = [
        f"# {meeting['title']}",
        "",
        f"> 时间：{meeting['created_at']}　来源：{meeting['source']}",
        "",
        "## 会议摘要",
        "",
        r["meeting_summary"] or "（无）",
        "",
        "## 关键决策",
        "",
    ]
    lines += [f"{i}. {d}" for i, d in enumerate(r["key_decisions"], 1)] or ["（无）"]
    lines += ["", "## 行动项", ""]
    if r["action_items"]:
        lines += ["| 任务 | 负责人 | 截止时间 | 优先级 | 状态 |", "| --- | --- | --- | --- | --- |"]
        for t in r["action_items"]:
            lines.append(
                f"| {_cell(t['task_title'])} | {_cell(t['assignee'])} | {_cell(t['deadline'])} "
                f"| {t['priority']} | {t['status']} |"
            )
        quotes = [t for t in r["action_items"] if t["source_quote"]]
        if quotes:
            lines += ["", "### 原文依据", ""]
            lines += [f"- **{t['task_title']}**：“{t['source_quote']}”" for t in quotes]
    else:
        lines.append("（无）")
    return "\n".join(lines) + "\n"


def to_feishu_post(meeting: dict) -> dict:
    """飞书自定义机器人「富文本 post」消息格式。"""
    r = meeting["result"]

    def text(t: str) -> list:
        return [{"tag": "text", "text": t}]

    content = [text("【会议摘要】"), text(r["meeting_summary"] or "（无）"), text(""), text("【关键决策】")]
    content += [text(f"{i}. {d}") for i, d in enumerate(r["key_decisions"], 1)] or [text("（无）")]
    content += [text(""), text("【行动项】")]
    for t in r["action_items"]:
        content.append(text(
            f"☐ {t['task_title']}｜负责人：{t['assignee']}｜截止：{t['deadline']}"
            f"｜优先级：{t['priority']}｜状态：{t['status']}"
        ))
    if not r["action_items"]:
        content.append(text("（无）"))
    return {
        "msg_type": "post",
        "content": {"post": {"zh_cn": {"title": f"📋 {meeting['title']}", "content": content}}},
    }


def push_feishu(webhook: str, payload: dict) -> str:
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except OSError as e:
        raise RuntimeError(tr("无法连接飞书：{error}", error=e)) from None
    code = body.get("code", body.get("StatusCode", 0))
    if code != 0:
        raise RuntimeError(tr("飞书返回错误（{code}）：{message}", code=code,
                              message=body.get("msg") or body.get("StatusMessage")))
    return tr("已推送到飞书群")
