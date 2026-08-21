"""One-off seed: ingredient_skin_score 데이터 (성분 59개, 피부타입 4종 x 각 성분).

점수 산정 근거 (evidence_level/source로 성분마다 구분해 표시):
  - "D" + source="AAD": AAD(미국피부과학회) 공식 페이지(aad.org/public/everyday-care/
    skin-care-basics/dry/pick-moisturizer)에서 피부타입별 보습제 성분으로 실제로
    이름을 명시한 8종(호호바씨오일·다이메티콘·글리세린·하이알루로닉애씨드·락틱애씨드·
    미네랄오일·페트롤라텀·시어버터) — 2026-08-21 직접 확인.
  - "D" + source="DermNet": DermNet(dermnetnz.org/topics/emollients-and-moisturisers)의
    humectant/occlusive/emollient 성분 분류 기준을 따른 항목 — 2026-08-21 직접 확인.
  - "E" + source="화장품 성분과학 컨센서스": 위 두 출처로 개별 검증하지는 않았지만,
    INCI 기능 분류·일반적인 화장품 원료학에서 널리 합의된 성분(펩타이드, 병풀 유도체,
    비타민C 유도체 등)에 대해 만든 예시 점수. 실제 서비스 전 문헌 재검토가 필요하다.

DB에 없는 성분(페트롤라텀 등)은 새로 추가한다 (레티날을 추가했던 것과 같은 방식).

Usage:
    python -m scripts.seed_ingredient_skin_scores [--db-url URL]
"""

import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models.ingredient import Ingredient
from app.models.ingredient_skin_score import IngredientSkinScore

_AAD = ("D", "AAD (aad.org - How to pick the right moisturizer, 2026-08-21 확인)")
_DERMNET = ("D", "DermNet (dermnetnz.org/topics/emollients-and-moisturisers, 2026-08-21 확인)")
_CONSENSUS = ("E", "화장품 성분과학 컨센서스 (개별 문헌 미검증, 재검토 필요)")
_KFIA = ("D", "대한화장품협회 (소비자를 위한 화장품 상식)")

