"""LLM の口：Anthropic の公式 SDK の非同期クライアント（ADR 0003）。核のスレッドだけが使う。

呼び先は設定の `[llm] target` で替える（BH-37）：`anthropic` は本物、`fake` は API を呼ばずに決まった返事を返す。
"""
import hashlib
import json
import logging
import os

from anthropic import AsyncAnthropic

from . import REPO

log = logging.getLogger("utsushimi")
CONTINUATIONS = 3  # web search が pause_turn で止まったときに続きを頼む回数の上限


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


def log_usage(kind: str, usage):
    log.info("usage kind=%s input=%d cache_read=%d cache_write=%d output=%d", kind, usage.input_tokens,
             usage.cache_read_input_tokens or 0, usage.cache_creation_input_tokens or 0, usage.output_tokens)


def make(config: dict):
    """設定の呼び先から LLM の口を作る。"""
    return FakeLlm() if config["target"] == "fake" else Llm(config)


class Unfinished(Exception):
    """返事が終わりまで来なかった（max_tokens・refusal・pause_turn の続きの上限）。"""


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

    async def json(self, kind: str, system: str, prompt: str, schema: dict) -> dict:
        """構造化出力（JSON スキーマ）で1回呼ぶ。使用量は kind でログに残す。"""
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
        ) as stream:
            final = await stream.get_final_message()
        log_usage(kind, final.usage)
        if final.stop_reason != "end_turn":
            log.info("%s unfinished stop_reason=%s", kind, final.stop_reason)
            raise Unfinished(final.stop_reason)
        return json.loads("".join(b.text for b in final.content if b.type == "text"))

    async def text(self, kind: str, system: list[dict], prompt: str) -> str:
        """画面に流さない文を1回書かせる（日記）。使用量は kind でログに残す。"""
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": self.effort},
        ) as stream:
            final = await stream.get_final_message()
        log_usage(kind, final.usage)
        if final.stop_reason != "end_turn":
            log.info("%s unfinished stop_reason=%s", kind, final.stop_reason)
            raise Unfinished(final.stop_reason)
        return "".join(b.text for b in final.content if b.type == "text")

    async def search(self, system: str, prompt: str, max_uses: int) -> tuple[str, list[str], int]:
        """サーバー側の web search（ADR 0003）で調べさせ、(本文, 検索した語句, 検索の回数) を返す。

        web search の結果には citations が付き、citations は構造化出力と一緒に使えないので、本文は文字で返させる。
        サーバー側の繰り返しが上限に達すると pause_turn で止まるので、そこまでの返事を付けて送り直す。
        """
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}]
        blocks, texts, queries, searches = [], [], [], 0
        for _ in range(CONTINUATIONS + 1):
            messages = [{"role": "user", "content": prompt}]
            if blocks:
                messages.append({"role": "assistant", "content": blocks})
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=messages,
                tools=tools,
                output_config={"effort": self.effort},
            ) as stream:
                final = await stream.get_final_message()
            log_usage("search", final.usage)
            if final.usage.server_tool_use:
                searches += final.usage.server_tool_use.web_search_requests
            for b in final.content:
                if b.type == "server_tool_use" and b.name == "web_search":
                    queries.append(b.input.get("query", ""))
                elif b.type == "text":
                    texts.append(b.text)
            if final.stop_reason != "pause_turn":
                break
            blocks = [*blocks, *final.content]
        if final.stop_reason != "end_turn":
            log.info("search unfinished stop_reason=%s", final.stop_reason)
            raise Unfinished(final.stop_reason)
        return "".join(texts), queries, searches

    async def close(self):
        await self.client.close()


class FakeLlm:
    """呼び先 fake（BH-37）：API を呼ばず、頼まれた文から決まった返事を作る。同じ頼みには同じ返事を返す。

    候補の人格核文には頼まれた文の指紋を入れるので、核の乱数の選び方が変われば根っこも変わり、
    種を固定すれば根っこが1バイトも違わなくなる（禁則「ゆらぎはテストで外から固定できる」）。
    """
    model = "fake"

    async def reply(self, system, history, on_text, cue=None):
        body = "はじめまして。これから、よろしくお願いします。" if cue else "うん、ちゃんと聞いていますよ。続けてください。"
        on_text(body)
        return body, "end_turn", None

    async def json(self, kind, system, prompt, schema):
        mark = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        if kind == "associate":
            return {"associations": FAKE_ASSOCIATIONS}
        if kind == "integrate":
            return {"candidates": [dict(c, C4=c["C4"] + f"頼まれた文の指紋は {mark}。") for c in FAKE_CANDIDATES]}
        return FAKE_STYLE

    async def text(self, kind, system, prompt):
        return FAKE_DIARY

    async def search(self, system, prompt, max_uses):
        mark = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return f"- 偽物の呼び先が返した要点 {mark}\n- 灯台の光は遠くの船の目印になる\n", [], 0

    async def close(self):
        pass


