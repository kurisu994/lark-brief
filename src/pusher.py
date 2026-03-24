"""推送模块：钉钉 & 飞书机器人 Webhook 推送（HMAC-SHA256 加签）

两个推送器共享同一套简报解析逻辑，各自按平台特性输出美化格式：
- 钉钉：Markdown（标题 + 引用日期 + 加粗编号 + 可点击链接）
- 飞书：Interactive Card（卡片头 + 日期高亮 + 分隔线 + 统计页脚）
"""

import base64
import hashlib
import hmac
import logging
import os
import re
import time
import urllib.parse

import httpx

logger = logging.getLogger(__name__)

# ── 简报内容结构 ──
# (编号, 摘要, url)
type BriefItem = tuple[str, str, str]


def _parse_brief_content(content: str) -> tuple[str, list[BriefItem]]:
    """解析简报纯文本，提取日期行和新闻条目

    Args:
        content: compose_brief() 生成的简报文本

    Returns:
        (date_line, items) — items 为 [(编号, 摘要, url), ...]
    """
    lines = content.strip().split("\n")

    # 提取日期行（包含"年""月""日"的行）
    date_line = ""
    for line in lines:
        s = line.strip()
        if s and "年" in s and "月" in s and "日" in s:
            date_line = s
            break

    # 提取新闻条目
    items: list[BriefItem] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            num, summary = m.group(1), m.group(2)
            url = ""
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith("🔗"):
                    url = next_line.replace("🔗", "").strip()
                    i += 1
            items.append((num, summary, url))
        i += 1

    return date_line, items