# name_kr -> {"evidence": (level, source), "scores": {스킨타입: (score, function, caution)}}
# 스킨타입 순서: 지성, 복합성, 건성, 민감성. score 범위 -3~+3.
_SEED = {
    # --- AAD가 명시적으로 이름을 든 8종 ---
    "하이알루로닉애씨드": {
        "evidence": _AAD,
        "scores": {
            "지성": (1, "Humectant", None),
            "복합성": (1, "Humectant", None),
            "건성": (3, "Humectant", None),
            "민감성": (1, "Humectant", None),
        },
    },
    "소듐하이알루로네이트": {
        "evidence": _AAD,
        "scores": {
            "지성": (1, "Humectant", "하이알루로닉애씨드의 염 형태, 분자가 작아 흡수가 더 빠름"),
            "복합성": (1, "Humectant", None),
            "건성": (3, "Humectant", None),
            "민감성": (1, "Humectant", None),
        },
    },
    "글리세린": {
        "evidence": _AAD,
        "scores": {
            "지성": (1, "Humectant", None),
            "복합성": (2, "Humectant", None),
            "건성": (3, "Humectant", None),
            "민감성": (2, "Humectant", None),
        },
    },
    "미네랄오일": {
        "evidence": _AAD,
        "scores": {
            "지성": (-1, "Occlusive", "폐색 작용으로 지성 피부에서는 무겁게 느껴질 수 있음"),
            "복합성": (1, "Occlusive", None),
            "건성": (2, "Occlusive", None),
            "민감성": (1, "Occlusive", None),
        },
    },
    "페트롤라텀": {  # DB에 없으면 새로 추가
        "evidence": _AAD,
        "scores": {
            "지성": (-2, "Occlusive", "무거운 폐색 성분이라 지성/여드름 피부엔 부담"),
            "복합성": (0, "Occlusive", None),
            "건성": (3, "Occlusive", None),
            "민감성": (2, "Occlusive", "불활성 성분으로 손상된 장벽 보호용으로 자주 쓰임"),
        },
    },
    "다이메티콘": {
        "evidence": _AAD,
        "scores": {
            "지성": (1, "Occlusive", "실리콘 계열이라 오일 대비 가볍고 논코메도제닉으로 알려짐"),
            "복합성": (2, "Occlusive", None),
            "건성": (2, "Occlusive", None),
            "민감성": (2, "Occlusive", None),
        },
    },
    "락틱애씨드": {
        "evidence": _AAD,
        "scores": {
            "지성": (2, "각질관리/Humectant", None),
            "복합성": (2, "각질관리/Humectant", None),
            "건성": (0, "각질관리/Humectant", "AHA 중에서는 분자가 커서 순한 편이며 NMF 구성 성분이기도 함"),
            "민감성": (-1, "각질관리/Humectant", "산 성분이라 장벽 약화 시 자극 가능"),
        },
    },
    "호호바씨오일": {
        "evidence": _AAD,
        "scores": {
            "지성": (1, "Emollient", "피지와 구조가 유사해 무겁지 않고 논코메도제닉으로 알려짐"),
            "복합성": (2, "Emollient", None),
            "건성": (2, "Emollient", None),
            "민감성": (2, "Emollient", None),
        },
    },
    "시어버터": {
        "evidence": _AAD,
        "scores": {
            "지성": (-2, "Emollient/Occlusive", "고지방 성분이라 지성/여드름 피부엔 무거울 수 있음"),
            "복합성": (0, "Emollient/Occlusive", None),
            "건성": (3, "Emollient/Occlusive", None),
            "민감성": (2, "Emollient/Occlusive", "저자극으로 알려져 있으나 견과류 알레르기 주의"),
        },
    },
    # --- DermNet 분류(humectant/occlusive/emollient) 기준 ---
    "우레아": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (0, "Humectant", None),
            "복합성": (1, "Humectant", None),
            "건성": (3, "Humectant", "고농도(10%+)는 각질용해 목적으로도 쓰임"),
            "민감성": (-1, "Humectant", "고농도에서 따가움 등 자극 보고"),
        },
    },
    "베타인": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Humectant", None),
            "복합성": (2, "Humectant", None),
            "건성": (2, "Humectant", None),
            "민감성": (2, "Humectant", None),
        },
    },
    "판테놀": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Humectant/진정", None),
            "복합성": (2, "Humectant/진정", None),
            "건성": (3, "Humectant/진정", None),
            "민감성": (3, "Humectant/진정", None),
        },
    },
    "소듐피씨에이": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Humectant", "피부 자체 NMF 구성 성분"),
            "복합성": (2, "Humectant", None),
            "건성": (2, "Humectant", None),
            "민감성": (1, "Humectant", None),
        },
    },
    "프로판다이올": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Humectant/용제", None),
            "복합성": (2, "Humectant/용제", None),
            "건성": (2, "Humectant/용제", None),
            "민감성": (2, "Humectant/용제", None),
        },
    },
    "트레할로오스": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Humectant", None),
            "복합성": (1, "Humectant", None),
            "건성": (2, "Humectant", None),
            "민감성": (2, "Humectant", None),
        },
    },
    "스쿠알란": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Emollient", "피지와 유사한 구조로 가벼운 편"),
            "복합성": (2, "Emollient", None),
            "건성": (3, "Emollient", None),
            "민감성": (2, "Emollient", None),
        },
    },
    "카프릴릭/카프릭트라이글리세라이드": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (1, "Emollient", None),
            "복합성": (2, "Emollient", None),
            "건성": (2, "Emollient", None),
            "민감성": (2, "Emollient", None),
        },
    },
    "세틸알코올": {
        "evidence": _DERMNET,
        "scores": {
            "지성": (0, "Emollient", "지방알코올로 에탄올 등 저분자 알코올과 달리 순함"),
            "복합성": (1, "Emollient", None),
            "건성": (2, "Emollient", None),
            "민감성": (1, "Emollient", None),
        },
    },
    # --- 대한화장품협회 ---
    "향료": {
        "evidence": _KFIA,
        "scores": {
            "지성": (0, None, None),
            "복합성": (0, None, None),
            "건성": (-1, None, "필수 성분은 아니며 건조/민감 피부에서 자극 요인이 될 수 있음"),
            "민감성": (-3, None, "대표적인 접촉성 알레르기 유발 성분으로 꼽힘"),
        },
    },
    "에탄올": {
        "evidence": _KFIA,
        "scores": {
            "지성": (1, "수렴/용제", "휘발성 알코올, 산뜻한 사용감으로 지성 제품에 흔히 쓰임"),
            "복합성": (-1, "수렴/용제", None),
            "건성": (-3, "수렴/용제", "휘발 시 피부 수분을 함께 가져가 건조·장벽손상 우려"),
            "민감성": (-3, "수렴/용제", "장벽이 약해진 상태에서 자극 위험 큼"),
        },
    },
    # --- 화장품 성분과학 컨센서스 (개별 문헌 미검증, 재검토 필요) ---
    "세라마이드엔피": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "피부장벽", None),
            "복합성": (2, "피부장벽", None),
            "건성": (3, "피부장벽", "피부장벽 지질(세라마이드/콜레스테롤/지방산) 구성 성분"),
            "민감성": (3, "피부장벽", None),
        },
    },
    "세라마이드엔지": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "피부장벽", None),
            "복합성": (2, "피부장벽", None),
            "건성": (3, "피부장벽", None),
            "민감성": (3, "피부장벽", None),
        },
    },
    "콜레스테롤": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "피부장벽", None),
            "복합성": (1, "피부장벽", None),
            "건성": (2, "피부장벽", "세라마이드·지방산과 함께 피부장벽 지질을 구성"),
            "민감성": (2, "피부장벽", None),
        },
    },
    "나이아신아마이드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (3, "피지조절/진정", None),
            "복합성": (2, "피지조절/진정", None),
            "건성": (1, "피지조절/진정", None),
            "민감성": (1, "피지조절/진정", "고농도(10%+)에서 일부 민감 피부에 자극 가능"),
        },
    },
    "살리실릭애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (3, "각질/모공관리", None),
            "복합성": (2, "각질/모공관리", None),
            "건성": (-1, "각질/모공관리", "각질 용해 작용이 건성 피부를 더 건조하게 할 수 있음"),
            "민감성": (-2, "각질/모공관리", "산성 각질제거 성분이라 장벽 약화 시 자극 위험"),
        },
    },
    "글라이콜릭애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "각질관리", None),
            "복합성": (1, "각질관리", None),
            "건성": (-1, "각질관리", "AHA 중 분자가 가장 작아 침투력이 강하고 자극도 상대적으로 큼"),
            "민감성": (-2, "각질관리", None),
        },
    },
    "만델릭애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "각질관리", None),
            "복합성": (2, "각질관리", None),
            "건성": (0, "각질관리", "AHA 중 분자가 커서 가장 순한 편으로 알려짐"),
            "민감성": (0, "각질관리", None),
        },
    },
    "레티놀": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "안티에이징/각질회전", None),
            "복합성": (1, "안티에이징/각질회전", None),
            "건성": (0, "안티에이징/각질회전", "각질 회전을 촉진해 건조감을 동반할 수 있음"),
            "민감성": (-2, "안티에이징/각질회전", "초기 사용 시 자극·홍조·각질(레티놀 적응기) 흔함"),
        },
    },
    "아데노신": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "주름개선(기능성)", None),
            "복합성": (2, "주름개선(기능성)", None),
            "건성": (2, "주름개선(기능성)", None),
            "민감성": (2, "주름개선(기능성)", "국내 기능성화장품 고시 성분, 레티놀 대비 자극이 적은 편"),
        },
    },
    "팔미토일펜타펩타이드-4": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "안티에이징(펩타이드)", None),
            "복합성": (2, "안티에이징(펩타이드)", None),
            "건성": (2, "안티에이징(펩타이드)", None),
            "민감성": (2, "안티에이징(펩타이드)", "주요 자극 보고가 적은 편"),
        },
    },
    "아스코빅애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "미백/항산화", None),
            "복합성": (2, "미백/항산화", None),
            "건성": (1, "미백/항산화", None),
            "민감성": (-1, "미백/항산화", "저pH·산화 불안정성으로 민감 피부 자극 가능"),
        },
    },
    "아스코빌글루코사이드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "미백/항산화", "안정화된 비타민C 유도체"),
            "복합성": (2, "미백/항산화", None),
            "건성": (2, "미백/항산화", None),
            "민감성": (1, "미백/항산화", "순수 아스코빅애씨드보다 자극이 적은 편"),
        },
    },
    "3-O-에틸아스코빅애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "미백/항산화", "안정화된 비타민C 유도체"),
            "복합성": (2, "미백/항산화", None),
            "건성": (2, "미백/항산화", None),
            "민감성": (1, "미백/항산화", None),
        },
    },
    "알부틴": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "미백", None),
            "복합성": (2, "미백", None),
            "건성": (1, "미백", None),
            "민감성": (1, "미백", None),
        },
    },
    "트라넥사믹애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "미백/진정", None),
            "복합성": (2, "미백/진정", None),
            "건성": (1, "미백/진정", None),
            "민감성": (1, "미백/진정", "홍조·색소침착 동반 민감 피부에도 비교적 순하게 쓰임"),
        },
    },
    "병풀추출물": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "진정/재생", None),
            "복합성": (2, "진정/재생", None),
            "건성": (2, "진정/재생", None),
            "민감성": (3, "진정/재생", "저자극으로 널리 알려진 진정 성분(시카)"),
        },
    },
    "마데카소사이드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "진정/재생", "병풀 유래 활성 성분"),
            "복합성": (2, "진정/재생", None),
            "건성": (2, "진정/재생", None),
            "민감성": (3, "진정/재생", None),
        },
    },
    "아시아틱애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "진정/재생", "병풀 유래 활성 성분"),
            "복합성": (2, "진정/재생", None),
            "건성": (2, "진정/재생", None),
            "민감성": (3, "진정/재생", None),
        },
    },
    "알란토인": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "진정/피부보호", None),
            "복합성": (2, "진정/피부보호", None),
            "건성": (2, "진정/피부보호", None),
            "민감성": (3, "진정/피부보호", "매우 저자극으로 알려진 대표적 진정 성분"),
        },
    },
    "비사보롤": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "진정", "카모마일 유래"),
            "복합성": (2, "진정", None),
            "건성": (2, "진정", None),
            "민감성": (3, "진정", None),
        },
    },
    "징크옥사이드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "자외선차단(무기)", None),
            "복합성": (1, "자외선차단(무기)", None),
            "건성": (1, "자외선차단(무기)", None),
            "민감성": (2, "자외선차단(무기)", "무기자차는 화학자차보다 자극이 적어 민감 피부에 우선 권장되는 편"),
        },
    },
    "티타늄디옥사이드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "자외선차단(무기)", None),
            "복합성": (1, "자외선차단(무기)", None),
            "건성": (1, "자외선차단(무기)", None),
            "민감성": (2, "자외선차단(무기)", None),
        },
    },
    "벤토나이트": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "피지흡착", None),
            "복합성": (1, "피지흡착", "T존 위주 사용 고려"),
            "건성": (-1, "피지흡착", "흡착 작용이 건성 피부를 더 건조하게 할 수 있음"),
            "민감성": (0, "피지흡착", None),
        },
    },
    "카올린": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "피지흡착", "벤토나이트보다 흡착력이 약하고 순한 편"),
            "복합성": (1, "피지흡착", None),
            "건성": (0, "피지흡착", None),
            "민감성": (1, "피지흡착", None),
        },
    },
    "실리카": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "피지흡착/매트피니시", None),
            "복합성": (1, "피지흡착/매트피니시", None),
            "건성": (0, "피지흡착/매트피니시", None),
            "민감성": (0, "피지흡착/매트피니시", None),
        },
    },
    "알로에잎즙": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (2, "진정/경보습", None),
            "복합성": (1, "진정/경보습", None),
            "건성": (1, "진정/경보습", None),
            "민감성": (1, "진정/경보습", None),
        },
    },
    "멘톨": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "청량감", None),
            "복합성": (0, "청량감", None),
            "건성": (-2, "청량감", "청량감을 주지만 자극 유발 가능성이 있는 성분으로 알려짐"),
            "민감성": (-3, "청량감", None),
        },
    },
    "폴리글루타믹애씨드": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "Humectant", None),
            "복합성": (2, "Humectant", None),
            "건성": (2, "Humectant", None),
            "민감성": (1, "Humectant", None),
        },
    },
    "바이오사카라이드검-1": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "Humectant/진정", None),
            "복합성": (1, "Humectant/진정", None),
            "건성": (2, "Humectant/진정", None),
            "민감성": (1, "Humectant/진정", None),
        },
    },
    "다이프로필렌글라이콜": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "용제", None),
            "복합성": (0, "용제", None),
            "건성": (1, "용제", None),
            "민감성": (0, "용제", None),
        },
    },
    "펜틸렌글라이콜": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "용제/방부보조", None),
            "복합성": (1, "용제/방부보조", None),
            "건성": (1, "용제/방부보조", None),
            "민감성": (0, "용제/방부보조", None),
        },
    },
    "수크로오스": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "Humectant", None),
            "복합성": (0, "Humectant", None),
            "건성": (1, "Humectant", None),
            "민감성": (0, "Humectant", None),
        },
    },
    "아이소노닐아이소노나노에이트": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "Emollient(경질감)", None),
            "복합성": (1, "Emollient(경질감)", None),
            "건성": (1, "Emollient(경질감)", None),
            "민감성": (0, "Emollient(경질감)", None),
        },
    },
    "잔탄검": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "점증제", None),
            "복합성": (0, "점증제", None),
            "건성": (1, "점증제", None),
            "민감성": (0, "점증제", None),
        },
    },
    "카보머": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "점증제", None),
            "복합성": (0, "점증제", None),
            "건성": (0, "점증제", None),
            "민감성": (0, "점증제", None),
        },
    },
    "토코페롤": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (1, "항산화", None),
            "복합성": (1, "항산화", None),
            "건성": (2, "항산화", None),
            "민감성": (1, "항산화", "드물게 접촉성 피부염 보고 사례 있음"),
        },
    },
    "다이소듐이디티에이": {
        "evidence": _CONSENSUS,
        "scores": {
            "지성": (0, "제형안정(킬레이팅)", None),
            "복합성": (0, "제형안정(킬레이팅)", None),
            "건성": (0, "제형안정(킬레이팅)", None),
            "민감성": (0, "제형안정(킬레이팅)", None),
        },
    },
}

