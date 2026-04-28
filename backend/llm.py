"""
统一 LLM 调用模块

支持 OpenAI 官方 API 和 OpenAI-compatible 中转站 API

环境变量配置:
- OPENAI_API_KEY: API 密钥（必需）
- OPENAI_BASE_URL: API base URL（可选，默认使用 OpenAI 官方）
  - 示例: https://your-proxy-domain.com/v1
- OPENAI_MODEL: 模型名称（可选，默认 gpt-4o-mini）
"""

from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple

import requests


# ──────────────────────────────────────────────────
# 配置读取
# ──────────────────────────────────────────────────

def get_llm_config() -> Dict[str, Any]:
    """获取 LLM 配置"""
    return {
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "base_url": os.getenv("OPENAI_BASE_URL", "").strip(),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
    }


def is_llm_available() -> bool:
    """检查 LLM 是否可用"""
    config = get_llm_config()
    return bool(config["api_key"])


def get_api_endpoint() -> str:
    """获取 API endpoint"""
    config = get_llm_config()
    if config["base_url"]:
        # 移除末尾斜杠
        base_url = config["base_url"].rstrip("/")
        return f"{base_url}/chat/completions"
    return "https://api.openai.com/v1/chat/completions"


# ──────────────────────────────────────────────────
# 错误类型定义
# ──────────────────────────────────────────────────

class LLMError(Exception):
    """LLM 调用基础错误"""
    pass


class LLMConfigError(LLMError):
    """配置错误"""
    pass


class LLMAPIError(LLMError):
    """API 调用错误"""
    def __init__(self, message: str, status_code: int = 0, error_type: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


# ──────────────────────────────────────────────────
# API 调用
# ──────────────────────────────────────────────────

def _make_request(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """
    发起 LLM API 请求
    
    Args:
        messages: 消息列表
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数
    
    Returns:
        API 响应 JSON
    """
    config = get_llm_config()
    
    if not config["api_key"]:
        raise LLMConfigError("OPENAI_API_KEY 未配置")
    
    endpoint = get_api_endpoint()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=120,
        )
        
        if response.status_code != 200:
            error_detail = ""
            error_type = ""
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {}).get("message", response.text)
                error_type = error_data.get("error", {}).get("type", "")
            except Exception:
                error_detail = response.text
            
            # 友好的错误消息
            if response.status_code == 401:
                raise LLMAPIError(
                    "API 密钥无效或已过期",
                    status_code=401,
                    error_type="authentication_error"
                )
            elif response.status_code == 403:
                raise LLMAPIError(
                    "无权访问，请检查 API 密钥权限",
                    status_code=403,
                    error_type="permission_error"
                )
            elif response.status_code == 429:
                raise LLMAPIError(
                    "请求频率超限，请稍后重试",
                    status_code=429,
                    error_type="rate_limit_error"
                )
            elif response.status_code >= 500:
                raise LLMAPIError(
                    "AI 服务端错误，请稍后重试",
                    status_code=response.status_code,
                    error_type="server_error"
                )
            else:
                raise LLMAPIError(
                    f"API 请求失败: {error_detail}",
                    status_code=response.status_code,
                    error_type=error_type
                )
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise LLMAPIError(
            "AI 请求超时，请检查网络或中转站状态",
            status_code=0,
            error_type="timeout"
        )
    except requests.exceptions.ConnectionError as e:
        raise LLMAPIError(
            f"无法连接到 AI 服务: {str(e)}",
            status_code=0,
            error_type="connection_error"
        )
    except LLMAPIError:
        raise
    except Exception as e:
        raise LLMAPIError(
            f"AI 调用失败: {str(e)}",
            status_code=0,
            error_type="unknown_error"
        )


# ──────────────────────────────────────────────────
# 统一调用接口 - 字典格式返回
# ──────────────────────────────────────────────────

