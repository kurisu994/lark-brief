"""推送模块：钉钉机器人 Webhook 推送（HMAC-SHA256 加签）"""

import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse

import httpx

logger = logging.getLogger(__name__)


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
            f"{self.webhook_url}"
            f"?access_token={self.access_token}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
        )

    async def push(self, title: str, content: str) -> bool:
        """发送 Markdown 消息到钉钉群

        Args:
            title: 消息标题（在通知栏显示）
            content: Markdown 格式的消息内容

        Returns:
            是否发送成功
        """
        url = self._build_url()
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
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