def _is_brief(content: str) -> bool:
    """判断内容是否为简报格式（而非告警等其他消息）"""
    return content.lstrip().startswith("今日简报")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 钉钉推送
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class DingTalkPusher:
    """钉钉自定义机器人推送

    安全设置使用「加签」模式：
    1. 用 timestamp + "\\n" + secret 做 HMAC-SHA256
    2. 签名结果 Base64 编码后 URL encode
    3. 将 timestamp 和 sign 附加到 Webhook URL 参数中
    """

    def __init__(self, webhook_url: str | None = None):
        """初始化钉钉推送器

        Args:
            webhook_url: Webhook 基础 URL（来自 settings.yaml）
                         access_token 和 secret 从环境变量读取
        """
        self.webhook_url = webhook_url or os.environ.get(
            "D_WEB_HOOK", "https://oapi.dingtalk.com/robot/send"
        )
        self.access_token = os.environ.get("D_ACCESS_TOKEN", "")
        self.secret = os.environ.get("D_SECRET", "")

        if not self.access_token:
            logger.warning("未配置 D_ACCESS_TOKEN 环境变量")
        if not self.secret:
            logger.warning("未配置 D_SECRET 环境变量")

    def _sign(self) -> tuple[str, str]:
        """生成钉钉加签参数

        Returns:
            (timestamp, sign) 元组
        """
        timestamp = str(int(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
        return timestamp, sign

    def _build_url(self) -> str:
        """构建完整的带签名的 Webhook URL"""
        timestamp, sign = self._sign()
        return (
            f"{self.webhook_url}?access_token={self.access_token}"
            f"&timestamp={timestamp}&sign={sign}"
        )

    @staticmethod
    def _format_brief(content: str) -> str:
        """将简报纯文本转换为钉钉美化 Markdown

        格式：### 标题 → > 引用日期 → 加粗编号 + 可点击链接 → 引用统计
        """
        date_line, items = _parse_brief_content(content)

        parts: list[str] = ["### ☀️ 今日简报\n"]

        if date_line:
            parts.append(f"> 📅 {date_line}\n")

        for num, summary, url in items:
            if url:
                parts.append(f"**{num}.** {summary}\n\n[🔗 原文链接]({url})\n")
            else:
                parts.append(f"**{num}.** {summary}\n")

        parts.append(f"> 📊 共 {len(items)} 条资讯 · 由云雀简报自动生成")
        return "\n".join(parts)

    async def push(self, title: str, content: str) -> bool:
        """发送 Markdown 消息到钉钉群

        简报内容自动转换为美化格式（标题 + 引用日期 + 加粗编号 + 可点击链接），
        告警等其他消息保持原样。

        Args:
            title: 消息标题（在通知栏显示）
            content: Markdown 格式的消息内容

        Returns:
            是否发送成功
        """
        text = self._format_brief(content) if _is_brief(content) else content

        url = self._build_url()
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                result = response.json()

            if result.get("errcode") == 0:
                logger.info("✅ 钉钉推送成功")
                return True
            else:
                logger.warning("❌ 钉钉推送失败: %s", result.get("errmsg", "未知错误"))
                return False
        except Exception as e:
            logger.error("❌ 钉钉推送异常: %s", e)
            return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 飞书推送
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FeishuPusher:
    """飞书自定义机器人推送

    安全设置使用「签名校验」模式：
    1. 用 (timestamp + "\\n" + secret) 作为 HMAC-SHA256 的 key，消息体为空
    2. 签名结果 Base64 编码
    3. 将 timestamp 和 sign 放入 POST 请求体中
    """

    def __init__(self, webhook_url: str | None = None):
        """初始化飞书推送器

        Args:
            webhook_url: Webhook 基础 URL（来自 settings.yaml）
                         access_token 和 secret 从环境变量读取
        """
        self.webhook_url = webhook_url or "https://open.feishu.cn/open-apis/bot/v2/hook"
        self.access_token = os.environ.get("FS_ACCESS_TOKEN", "")
        self.secret = os.environ.get("FS_SECRET", "")

        if not self.access_token:
            logger.warning("未配置 FS_ACCESS_TOKEN 环境变量")
        if not self.secret:
            logger.warning("未配置 FS_SECRET 环境变量")

    def _sign(self) -> tuple[str, str]:
        """生成飞书加签参数

        飞书签名与钉钉的区别：
        - 时间戳单位为秒（非毫秒）
        - HMAC key 为 (timestamp + "\\n" + secret)，消息体为空字节串
        - 签名直接 Base64 编码，无需 URL encode

        Returns:
            (timestamp, sign) 元组
        """
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            b"",
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return timestamp, sign

    def _build_url(self) -> str:
        """构建飞书 Webhook URL（access_token 在路径中）"""
        return f"{self.webhook_url}/{self.access_token}"

    @staticmethod
    def _format_brief_elements(content: str) -> list[dict]:
        """将简报纯文本转换为飞书卡片元素列表

        格式：📅 日期高亮 → 分隔线 → 加粗编号 + 可点击链接 → 分隔线 → 统计页脚
        """
        date_line, items = _parse_brief_content(content)

        elements: list[dict] = []

        # 日期行：带日历 emoji 高亮显示
        if date_line:
            elements.append({"tag": "markdown", "content": f"📅 **{date_line}**"})
            elements.append({"tag": "hr"})

        # 新闻条目：加粗编号 + 可点击链接
        formatted = []
        for num, summary, url in items:
            if url:
                formatted.append(f"**{num}.** {summary}\n[🔗 原文链接]({url})")
            else:
                formatted.append(f"**{num}.** {summary}")

        if formatted:
            elements.append({"tag": "markdown", "content": "\n\n".join(formatted)})

        # 底部分隔线 + 统计信息
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"📊 共 {len(items)} 条资讯 · 由云雀简报自动生成",
                }
            ],
        })

        return elements

    @staticmethod
    def _build_card(title: str, content: str) -> dict:
        """构建飞书消息卡片，自动识别简报内容并优化格式

        简报内容使用富文本卡片（加粗编号、可点击链接、日期高亮、统计页脚），
        其他消息（如告警）使用简单红色卡片。
        """
        if _is_brief(content):
            elements = FeishuPusher._format_brief_elements(content)
            template = "turquoise"
        else:
            elements = [{"tag": "markdown", "content": content}]
            template = "red"

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": template,
            },
            "elements": elements,
        }

    async def push(self, title: str, content: str) -> bool:
        """发送消息卡片到飞书群

        简报内容自动转换为富文本卡片（加粗编号、可点击链接、日期高亮），
        告警消息使用红色主题简单卡片。

        Args:
            title: 消息标题
            content: Markdown 格式的消息内容

        Returns:
            是否发送成功
        """
        url = self._build_url()
        timestamp, sign = self._sign()
        payload = {
            "timestamp": timestamp,
            "sign": sign,
            "msg_type": "interactive",
            "card": self._build_card(title, content),
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                result = response.json()

            if result.get("code") == 0:
                logger.info("✅ 飞书推送成功")
                return True
            else:
                logger.warning("❌ 飞书推送失败: %s", result.get("msg", "未知错误"))
                return False
        except Exception as e:
            logger.error("❌ 飞书推送异常: %s", e)
            return False