def call_llm(
    prompt: str,
    system_prompt: str = "",
    model: str = "",
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """
    统一的 LLM 调用接口

    Returns:
        {
            "ok": bool,
            "content": str,
            "error": str | None
        }

    示例:
        result = call_llm("请总结以下内容...")
        if result["ok"]:
            print(result["content"])
        else:
            print(f"Error: {result['error']}")
    """
    config = get_llm_config()

    # 检查配置
    if not config["api_key"]:
        return {"ok": False, "content": "", "error": "OPENAI_API_KEY 未配置"}

    # 使用指定模型或默认模型
    model = model.strip() or config["model"]

    # 构建消息
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = _make_request(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 解析响应
        content = ""
        if response.get("choices"):
            choice = response["choices"][0]
            if choice.get("message"):
                content = choice["message"].get("content", "")

        if not content:
            return {"ok": False, "content": "", "error": "AI 返回内容为空"}

        return {"ok": True, "content": content.strip(), "error": None}

    except LLMAPIError as e:
        return {"ok": False, "content": "", "error": str(e)}
    except Exception as e:
        return {"ok": False, "content": "", "error": f"AI 调用异常: {str(e)}"}


def call_llm_json(
    prompt: str,
    system_prompt: str = "",
    model: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> Dict[str, Any]:
    """
    调用 LLM 并期望返回 JSON 格式结果

    Returns:
        {
            "ok": bool,
            "data": dict | list | None,
            "error": str | None
        }
    """
    result = call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if not result["ok"]:
        return {"ok": False, "data": None, "error": result["error"]}

    # 尝试解析 JSON
    try:
        return {"ok": True, "data": json.loads(result["content"]), "error": None}
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', result["content"])
        if json_match:
            try:
                return {"ok": True, "data": json.loads(json_match.group()), "error": None}
            except json.JSONDecodeError:
                pass
        return {"ok": False, "data": None, "error": f"AI 返回不是有效 JSON: {result['content'][:100]}..."}


# ──────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────

def translate_to_zh(text: str) -> str:
    """翻译英文到中文"""
    if not text.strip():
        return ""
    
    prompt = f"把下面英文翻译成地道流畅的中文，保留语气与梗，不要解释。\n\n英文：{text}\n\n中文："
    success, result = call_llm(prompt, max_tokens=500)
    
    if success:
        return result
    return ""


def summarize_text(text: str, max_length: int = 200) -> str:
    """总结文本"""
    prompt = f"用不超过 {max_length} 个字总结以下内容：\n\n{text}"
    success, result = call_llm(prompt, max_tokens=400)
    
    if success:
        return result
    return text[:max_length] + "..."


# ──────────────────────────────────────────────────
# 诊断信息
# ──────────────────────────────────────────────────

def get_llm_diagnostic() -> Dict[str, Any]:
    """获取 LLM 诊断信息"""
    config = get_llm_config()

    return {
        "api_key_configured": bool(config["api_key"]),
        "api_key_preview": config["api_key"][:10] + "..." if config["api_key"] else "",
        "base_url": config["base_url"] or "https://api.openai.com/v1 (默认)",
        "model": config["model"],
        "endpoint": get_api_endpoint(),
    }


def check_llm_health() -> Dict[str, Any]:
    """
    检查 LLM 服务健康状态

    Returns:
        {
            "enabled": bool,
            "base_url": str,
            "model": str,
            "status": str,  # "ok" when enabled and working
            "error": str | None
        }
    """
    config = get_llm_config()

    if not config["api_key"]:
        return {
            "enabled": False,
            "base_url": config["base_url"] or "https://api.openai.com/v1",
            "model": config["model"],
            "status": "error",
            "error": "OPENAI_API_KEY 未配置"
        }

    result = call_llm(
        prompt="只回复 OK",
        system_prompt="你是一个有帮助的助手。",
        max_tokens=10,
    )

    if result["ok"]:
        return {
            "enabled": True,
            "base_url": config["base_url"] or "https://api.openai.com/v1",
            "model": config["model"],
            "status": "ok",
            "error": None
        }
    else:
        return {
            "enabled": False,
            "base_url": config["base_url"] or "https://api.openai.com/v1",
            "model": config["model"],
            "status": "error",
            "error": result["error"]
        }


if __name__ == "__main__":
    # 测试代码
    print("LLM 诊断信息:")
    diag = get_llm_diagnostic()
    for key, value in diag.items():
        print(f"  {key}: {value}")
    
    print("\n测试调用:")
    success, result = call_llm("你好，请用一句话介绍自己")
    if success:
        print(f"成功: {result}")
    else:
        print(f"失败: {result}")
