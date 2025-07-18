#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 영문 텍스트를 Gemma-3 번역으로 치환하여 한글 PDF로 저장.
    ▸ 2025-07-04 6차 패치 + 소폭 리팩터
        • LOCAL_DICT 소문자화 → 케이스 불문 매핑
        • validate_translation에 '원문 동일' 체크
        • re.sub 통합
        • 숫자+단위(in, mm 등) 변환 차단
"""

from __future__ import annotations

import re
import logging
import textwrap
from functools import lru_cache

import fitz                           # PyMuPDF
from transformers import AutoTokenizer
from Gemma_trans import en2ko_gemma   # 사용자 정의 Gemma 래퍼

# ───────────────────────────── 전역 설정 ──────────────────────────────
TRANSLATE_LABEL = True
SHOW_RAW  = True
SHOW_DIFF = True

LOCAL_DICT_RAW = {
    "Color": "색상", "Black": "검정", "Material Type": "재질",
    "Dimensions": "치수", "Dimension": "치수",
    "Height": "높이",  "Width": "폭",
    "Finish": "마감",  "Steel": "강철",
    "Powder coated": "분체 도장",
    "Australia": "호주", "New Zealand": "뉴질랜드",
    "Patching": "패칭", "Splicing": "스플라이싱",
    "Fully loaded": "완전 장착형",
    "Cable Exit Direction": "케이블 출구 방향",
    "in": "인치",
}
LOCAL_DICT_RAW.update({
    "China": "중국",
    "India": "인도",
    "Asia": "아시아",                      
})
# → 모두 소문자 key 로 변환
LOCAL_DICT = {k.lower(): v for k, v in LOCAL_DICT_RAW.items()}

SUPPORT_WRAP = hasattr(fitz, "TEXT_WRAP")

# ───────────────────────────── 정규식 ─────────────────────────────────
STAR_ONLY  = re.compile(r"^[\*\u2022●▪· ]+$")
ONLY_NUM   = re.compile(r"^[0-9./\-\s]+$")
ONLY_CODE  = re.compile(r"^[A-Z0-9_\-/]{2,}$")
MD_STAR    = re.compile(r"^[\*\-\u2022●▪·]\s+")
STRIP_BOLD = re.compile(r"^\*+\s*|\s*\*+$")
PIPE_SPLIT = re.compile(r"\s*\|\s*")
SINGLE_HAN = re.compile(r"^[가-힣]$")
SLASH_SPLIT_RGX = re.compile(r"\s*/\s*")
NUM_ONLY_RGX    = re.compile(r"^[0-9./]+$")
NUM_UNIT_RGX    = re.compile(r"^[0-9.]+\s*(mm|in|cm)$", re.I)

# ───────────────────────────── 토크나이저 ─────────────────────────────
@lru_cache(maxsize=1)
def get_tokenizer():
    return AutoTokenizer.from_pretrained("google/gemma-3-12b-it")

# ───────────────────────────── 유틸 함수 ──────────────────────────────
def need_trans(txt: str) -> bool:
    txt = txt.strip()
    if not txt or STAR_ONLY.match(txt):
        return False
    if not re.search(r"[A-Za-z]", txt):
        return False
    if ONLY_NUM.match(txt) or ONLY_CODE.match(txt):
        return False
    return True


def safe_gemma(txt: str) -> str:
    """Gemma 호출 + 후처리 + fallback."""
    try:
        ko = en2ko_gemma(txt).strip()
    except Exception as e:
        logging.warning("Gemma 실패(%s) → fallback", e)
        return LOCAL_DICT.get(txt.strip().lower(), txt)

    # 노이즈 토큰·마크다운 제거
    ko = STRIP_BOLD.sub("", ko).strip()
    ko = re.sub(r"\s*(<end_of_turn>|#{2,}|\*\*)\s*", " ", ko)
    ko = re.sub(r"\b[Aa]ustralia\s+is\b", "호주", ko)
    ko = " ".join(ko.split())

    # 숫자+단위는 원문 보존
    if NUM_UNIT_RGX.match(txt.strip()):
        ko = txt

    if ko and ko.lower() != txt.lower():
        return ko
    return LOCAL_DICT.get(txt.strip().lower(), txt)


def validate_translation(en: str, ko: str) -> bool:
    if not ko or SINGLE_HAN.match(ko):
        return False
    if en.strip().lower() == ko.strip().lower():  # 번역이 안 됐으면 실패
        return False
    if len(en.strip()) >= 5 and len(ko.strip()) <= 2:
        return False
    return True


def split_by_slash(text: str) -> list[str]:
    if '/' not in text:
        return [text]
    parts = SLASH_SPLIT_RGX.split(text)
    if len(parts) == 2 and all(re.search(r"[A-Za-z]", p) for p in parts):
        return parts
    if len(parts) >= 3 and not NUM_ONLY_RGX.match(text):
        return parts
    return [text]


def translate_segment(text: str) -> str:
    """콤마·슬래시 단위 분할 → 개별 번역 → 재조립"""
    comma_parts = [p.strip() for p in text.split(',')] if ',' in text else [text]
    out_parts = []
    for part in comma_parts:
        tr_slash = []
        for sp in split_by_slash(part):
            if need_trans(sp):
                ko = safe_gemma(sp)
                if not validate_translation(sp, ko):
                    ko = LOCAL_DICT.get(sp.strip().lower(), sp)
                tr_slash.append(ko)
            else:
                tr_slash.append(sp)
        out_parts.append(' / '.join(tr_slash))
    return ', '.join(out_parts)

# ───────────────────────────── 메인 함수 ───────────────────────────────
def translate_pdf(
    input_pdf: str = "test_m1.pdf",
    output_pdf: str = "Gemma_34.pdf",
    *,
    fontfile: str = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    fontname: str = "NotoSansCJKKRBold",
    min_font: float = 5.0,
    scale: float = 1.2,
    padding: float = 1.5,
):
    logging.basicConfig(level=logging.INFO)

    with fitz.open(input_pdf) as doc:
        for page in doc:
            # ─── 원본 출력 ───
            if SHOW_RAW:
                print(f"\n=== Page {page.number + 1} RAW ===")
                print(page.get_text("text", flags=1))
                print("=== end raw ===")

            spans, orig, flags = [], [], []

            # ① 라인 병합 ------------------------------------------------------
            for blk in sorted(page.get_text("dict", flags=1)["blocks"],
                              key=lambda b: b["bbox"][1]):
                if blk["type"]:
                    continue
                for line in blk["lines"]:
                    line_rect = fitz.Rect(line["bbox"])
                    line_txt  = "".join(sp["text"] for sp in line["spans"]).strip()
                    line_txt  = MD_STAR.sub("", line_txt)
                    if not line_txt:
                        continue
                    size = max(sp["size"] for sp in line["spans"])

                    parts = PIPE_SPLIT.split(line_txt)
                    if 2 <= len(parts) <= 4:
                        col_w = (line_rect.x1 - line_rect.x0) / len(parts)
                        for idx, p in enumerate(parts):
                            rect = fitz.Rect(
                                line_rect.x0 + idx * col_w,
                                line_rect.y0,
                                line_rect.x0 + (idx + 1) * col_w,
                                line_rect.y1,
                            )
                            spans.append((rect, size, p))
                            orig.append(p)
                            flag = (idx != 0 or TRANSLATE_LABEL) and need_trans(p)
                            flags.append(flag)
                    else:
                        spans.append((line_rect, size, line_txt))
                        orig.append(line_txt)
                        flags.append(need_trans(line_txt))

            # ② 항목별 번역 ----------------------------------------------------
            final = [
                txt if not f else translate_segment(txt)
                for txt, f in zip(orig, flags)
            ]

            # diff 출력
            if SHOW_DIFF and any(e.strip() != k.strip() for e, k in zip(orig, final)):
                print(f"\n=== Page {page.number + 1} diff ===")
                for e, k in zip(orig, final):
                    if e.strip() != k.strip():
                        print(f"ENG: {e}\nKOR: {k}\n")
                print("=== end diff ===")
                

            # ③ 원본 삭제 & 새 텍스트 삽입 -----------------------------------
            for (rect, _, _), _ in zip(spans, final):
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            for (rect, size, _), txt in zip(spans, final):
                txt_wrapped = txt if SUPPORT_WRAP else "\n".join(textwrap.wrap(txt, 80))
                fs, rc = max(size * scale, min_font), -1
                kw = dict(fontfile=fontfile, fontname=fontname,
                          color=(0, 0, 0), align=0)
                if SUPPORT_WRAP:
                    kw["wrap"] = fitz.TEXT_WRAP
                while fs >= min_font:
                    kw["fontsize"] = fs
                    rc = page.insert_textbox(rect, txt_wrapped, **kw)
                    if rc >= 0:
                        break
                    fs -= 0.5
                if rc < 0:
                    big = fitz.Rect(rect.x0 - padding, rect.y0 - padding,
                                    page.rect.x1 - padding, rect.y1 + fs * 3 + padding)
                    if page.insert_textbox(big, txt_wrapped, **kw) < 0:
                        logging.warning("텍스트 오버플로: %.60s...", txt_wrapped)

            page.clean_contents()

        doc.save(output_pdf, garbage=4, deflate=True, clean=True)
    print("✓ 번역 완료 →", output_pdf)

translate_pdf()


# PYTHONPATH=$(pwd)/rag:$(pwd)/rag/store/faiss:$(pwd)/rag/answer/exaone_3_5 python fitz_Gemma_test.py