_NAME_EN = {"페트롤라텀": "Petrolatum"}


def seed(db_url: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine, tables=[IngredientSkinScore.__table__])

    with Session(engine) as db:
        names = list(_SEED.keys())
        id_by_name = dict(
            db.execute(
                select(Ingredient.name_kr, Ingredient.ingredient_id).where(
                    Ingredient.name_kr.in_(names)
                )
            ).all()
        )
        missing = set(names) - set(id_by_name)
        for name in missing:
            ingredient = Ingredient(name_kr=name, name_en=_NAME_EN.get(name))
            db.add(ingredient)
            db.flush()
            id_by_name[name] = ingredient.ingredient_id
        if missing:
            print(f"missing ingredient added: {sorted(missing)}")

        insert_fn = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        rows = 0
        for name, entry in _SEED.items():
            ingredient_id = id_by_name[name]
            evidence_level, source = entry["evidence"]
            for skin_type, (score, function, caution) in entry["scores"].items():
                stmt = (
                    insert_fn(IngredientSkinScore)
                    .values(
                        ingredient_id=ingredient_id,
                        skin_type=skin_type,
                        score=score,
                        function=function,
                        evidence_level=evidence_level,
                        source=source,
                        caution=caution,
                    )
                    .on_conflict_do_update(
                        index_elements=["ingredient_id", "skin_type"],
                        set_={
                            "score": score,
                            "function": function,
                            "evidence_level": evidence_level,
                            "source": source,
                            "caution": caution,
                        },
                    )
                )
                db.execute(stmt)
                rows += 1
        db.commit()
        print(f"{len(_SEED)} ingredients / {rows} ingredient_skin_score rows upserted into {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    seed(args.db_url)
