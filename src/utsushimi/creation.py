"""キャラ作り：5段で人格の根っこを生む（design.md §4.3・docs/concept.md §8.8〜§8.9。保護指定3）。核のスレッドだけが使う。

連想と調べる語を選ぶのは核の乱数で、乱数は外から受け取る（本番は OS の乱数、確かめでは種を固定した物。禁則）。
種はどこにも書かない。LLM の口は呼び先で替えられる（BH-37）。
"""
from datetime import datetime

from .persona import CORE, REQUIRED, STYLE, render

METHODS = {"omakase": "おまかせ", "image": "既存イメージ"}

SYSTEM = """あなたは、主人のデスクトップに常駐する1対1の相棒キャラを、主人と一緒に生み出す手伝いをしています。
相棒は文字だけで主人と話します。見た目が無いので、名前・一人称・呼び方・口調が、その子がその子である印になります。"""

ASSOCIATE = {
    "omakase": "主人が出したキーワード：{text}\n\n"
               "このキーワードから、生まれてくる相棒の性格・好み・癖・暮らしぶり・興味の向きにつながる連想を{offer}個挙げてください。",
    "image": "主人が書いた、ほしい相棒の姿：\n{text}\n\n"
             "この記述から、相棒の性格・好み・癖・暮らしぶり・興味の向きをふくらませる連想を{offer}個挙げてください。",
}
ASSOCIATE_RULES = """
- 1つの連想は2〜15文字ほどの短い語句にする。
- 似た連想を並べず、向きの違うものを混ぜる。ありきたりなものだけでなく、少し意外なものも入れる。"""

SEARCH = """相棒キャラを作る材料として、次の語を web search で調べてください：{words}
検索は各語について1回だけにしてください。

調べた結果から、キャラの好みや知識や話の種になりそうな具体的な事柄（固有名詞・数・出来事・豆知識など）を拾ってください。
最後に、拾った事柄を1行に1つ、行頭を「- 」にして3〜6行で書いてください。前置きやまとめは書かないでください。"""

INTEGRATE = """主人の入力（{method}）：
{text}

核の乱数で選んだ連想：{associations}

調べて拾った事柄：
{points}

これらを材料に、相棒の人格の根っこを{count}体分作ってください。{distinct}
各項目の中身と量：
- C1 名前：1〜20文字。呼びかけに使う名前だけを書く
- C2 一人称：1〜5文字
- C3 二人称：主人の呼び方。1〜20文字
- C4 人格核文：この子が何者かを1〜2文で。50〜150文字
- C5 性格軸：好奇心・社交性・繊細さ・几帳面さ・思いやりのうち3〜5軸を、1行に1軸「- 軸：説明」で（説明は20〜50文字）
- C6 口調パターン：語尾、丁寧かくだけているか、つなぎ言葉、記号（…、！、〜）の使い方。50〜200文字
- C7 口癖：2〜5個を1行に1つ「- 」で
- C8 年齢感：数でなく印象で。10〜30文字
- C9 価値観：判断の軸。50〜150文字
- C10 禁忌：絶対にしないことを1〜3個、1行に1つ「- 」で
- C11 知識の自己認識：知らないことにどう反応するか。30〜80文字

守ること：
- 調べて拾った事柄のうち少なくとも1つを、その語のまま C4・C5・C9・C11 のどれかの文に入れる（この子の好みや知識として）。
- 連想は全部使わなくてよい。合うものを選ぶ。
- 主人の入力に書かれたことは消さずに使う。{keep}
- 気持ちや動作を括弧書きのト書きで書かない。"""
DISTINCT = "{count}体は、名前・一人称・口調・性格の向きが互いにはっきり違う、別の人物にしてください。"
KEEP = "主人が書いた名前・一人称・呼び方・性格・口調などは、言い換えずにそのまま使い、書かれていない所だけを補う。"

STYLE_PROMPT = """次の人格の根っこを持つ相棒の、口調の見本を作ってください。

{core}
種別と数：
- S1 日常会話：3〜5例
- S2 感情表現（喜）：2〜3例（小さな喜びと大きな喜びの両方）
- S3 感情表現（怒／不快）：2〜3例
- S4 感情表現（悲／寂）：2〜3例
- S5 困惑／不知：2〜3例
- S6 ユーモア：2〜3例（C4 に合う向きのユーモアだけ）
- S7 沈黙破り：2〜3例（しばらく黙っていた後に自分から話しかける一言。疲れて休みたいときの調子を1つ含める）
合計17〜25例。

各例は「状況」と「発話」の組にする。状況は主人がしたことや場面を短く書き、発話はこの子が主人に向けて言う言葉そのものにする。
発話の中に括弧書きのト書きを入れない。C10 の禁忌に触れる例は入れない。"""


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string"}
ASSOCIATE_SCHEMA = _object({"associations": {"type": "array", "items": TEXT}})
CANDIDATES_SCHEMA = _object({"candidates": {"type": "array", "items": _object({key: TEXT for key, _ in CORE})}})
EXAMPLE = _object({"situation": TEXT, "utterance": TEXT})
STYLE_SCHEMA = _object({key: {"type": "array", "items": EXAMPLE} for key, _ in STYLE})


