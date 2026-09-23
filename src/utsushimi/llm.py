"""LLM の口：Anthropic の公式 SDK の非同期クライアント（ADR 0003）。核のスレッドだけが使う。"""
import os

from anthropic import AsyncAnthropic

from . import REPO


def _api_key():
    if "ANTHROPIC_API_KEY" in os.environ:
        return os.environ["ANTHROPIC_API_KEY"]
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "ANTHROPIC_API_KEY":
                return value.strip().strip('"').strip("'")
    return None


class Llm:
    def __init__(self, config: dict):
        self.client = AsyncAnthropic(api_key=_api_key())
        self.model = config["model"]
        self.effort = config["effort"]
        self.max_tokens = config["max_tokens"]

    async def reply(self, system: list[dict], history: list[tuple[str, str]], on_text, cue: str | None = None):
        """system は文脈の前半（区切りは組む側が付ける）。history は古い順の (speaker, body)。
        cue は保存しない主人側の合図（最初の挨拶）。届いた文字を on_text に渡し、(本文, stop_reason, usage) を返す。

        過去の返事は本文の文字だけを渡す（思考のブロックは渡さない。design.md §4.2）。
        """
        if cue:
            history = [*history, ("master", cue)]
        messages = []
        for speaker, body in history:
            role = "user" if speaker == "master" else "assistant"
            if messages and messages[-1]["role"] == role:
                # 強制終了で返事が欠けると主人の発言が続く。続いた分は1つにまとめる
                messages[-1]["content"] += "\n" + body
            else:
                messages.append({"role": role, "content": body})
        while messages and messages[0]["role"] != "user":
            messages.pop(0)

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": self.effort},
        ) as stream:
            async for text in stream.text_stream:
                on_text(text)
            final = await stream.get_final_message()
        if final.stop_reason == "refusal":
            return None, final.stop_reason, final.usage
        body = "".join(b.text for b in final.content if b.type == "text")
        return body, final.stop_reason, final.usage
