"""抓取新闻详情 + 配图，富化 narration.json

作为 parse_news.py 与 gen_tts.py 之间的环节：
  1. 解析每条新闻的 aihot 链接，取出条目 id
  2. 抓取 aihot 条目页（纯 HTTP，无需 JS）：
       - og:description  -> 中文摘要
       - json-ld isBasedOn -> 原始文章 URL
       - ⚠️ og:image 是 AI HOT 品牌文字卡片，与新闻主题无关，一律弃用
  3. 抓取原始文章，抽取真实主题配图（og:image + 正文大图）：
       - 兼容懒加载属性 data-orig/data-original/data-src/data-lazy-src/srcset
       - 过滤 logo/图标/占位图/超宽 banner（PIL 校验尺寸与长宽比）
       - ⚠️ 用户明令「不允许文字图片」：品牌卡 / 渐变底大字卡 / 文档截图一律丢弃
         （looks_like_text_image：彩色度 + 主色占比 + 颜色唯一度三判据，见函数注释）
  3.5 原文没有可用实拍图时，走图库兜底取真实摄影图：Pexels → Pixabay（多源 × 多检索词）
       - 候选需通过 accepts_as_photo：非文字图 + 本片内未重复（避免多张新闻同图）
       - 两个图库 Key 都缺失时必然退化为关键词文字卡，因此会对该条打 CRITICAL 日志
  4. 把 bullets / images / image_sizes / image_source / summary / original_url 写回 scene.visual，
     并用「第 N 条 → 标题 → 要点 → 来源」的顺序重建 scene.clauses，
     使 gen_tts 的配音与字幕都覆盖详细内容。

所有抓取均带超时与失败兜底：任一环节出错只跳过该环节，
绝不中断整条流水线。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time

import requests
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (IMAGES_DIR, NARRATION, PEXELS_API_KEY, PIXABAY_API_KEY,  # noqa: E402
                    PIXABAY_API_URL, ensure_dirs)
from parse_news import clean_for_tts, ensure_period, merge_clauses  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 25
MIN_IMG = 240          # 配图最小边长（过滤图标/头像）
MAX_IMAGES = 1         # 每条新闻保留的配图数：渲染端只用 images[0]，多抓是纯浪费
MAX_BULLETS = 3        # 每条新闻最多要点数
BULLET_MAX = 38        # 单条要点最大字数

ID_RE = re.compile(r"/items/([A-Za-z0-9_-]+)")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
SKIP_IMG = re.compile(
    r"(favicon|logo|icon|avatar|sprite|emoji|badge|banner_ad|pixel|1x1"
    r"|/t\.png|blank|placeholder|loading|spacer)",
    re.I,
)
# 聚合站自带的品牌摘要卡（文字图片）域名：一律不作为配图
TEXT_CARD_DOMAINS = ("aihot.virxact.com",)
# img 标签上依次尝试的图片地址属性（覆盖常见懒加载方案）
IMG_ATTRS = ("src", "data-orig", "data-original", "data-src",
             "data-lazy-src", "data-actualsrc")

# ---------------------------------------------------------------- 实拍图库兜底（多源）
# 用户要求「彻底摆脱文字图片」：原文抓不到真实照片时，用图库检索真实摄影图。
# 源按序尝试：Pexels → Pixabay；两者都不可用时该条会退化为关键词文字卡（打 CRITICAL 日志）
PEXELS_SEARCH = "https://api.pexels.com/v1/search"

# 标题 → 图库检索词映射（命中前 2 条，再追加通用兜底词）。
# 两条硬约束（2026-09-17 用户第三次反馈「全是打字图片」后定版）：
#   1) 不拿标题里的品牌词检索——图库没有品牌图，只会返回无关结果；
#   2) 检索词必须指向「人物/实物/场景」等摄影题材，禁止指向「屏幕上的文字」，
#      否则会取回满屏代码/图表/幻灯片的图，观感与文字卡无异。
STOCK_HINTS = (
    (r"编码|编程|代码|IDE|编辑器|开发容器|VS ?Code|Copilot|Codex|Cursor|harness|重构|调试",
     "developer coding laptop"),
    (r"智能体|Agent|工作流|自动化|协同|编排", "robot automation technology"),
    (r"检索|RAG|知识库|向量|数据库|存储|缓存|索引|扇出", "server room data center"),
    (r"芯片|加速器|GPU|算力|吞吐|显存|内核|硬件|部署|推理系统",
     "computer processor circuit board"),
    (r"安全|披露|事故|风险|合规|漏洞|越狱|对齐|错位", "cyber security data protection"),
    (r"报告|论文|研究|基准|评测|调研|数据|统计", "research library books desk"),
    (r"开源|仓库|GitHub|版本|框架|发布|规范", "software development team"),
    (r"融资|收入|定价|成本|商业|采购|账单|亿美元|市场", "business meeting office"),
    (r"视频|图像|多模态|语音|视觉|扩散|生成", "digital creative technology"),
    (r"模型|大模型|训练|微调|推理|token|上下文|参数", "artificial intelligence technology"),
)
DEFAULT_STOCK_QUERIES = ("artificial intelligence technology", "technology")
STOCK_PER_PAGE = 6      # 每个检索词取回的候选数


def stock_queries(title: str):
    """由标题生成图库检索词：命中业务域优先，末位追加通用兜底词。"""
    out = []
    for pat, q in STOCK_HINTS:
        if q not in out and re.search(pat, title or "", re.I):
            out.append(q)
        if len(out) >= 2:
            break
    for q in DEFAULT_STOCK_QUERIES:
        if q not in out:
            out.append(q)
    return out


def pexels_urls(query: str, sess) -> list:
    """Pexels 检索，按相关度返回候选图 URL；Key 缺失或失败返回空列表。"""
    if not PEXELS_API_KEY:
        return []
    try:
        r = sess.get(
            PEXELS_SEARCH,
            params={"query": query, "per_page": STOCK_PER_PAGE, "orientation": "landscape"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return []
        urls = []
        for p in r.json().get("photos", []):
            src = p.get("src") or {}
            u = src.get("large2x") or src.get("large")
            if u:
                urls.append(u)
        return urls
    except Exception:
        return []


def pixabay_urls(query: str, sess) -> list:
    """Pixabay 检索（复用 .env 已有的 PIXABAY_API_KEY，与 BGM 同一个 Key）。"""
    if not PIXABAY_API_KEY:
        return []
    try:
        r = sess.get(PIXABAY_API_URL, params={
            "key": PIXABAY_API_KEY, "q": query, "image_type": "photo",
            "orientation": "horizontal", "safesearch": "true",
            "per_page": STOCK_PER_PAGE, "lang": "en",
        }, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        urls = []
        for h in r.json().get("hits", []):
            u = h.get("largeImageURL") or h.get("webformatURL")
            if u:
                urls.append(u)
        return urls
    except Exception:
        return []


STOCK_SOURCES = (("pexels", pexels_urls), ("pixabay", pixabay_urls))


def _remove(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


def stock_fallback(item_id: str, title: str, sess, images: list, image_sizes: list) -> str:
    """图库兜底：多源 × 多检索词 × 多候选，返回命中的来源名（全部失败返回 ''）。

    候选按序尝试：文字图、本片已用过的图都会被跳过，因此同一条会一直试到
    拿到「可用且不与前文重复」的照片为止。
    """
    for src_name, fetch_urls in STOCK_SOURCES:
        for q in stock_queries(title):
            for url in fetch_urls(q, sess):
                fn = f"{item_id}_{src_name}"
                dest = os.path.join(IMAGES_DIR, fn + ".jpg")
                dims = download_image(url, dest)
                if not dims:
                    continue
                if not accepts_as_photo(dest):
                    _remove(dest)
                    continue
                images.append(f"images/{fn}.jpg")
                image_sizes.append(list(dims))
                print(f"    [{src_name}] 「{q}」配图 {dims[0]}x{dims[1]}")
                return src_name
    return ""


# ---------------------------------------------------------------- 文字图识别
# 用户明令「不允许文字图片」。三条判据命中任一即判为文字图；
# 宁可误杀——误杀只是换一张图库实拍图，漏判则会把文字卡发到三平台。
# 本片已采用的配图指纹：图库对相近检索词常返回同一张图，
# 不去重会出现「三条新闻同一张照片」（2026-09-17 实测 4 条兜底 3 条同图）。
_USED_IMG_HASHES = set()


def _img_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def accepts_as_photo(path: str) -> bool:
    """配图准入：非文字图 + 本片内未用过。命中则登记指纹并返回 True。"""
    if looks_like_text_image(path):
        return False
    try:
        digest = _img_md5(path)
    except OSError:
        return False
    if digest in _USED_IMG_HASHES:
        return False
    _USED_IMG_HASHES.add(digest)
    return True


COLORFUL_TEXT = 20.0    # 彩色度低于此值 → 单色/近单色底
TOP1_TEXT = 0.62        # 粗量化主色占比超过此值 → 颜色高度集中（0.62 是实测取舍：
                        # 0.55 会误杀「手机 + 大面积纯色背景」这类真实照片）
TOP3_TEXT = 0.88        # 前 3 色占比超过此值 → 近似纯色卡
UNIQ5_TEXT = 0.038      # 5bit 量化后 96×96 的颜色唯一度低于此值 → 文字卡/无内容渐变图


def _colorfulness(px) -> float:
    """Hasler–Süsstrunk 彩色度（px 为 (N,3) 数组）：文字卡片通常 < 20，实拍照片通常 > 30。"""
    a = np.asarray(px, dtype=np.float32).reshape(-1, 3)
    rg = a[:, 0] - a[:, 1]
    yb = 0.5 * (a[:, 0] + a[:, 1]) - a[:, 2]
    return float((rg.std() ** 2 + yb.std() ** 2) ** 0.5
                 + 0.3 * (rg.mean() ** 2 + yb.mean() ** 2) ** 0.5)


def looks_like_text_image(path: str) -> bool:
    """判断图片是否为「文字卡片/海报/文档截图」而非实拍照片。

    判据（任一命中即判文字图）：
    1. 颜色唯一度过低（5bit 量化后 96×96 内仍只有极少数颜色）。
       这是覆盖「柔和渐变底 + 大字」的关键判据——例如 OpenAI 官网那张
       粉紫渐变标题卡，彩色度 41.75、主色占比 0.31/0.64，旧判据全部失效，
       但 5bit 颜色唯一度只有 0.024（实拍照片普遍 > 0.04）。
    2. 彩色度过低（大面积单色底）。
    3. 粗量化主色占比过高（近似纯色卡）。

    阈值来自 work/imgsamples 的 17 张标注样本（8 张文字卡/无内容渐变图 + 9 张实拍图，
    样本由本次事故中真实出现过的 URL 采集而来）：本规则 17/17 全部正确。
    """
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
    except Exception:
        return True     # 读不了就当文字图，交给图库兜底
    try:
        # 判据 1：颜色唯一度
        small = np.asarray(img.resize((96, 96)))
        q = small >> 3
        key = (q[:, :, 0].astype(np.int32) << 10) | \
              (q[:, :, 1].astype(np.int32) << 5) | q[:, :, 2]
        if len(np.unique(key)) / key.size < UNIQ5_TEXT:
            return True
        # 判据 2/3：彩色度 + 主色占比（沿用原口径，缩小到 ~100px 计算）
        scale = 100 / max(w, h)
        px = list(img.resize((max(8, int(w * scale)), max(8, int(h * scale)))).getdata())
        if not px:
            return True
        if _colorfulness(px) < COLORFUL_TEXT:
            return True
        qz = (np.asarray(px, dtype=np.int32) // 32)
        key2 = qz[:, 0] * 1024 + qz[:, 1] * 32 + qz[:, 2]
        counts = np.sort(np.bincount(key2))[::-1]
        total = len(px)
        top1 = counts[0] / total
        top3 = counts[:3].sum() / total
        return top1 > TOP1_TEXT or top3 > TOP3_TEXT
    except Exception:
        return True


# ---------------------------------------------------------------- HTTP
def download_image(url: str, dest: str):
    """下载并校验为有效图片，成功返回 (宽, 高)，失败返回 None。

    校验规则：HTTP 200、非 SVG、体积 ≥4KB、最小边 ≥MIN_IMG、
    长宽比在 0.4~2.8 之间（过滤超宽 banner / 细长图）。
    返回尺寸供渲染端做「完整展示 / 长图竖向滚动」决策。
    """
    try:
        if any(d in url for d in TEXT_CARD_DOMAINS):
            return None
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        if r.status_code != 200:
            return None
        ctype = r.headers.get("Content-Type", "")
        if "image/svg" in ctype:
            return None
        data = r.content
        if len(data) < 4000:
            return None
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if w < MIN_IMG or h < MIN_IMG:
            return None
        if not (0.4 <= w / h <= 2.8):
            return None
        img.convert("RGB").save(dest)
        return (w, h)
    except Exception:
        return None


# ---------------------------------------------------------------- aihot 页解析
def parse_aihot(html: str):
    og_image = og_desc = original = summary_full = reason = None
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("meta"):
        prop = (tag.get("property") or tag.get("name") or "").lower()
        content = tag.get("content")
        if not content:
            continue
        if prop == "og:image":
            og_image = content
        elif prop in ("og:description", "description") and not og_desc:
            og_desc = content
    # json-ld 里的 isBasedOn 指向原始文章
    for script in soup.find_all("script", type="application/ld+json"):
        txt = script.string or ""
        m = re.search(r'"isBasedOn"\s*:\s*"(https?://[^"]+)"', txt)
        if m:
            original = m.group(1)
            break
    if not original:
        m = re.search(r'"isBasedOn"\s*:\s*"(https?://[^"]+)"', html)
        if m:
            original = m.group(1)
    # 完整中文摘要（aihot 生成的要点，比被截断的 og:description 完整）
    # 只从可见 <p> 抽取，避免 json-ld 噪声；摘要段以「提供。」结尾
    best = None
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t.endswith("提供。") and len(t) > 40:
            if best is None or len(t) > len(best):
                best = t
    summary_full = best
    # 精选理由（补充说明价值）
    m = re.search(r'reason-text">([^<]{8,})<', html)
    if m:
        reason = m.group(1)
    return og_image, og_desc, original, summary_full, reason


# ---------------------------------------------------------------- 原始文章解析
def extract_article_text(html: str):
    soup = BeautifulSoup(html, "lxml")
    for bad in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
        bad.decompose()
    # 优先正文容器
    root = soup.find("article") or soup.find("main") or soup.body or soup
    paras = []
    for p in root.find_all(["p", "li"]):
        t = p.get_text(" ", strip=True)
        if t:
            paras.append(t)
    return " ".join(paras)


def _pick_from_srcset(srcset: str):
    """从 srcset 中取分辨率最大的一张。"""
    best, best_w = None, -1
    for part in srcset.split(","):
        seg = part.strip().split()
        if not seg:
            continue
        url = seg[0]
        w = 0
        if len(seg) > 1 and seg[1].rstrip("w").isdigit():
            w = int(seg[1].rstrip("w"))
        if w >= best_w:
            best, best_w = url, w
    return best


def extract_images(html: str, base_url: str):
    """抽取原文真实配图候选（og:image 优先，其次正文 img，含懒加载属性）。"""
    soup = BeautifulSoup(html, "lxml")
    cands = []
    og = soup.find("meta", attrs={"property": "og:image"}) or \
        soup.find("meta", attrs={"name": "og:image"})
    if og and og.get("content"):
        cands.append(og["content"].strip())
    for img in soup.find_all("img"):
        # 依次尝试多个属性；某个属性命中占位图/黑名单时继续尝试下一个，
        # 而不是放弃整个 img 标签（ithome 等站 src 固定为 t.png 占位）
        srcs = []
        for attr in IMG_ATTRS:
            v = img.get(attr)
            if v and v.strip() and not v.startswith("data:"):
                srcs.append(v.strip())
        for ss in (img.get("srcset"), img.get("data-srcset")):
            if ss:
                pick = _pick_from_srcset(ss)
                if pick:
                    srcs.append(pick)
        src = next((s for s in srcs if not SKIP_IMG.search(s)), None)
        if not src:
            continue
        if not src.lower().endswith(IMG_EXT) and "?" not in src:
            # 允许带 query 的未知扩展（如 _.jpg?x=1 已含扩展）
            if not re.search(r"\.(jpg|jpeg|png|webp)", src, re.I):
                continue
        cands.append(src)
    out = []
    for c in cands:
        try:
            abs_url = c if c.startswith("http") else \
                requests.compat.urljoin(base_url, c)
        except Exception:
            continue
        if abs_url and abs_url not in out:
            out.append(abs_url)
    return out


def build_bullets(*texts):
    """从若干中文语料（完整摘要 / 精选理由 / 描述）中产出 ≤MAX_BULLETS 条要点。

    直接按句末标点切成「完整句子」作为要点（不切逗号），
    保留原文信息量；超过软上限的句子在逗号处截断。
    优先含数字或动作词的句子，不足时回退到任意句子。
    """
    sents = []
    for t in texts:
        if not t:
            continue
        t = clean_for_tts(t)
        if re.search(r'["{}]|contentUrl|http|@type|application/', t):
            continue
        for s in re.split(r"[。！？!?；;]", t):
            s = s.strip("，,、 ")
            if len(s) < 8:
                continue
            if re.search(r'["{}]|contentUrl|http', s):
                continue
            # 完整保留句子（画面/字幕会自动换行）；仅在极端超长时按逗号截断
            if len(s) > 90:
                parts = re.split(r"[，,、]", s)
                cur = ""
                for p in parts:
                    if len(cur) + len(p) > 80 and cur:
                        break
                    cur = (cur + "，" + p) if cur else p
                s = cur
            sents.append(s)

    bullets, seen = [], set()
    scored = []
    for s in sents:
        if s[:10] in seen:
            continue
        score = 0
        if re.search(r"\d", s):
            score += 3
        if re.search(r"(发布|推出|开源|支持|宣布|上线|突破|超越|提升|降价|免费|开放|集成|提供|可用|版本|模型|额度|基准|整理|对比)", s):
            score += 2
        if 12 <= len(s) <= 45:
            score += 1
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])

    for _, s in scored:
        key = s[:10]
        if key in seen:
            continue
        seen.add(key)
        bullets.append(ensure_period(s))
        if len(bullets) >= MAX_BULLETS:
            break
    if not bullets and sents:
        bullets.append(ensure_period(sents[0][:BULLET_MAX + 6]))
    return bullets[:MAX_BULLETS]


def _norm(s: str) -> str:
    return re.sub(r"[\s，,。、；;：:！!？?\"'（）()\\[\\]【】]", "", s or "")


MAX_BULLET_SPOKEN = 22   # 口播要点最大字数（浓缩模式，1 分钟内成片的关键）
LONG_TITLE = 32          # 标题超过该字数时不再加口播要点（避免超时）


def _spoken_bullet(b: str, title_norm: str) -> str:
    """把要点浓缩成口播版：截到 MAX_BULLET_SPOKEN 字、保证句尾句号、与标题去重。"""
    bn = _norm(b)
    if title_norm and (bn in title_norm or title_norm in bn):
        return ""
    b = b.strip()
    if len(b) > MAX_BULLET_SPOKEN:
        cut = b[:MAX_BULLET_SPOKEN + 6]
        # 在最后一个逗号/顿号处截断，避免半句话
        for sep in ("，", "、", "；", " "):
            p = cut.rfind(sep)
            if p >= MAX_BULLET_SPOKEN - 8:
                cut = cut[:p]
                break
        b = cut
    return ensure_period(b)


def assemble_item_clauses(v: dict, bullets: list):
    """重建新闻条目口播顺序（浓缩版）：标题 → 至多 1 条精简要点。

    用户要求成片尽量浓缩到 1 分钟以内：
    - 「第 N 条」「来源」不上口播（仍展示在画面卡片上）
    - 要点最多口播 1 条且截到 MAX_BULLET_SPOKEN 字
    - 标题本身超过 LONG_TITLE 字时不再加要点
    """
    clauses = merge_clauses([ensure_period(v["title"])]) if v.get("title") else []
    title_norm = _norm(v.get("title", ""))
    if len(_norm(v.get("title", ""))) <= LONG_TITLE:
        for b in bullets[:1]:
            sb = _spoken_bullet(b, title_norm)
            if sb:
                clauses.append(sb)
    return clauses


# ---------------------------------------------------------------- 主流程
def _link_id(link: str) -> str:
    """非 aihot 链接的稳定短 id（用于配图文件名）。"""
    return hashlib.md5(link.encode("utf-8")).hexdigest()[:10]


def _og_desc(html: str) -> str:
    """从任意页面取 og:description（原文直链时作摘要兜底）。"""
    try:
        soup = BeautifulSoup(html, "lxml")
        m = soup.find("meta", attrs={"property": "og:description"}) or \
            soup.find("meta", attrs={"name": "description"})
        if m and m.get("content"):
            return m["content"].strip()
    except Exception:
        pass
    return ""


def enrich_scene(scene: dict, sess: requests.Session):
    v = scene.get("visual", {})
    link = v.get("link", "")
    if not link:
        return False

    summary_full = reason = og_desc = ""
    mid = ID_RE.search(link)
    if mid:
        # aihot 条目页：取 isBasedOn 原文 + 中文摘要
        item_id = mid.group(1)
        print(f"  [{item_id}] 抓取详情…")
        html = fetch_html(link, sess=sess)
        if not html:
            return False
        _og_image, og_desc, original, summary_full, reason = parse_aihot(html)
    else:
        # 原文直链（每日 AI 新闻推送 md 里的「原文：https://...」）：
        # 直接把该 URL 当作原始文章抓图，摘要交给 og:description
        item_id = _link_id(link)
        original = link
        print(f"  [直链 {item_id}] 抓取配图… {link[:60]}")

    # --- 配图：只取原始文章的真实照片，文字卡片一律识别并丢弃 ---
    # 三层防线：
    #   1) 域名黑名单（aihot 品牌卡）
    #   2) URL 特征（SKIP_IMG：logo/icon/banner 等）
    #   3) 像素判据 looks_like_text_image（品牌卡/渐变大字卡/文档截图），误杀走图库兜底
    images = []
    image_sizes = []       # 与 images 平行，存 (w, h)，供渲染端动态高度/长图滚动决策
    n_rejected = 0         # 被判定为文字图而丢弃的候选数（用于诊断）
    if original:
        v["original_url"] = original
        ahtml = fetch_html(original, sess=sess)
        if ahtml:
            if not og_desc and not summary_full:
                og_desc = _og_desc(ahtml)
            for img_url in extract_images(ahtml, original):
                if len(images) >= MAX_IMAGES:
                    break
                if any(d in img_url for d in TEXT_CARD_DOMAINS):
                    continue
                fn = f"{item_id}_{len(images)+1}"
                dest = os.path.join(IMAGES_DIR, fn + ".jpg")
                dims = download_image(img_url, dest)
                if not dims:
                    continue
                if not accepts_as_photo(dest):
                    n_rejected += 1
                    print(f"    [filter] 丢弃文字图/重复图 {img_url[:56]}")
                    _remove(dest)
                    continue
                images.append(f"images/{fn}.jpg")
                image_sizes.append(list(dims))
                v["image_source"] = "original"

    # 原文没有可用实拍图（或全是文字卡）-> 图库检索真实摄影图
    if not images:
        if n_rejected:
            print(f"    [filter] 原文 {n_rejected} 张候选全部判为文字图，转图库兜底")
        src = stock_fallback(item_id, v.get("title", ""), sess, images, image_sizes)
        if src:
            v["image_source"] = src
        else:
            # 用户明令禁止文字图片：走到这里说明图库 Key 缺失/全部失败，画面会退化成关键词文字卡
            print("    [CRITICAL] 配图缺失：原文无可用实拍图，且图库兜底（Pexels/Pixabay）全部失败"
                  " → 本条画面将退化为关键词文字卡（用户已明令禁止）")

    # --- 要点：用 aihot 中文摘要 + 精选理由（已含详细事实） ---
    # og:description 常被截断，仅作兜底且只取句号前的完整部分
    if summary_full:
        bullet_src = [summary_full, reason]
    elif og_desc:
        cut = og_desc.rsplit("。", 1)[0] + "。" if "。" in og_desc else og_desc
        bullet_src = [cut, reason]
    else:
        bullet_src = [reason]
    new_bullets = build_bullets(*bullet_src)
    if og_desc:
        v["summary"] = clean_for_tts(og_desc)
    # md 自带要点（parse 阶段写入的「核心/细节/价值」）优先：
    # 那是中文且贴合推送口径，抓取到的英文 og:description 只作兜底，不覆盖
    if not v.get("bullets") and new_bullets:
        v["bullets"] = new_bullets
    bullets = v.get("bullets", [])
    v["images"] = images
    v["image_sizes"] = image_sizes

    if bullets or images:
        scene["clauses"] = assemble_item_clauses(v, bullets)
        print(f"    ✓ 要点 {len(bullets)} 条 / 配图 {len(images)} 张"
              + (f" / 来源 {original[:48]}" if original else ""))
        return True
    return False


def fetch_html(url: str, sess: requests.Session = None, tries: int = 2):
    sess = sess or requests
    for i in range(tries):
        try:
            r = sess.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and r.text:
                return r.text
        except Exception as e:
            if i == 0:
                print(f"    [warn] 抓取失败 {url[:60]}... {e}")
            time.sleep(1.2 * (i + 1))
    return None


def main():
    ap = argparse.ArgumentParser(description="抓取新闻详情与配图，富化 narration.json")
    ap.add_argument("--narration", default=NARRATION)
    ap.add_argument("--no-fetch", action="store_true", help="跳过抓取，仅保留现有 clauses")
    args = ap.parse_args()

    ensure_dirs()
    if not os.path.isfile(args.narration):
        print(f"FAIL: 找不到 {args.narration}，请先运行 parse_news.py")
        return 1

    narr = json.load(open(args.narration, encoding="utf-8"))
    scenes = narr.get("scenes", [])

    if args.no_fetch:
        print("SKIP 抓取（--no-fetch）")
        json.dump(narr, open(args.narration, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return 0

    sess = requests.Session()
    sess.headers.update(HEADERS)
    # 清空上一轮配图，避免旧的 AI HOT 文字卡片残留在成片里
    for old in os.listdir(IMAGES_DIR):
        try:
            os.remove(os.path.join(IMAGES_DIR, old))
        except OSError:
            pass
    _USED_IMG_HASHES.clear()   # 去重指纹只在本轮内生效
    n_enriched = 0
    stat = {"original": 0, "pexels": 0, "pixabay": 0, "": 0}
    for sc in scenes:
        if sc.get("visual", {}).get("type") == "news_item":
            if enrich_scene(sc, sess):
                n_enriched += 1
            src = sc.get("visual", {}).get("image_source", "")
            stat[src] = stat.get(src, 0) + 1
            time.sleep(0.4)  # 礼貌限速

    json.dump(narr, open(args.narration, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"DONE 富化 {n_enriched} 条新闻 -> {args.narration}")
    print(f"  配图来源：原文 {stat['original']} / Pexels {stat['pexels']} / "
          f"Pixabay {stat['pixabay']} / 缺失 {stat['']}")
    if stat[""]:
        print(f"  [CRITICAL] {stat['']} 条新闻无配图，画面将出现关键词文字卡（用户明令禁止）。"
              f"请检查 .env 的 PEXELS_API_KEY / PIXABAY_API_KEY 是否有效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