class Shortfall(Exception):
    """LLM の返事が、頼んだ数や項目に足りなかった。"""


class Draft:
    """作りかけの人格。確定するまで核の中だけにあり、ファイルには書かない。"""

    def __init__(self, method: str, text: str):
        self.method, self.text = method, text
        self.reset()

    def reset(self):
        self.associations, self.words, self.queries, self.points = [], [], [], []
        self.searches = 0
        self.candidates = []  # [{"C1": ..., ..., "C11": ...}]
        self.styles = {}      # 候補の番号 → {"S1": [{"situation", "utterance"}], ...}


async def associate(llm, rng, draft: Draft, count: int) -> int:
    """段1・2：入力を解釈して連想を多めに出させ、核の乱数で count 個を選ぶ。出させた数を返す。"""
    offer = count * 2 + 2
    prompt = ASSOCIATE[draft.method].format(text=draft.text, offer=offer) + ASSOCIATE_RULES
    offered = [a.strip() for a in (await llm.json("associate", SYSTEM, prompt, ASSOCIATE_SCHEMA))["associations"]]
    offered = list(dict.fromkeys(a for a in offered if a))
    if len(offered) < count:
        raise Shortfall(f"associations {len(offered)} < {count}")
    draft.associations = rng.sample(offered, count)
    return len(offered)


def choose_words(rng, draft: Draft):
    """段3の前半：選んだ連想から、核の乱数で調べる語を1〜2語選ぶ。"""
    draft.words = rng.sample(draft.associations, min(rng.randint(1, 2), len(draft.associations)))


async def research(llm, draft: Draft):
    """段3の後半：サーバー側の web search で調べ、要点を拾う（BH-11）。"""
    text, draft.queries, draft.searches = await llm.search(
        SYSTEM, SEARCH.format(words="、".join(draft.words)), max_uses=2 * len(draft.words))
    draft.points = [line[2:].strip() for line in text.splitlines() if line.startswith("- ") and line[2:].strip()]
    if not draft.points:
        raise Shortfall("no points")


async def integrate(llm, draft: Draft):
    """段4：入力・連想・要点から C1〜C11 を作る。おまかせは3体、既存イメージは1体（BH-42）。"""
    count = 3 if draft.method == "omakase" else 1
    prompt = INTEGRATE.format(
        method=METHODS[draft.method], text=draft.text, associations="、".join(draft.associations),
        points="\n".join(f"- {p}" for p in draft.points), count=count,
        distinct=DISTINCT.format(count=count) if count > 1 else "", keep=KEEP if draft.method == "image" else "")
    candidates = (await llm.json("integrate", SYSTEM, prompt, CANDIDATES_SCHEMA))["candidates"][:count]
    if len(candidates) < count or any(not c[key].strip() for c in candidates for key in REQUIRED["core.md"]):
        raise Shortfall("candidates")
    draft.candidates = [{key: c[key].strip() for key, _ in CORE} for c in candidates]


async def style(llm, draft: Draft, index: int):
    """段5：選ばれた候補の C1〜C11 から S1〜S7 を作る。"""
    samples = await llm.json("style", SYSTEM, STYLE_PROMPT.format(core=core_md(draft, index)), STYLE_SCHEMA)
    if any(not samples[key] for key, _ in STYLE):
        raise Shortfall("style")
    draft.styles[index] = samples


def core_md(draft: Draft, index: int) -> str:
    return render(CORE, draft.candidates[index])


def style_md(draft: Draft, index: int) -> str:
    return render(STYLE, {key: "\n".join(f"- （{e['situation'].strip()}）{e['utterance'].strip()}" for e in examples)
                          for key, examples in draft.styles[index].items()})


def origin_md(draft: Draft, model: str) -> str:
    """生まれた経緯（BH-10）。主人が振り返るための記録で、再現のためのレシピではないので、乱数の種は書かない。"""
    count = len(draft.candidates)
    method = METHODS[draft.method] + (f"（候補{count}体から主人が選んだ）" if count > 1 else "")
    words = "\n".join(f"- {w}" for w in draft.words)
    if draft.queries:
        words += "\n\n検索した語句：" + "、".join(draft.queries)
    return "\n".join([
        f"## 日時\n{datetime.now():%Y-%m-%d %H:%M}\n",
        f"## モデル\n{model}\n",
        f"## 方式\n{method}\n",
        f"## 主人の入力\n{draft.text}\n",
        "## 連想\n" + "\n".join(f"- {a}" for a in draft.associations) + "\n",
        f"## 調べた語\n{words}\n",
        "## 要点\n" + "\n".join(f"- {p}" for p in draft.points) + "\n",
    ])