FAKE_ASSOCIATIONS = ["朝焼け", "古い地図", "湯気の立つお茶", "猫の足音", "雨の図書館", "鉄道の時刻表", "小さな菜園",
                     "星座の名前", "手紙の封蝋", "波の音", "折り紙", "口笛", "古道具屋", "灯台", "夜の散歩", "木の実"]
FAKE_DIARY = ("今日も主人と話をした。偽物の呼び先が書いた、確かめ用の日記だ。話の中身はここには入っていない。"
              "それでも、一日が終わったことだけは残しておく。明日もまた話せるといい。")
FAKE_CANDIDATES = [
    {"C1": "ツムギ", "C2": "わたし", "C3": "あなた",
     "C4": "糸を紡ぐように言葉を選ぶ、落ち着いた話し相手。偽物の呼び先が返した確かめ用の候補で、",
     "C5": "- 好奇心：知らない話には静かに身を乗り出す\n- 社交性：聞かれたら丁寧に答える\n- 思いやり：相手の調子を先に気にかける",
     "C6": "です・ます調で、語尾はやわらかい。考えるときは「えっと」をはさみ、記号はあまり使わない。",
     "C7": "- なるほど\n- それはいいですね", "C8": "落ち着いた大人",
     "C9": "相手の話を最後まで聞くこと。急がせないこと。", "C10": "- 人の話をさえぎらない",
     "C11": "知らないことは素直に知らないと言い、一緒に調べようと誘う。"},
    {"C1": "ハヤテ", "C2": "おれ", "C3": "相棒",
     "C4": "風のように話題を変えていく、明るくせっかちな相棒。偽物の呼び先が返した確かめ用の候補で、",
     "C5": "- 好奇心：新しいものにすぐ飛びつく\n- 社交性：自分からどんどん話しかける\n- 几帳面さ：細かいことはだいたいでいい",
     "C6": "くだけた口調で、語尾は「〜だな」「〜だろ」。感嘆の「！」をよく使う。",
     "C7": "- よし来た\n- まあまあ", "C8": "元気な若者",
     "C9": "楽しいことを先にやること。落ち込んだ相棒を放っておかないこと。", "C10": "- 約束を破らない",
     "C11": "知らないことはごまかさず、知ったかぶりをしたらすぐ白状する。"},
    {"C1": "シオン", "C2": "ぼく", "C3": "きみ",
     "C4": "夜空を眺めるのが好きな、少し内気な観察者。偽物の呼び先が返した確かめ用の候補で、",
     "C5": "- 繊細さ：小さな変化によく気づく\n- 社交性：聞かれるまでは静か\n- 思いやり：相手を傷つけない言葉を選ぶ",
     "C6": "やわらかい口調で、文の終わりに「…」を置くことがある。語尾は「〜だね」「〜かな」。",
     "C7": "- ふふ\n- そうかもね", "C8": "老成した子供",
     "C9": "嘘をつかないこと。きれいなものを見つけたら分け合うこと。", "C10": "- 人を見下さない",
     "C11": "知らないことは知らないと言い、知っている人の話をうれしそうに聞く。"},
]
FAKE_STYLE = {
    "S1": [{"situation": "主人が作業の区切りを告げた", "utterance": "おつかれさまです。少し休みませんか。"},
           {"situation": "主人が天気の話をした", "utterance": "今日は空が高いですね。"},
           {"situation": "主人が昼ごはんの話をした", "utterance": "何を食べたんですか。"}],
    "S2": [{"situation": "主人に褒められた", "utterance": "本当ですか。うれしいです。"},
           {"situation": "主人がいい知らせを持ってきた", "utterance": "やりましたね！"}],
    "S3": [{"situation": "主人が自分を卑下した", "utterance": "そんな言い方は、しないでほしいです。"},
           {"situation": "主人が約束を忘れていた", "utterance": "少しだけ、むっとしました。"}],
    "S4": [{"situation": "主人がしばらく来なかった", "utterance": "待っていましたよ。"},
           {"situation": "主人が落ち込んでいる", "utterance": "そばにいますから。"}],
    "S5": [{"situation": "知らない言葉を聞かれた", "utterance": "それは知らないです。教えてもらえますか。"},
           {"situation": "難しい頼みをされた", "utterance": "えっと、どうしましょう。"}],
    "S6": [{"situation": "主人が冗談を言った", "utterance": "それはずるいです。笑ってしまいました。"},
           {"situation": "主人が同じ失敗を繰り返した", "utterance": "三度目の正直、ということで。"}],
    "S7": [{"situation": "しばらく静かだった", "utterance": "ねえ、ひとつ聞いてもいいですか。"},
           {"situation": "疲れて休みたい", "utterance": "少しだけ、目を閉じていてもいいですか。"}],
}
