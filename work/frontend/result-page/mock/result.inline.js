// mock/result.json 과 완전히 동일한 내용을 window 전역변수로 감싼 파일.
// 존재 이유: result.html을 서버 없이 file://로 더블클릭해서 열면 fetch('./mock/result.json')이
// 브라우저 보안 정책(CORS)에 막혀 항상 실패한다 — 반면 이렇게 <script src>로 불러오는 일반
// 스크립트는 file://에서도 정상 동작한다. render.js는 fetch를 먼저 시도하고, 실패하면(=
// file://로 열었을 가능성이 높으면) 이 전역변수로 자동 폴백한다.
//
// ⚠ 이 파일은 mock/result.json에서 그대로 생성한 것 — 목 데이터를 고칠 땐 반드시
// mock/result.json을 먼저 고치고, 이 파일은 그 내용을 다시 붙여넣어 동기화할 것.
window.__MOCK_RESULT__ = {
  "product": {
    "product_name": "발효 펩타이드 세럼",
    "raw_ingredients": "아쿠아(물), 락토코커스 발효 용해물, 글리세린, 에틸 리놀레에이트, 하이드록시에틸 아크릴레이트/소듐 아크릴로일디메틸 타우레이트 공중합체, 헥사노일 디펩타이드-3 노르류신 아세테이트, 미리스토일 노나펩타이드-3, 효모 추출물, 대두 아미노산, 비사볼롤, 슈도알테로모나스 엑소폴리사카라이드, 레시틴, 소르비탄 이소스테아레이트, 이소헥사데칸, 폴리소르베이트 60, 폴리아크릴레이트 크로스폴리머-6, 트리소듐 에틸렌디아민 디숙시네이트, 살리실산나트륨, 구연산, 염화나트륨, 소르빈산칼륨, 소듐 벤조에이트, 펜틸렌 글리콜, 에톡시디글리콜, 페녹시에탄올, 클로르페네신",
    "summary": {
      "one_liner": "발효 + 펩타이드가 들어간 순한 저자극 조합!",
      "total_count": 26,
      "star_count": 1,
      "good_count": 8,
      "key_purposes": "펩타이드(세포 신호 전달), 글리세린(보습), 비사볼롤(진정)이 핵심.",
      "product_character": "발효 유래 + 펩타이드 중심의 순한 저자극 세럼. 무알코올·향료 무첨가.",
      "similar_or_conflict": "펩타이드 세럼과 궁합이 좋고, 강한 산·고농도 비타민C와는 시간대를 나누는 게 좋아요.",
      "restricted_notes": null
    }
  },
  "ingredients": [
    {
      "name_kr": "아쿠아(물)",
      "name_en": "Aqua",
      "display_grade": "base",
      "label_rank": 1,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "용제(베이스)",
          "description": "성분들을 녹이고 담아내는 화장품의 기본 베이스."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "제품의 대부분을 차지하는 기본 베이스 물이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "다른 성분을 녹이고 담는 용제 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "거의 모든 제형의 기본 베이스라 궁합을 따질 필요는 없어요."
      }
    },
    {
      "name_kr": "락토코커스 발효 용해물",
      "name_en": "Lactococcus Ferment Lysate",
      "display_grade": "good",
      "label_rank": 2,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "발효 유래 케어",
          "description": "발효 과정에서 얻은 순한 케어 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "유산균 발효로 얻은 순한 케어 성분이에요.",
        "benefit_text": "발효 유래라 자극은 낮추고 피부 컨디션 케어에 도움을 줘요.",
        "caution_text": "",
        "usage_reason_text": "발효 유래 케어 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "진정·보습 성분과 함께 쓰면 시너지가 좋아요."
      }
    },
    {
      "name_kr": "글리세린",
      "name_en": "Glycerin",
      "display_grade": "star",
      "label_rank": 3,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "피부컨디셔닝제(보습제)",
          "description": "피부에 수분을 공급/유지하도록 돕는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "피부가 원래 가진 성분과 비슷한 대표 보습제.",
        "benefit_text": "촉촉함을 오래 잡아주는 수분 지킴이.",
        "caution_text": "",
        "usage_reason_text": "보습 · 수분 지킴이 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "대부분 성분과 잘 어울림."
      }
    },
    {
      "name_kr": "에틸리놀레에이트",
      "name_en": "Ethyl Linoleate",
      "display_grade": "base",
      "label_rank": 4,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "보들 매끈 · 착향",
          "description": "피부를 부드럽게 하고 은은한 향을 더하는 오일 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "발림성을 부드럽게 해주는 오일류 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "보들함과 은은한 향을 위해 배합.",
        "caution_group_text": "",
        "combo_recommendation": "보습 성분과 함께면 발림성이 더 좋아져요."
      }
    },
    {
      "name_kr": "하이드록시에틸 아크릴레이트/소듐 아크릴로일디메틸 타우레이트 공중합체",
      "name_en": "Copolymer",
      "display_grade": "base",
      "label_rank": 5,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "제형·점도 잡기",
          "description": "제품의 텍스처와 점도를 매끄럽게 잡아주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "제형을 매끄럽게 잡아주는 점증제예요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "텍스처·점도 조절 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정에 쓰이는 성분이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "헥사노일 디펩타이드-3 노르류신 아세테이트",
      "name_en": "Peptide",
      "display_grade": "good",
      "label_rank": 6,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "세포 신호 전달",
          "description": "피부 세포끼리 신호를 주고받도록 돕는 펩타이드 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "피부 세포 신호 전달을 돕는 펩타이드 성분이에요.",
        "benefit_text": "요즘 인기 있는 펩타이드 케어 성분으로, 피부 컨디션 관리에 도움을 줘요.",
        "caution_text": "",
        "usage_reason_text": "세포 신호 전달(펩타이드) 케어 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 펩타이드·보습 성분과 함께 쓰면 좋아요."
      }
    },
    {
      "name_kr": "미리스토일 노나펩타이드-3",
      "name_en": "Myristoyl Nonapeptide-3",
      "display_grade": "good",
      "label_rank": 7,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "세포 신호 전달",
          "description": "피부 세포끼리 신호를 주고받도록 돕는 펩타이드 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "피부 세포 신호 전달을 돕는 펩타이드 성분이에요.",
        "benefit_text": "위 펩타이드 성분과 함께 세포 케어 효과를 더해줘요.",
        "caution_text": "",
        "usage_reason_text": "세포 신호 전달(펩타이드) 케어 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 펩타이드 성분과 궁합이 좋아요."
      }
    },
    {
      "name_kr": "효모 추출물",
      "name_en": "Yeast Extract",
      "display_grade": "good",
      "label_rank": 8,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "수분 지킴이",
          "description": "피부의 촉촉함을 유지하도록 돕는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "촉촉함 유지에 도움을 주는 효모 유래 성분이에요.",
        "benefit_text": "보습과 영양 공급에 도움을 줘요.",
        "caution_text": "",
        "usage_reason_text": "수분 지킴이 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "보습 성분과 함께면 효과가 배가돼요."
      }
    },
    {
      "name_kr": "대두 아미노산",
      "name_en": "Soybean Amino Acids",
      "display_grade": "good",
      "label_rank": 9,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "수분 지킴이",
          "description": "보습을 돕는 아미노산 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "보습에 도움을 주는 식물 유래 아미노산이에요.",
        "benefit_text": "피부 속 수분을 붙잡아두는 데 도움을 줘요.",
        "caution_text": "",
        "usage_reason_text": "보습 도움 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 보습 성분과 함께 쓰면 좋아요."
      }
    },
    {
      "name_kr": "비사볼롤",
      "name_en": "Bisabolol",
      "display_grade": "good",
      "label_rank": 10,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "진정 케어",
          "description": "예민해진 피부를 부드럽게 달래주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "캐모마일에서 얻는 대표적인 진정 성분이에요.",
        "benefit_text": "예민하고 붉어진 피부를 부드럽게 달래줘요.",
        "caution_text": "",
        "usage_reason_text": "진정 케어 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "보습·발효 성분과 함께면 저자극 조합이 완성돼요."
      }
    },
    {
      "name_kr": "슈도알테로모나스 외다당류",
      "name_en": "Pseudoalteromonas Exopolysaccharides",
      "display_grade": "good",
      "label_rank": 11,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "수분 지킴이",
          "description": "보습에 도움을 주는 해양 유래 다당류 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "해양 미생물에서 얻는 보습 다당류예요.",
        "benefit_text": "피부 표면에 막을 형성해 수분 손실을 줄이는 데 도움을 줘요.",
        "caution_text": "",
        "usage_reason_text": "수분 지킴이 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 보습 성분과 함께 쓰면 좋아요."
      }
    },
    {
      "name_kr": "레시틴",
      "name_en": "Lecithin",
      "display_grade": "good",
      "label_rank": 12,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "보들 매끈 · 물기름 섞기",
          "description": "유화를 돕고 피부를 부드럽게 하는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "물과 기름을 잘 섞어주는 천연 유래 유화 성분이에요.",
        "benefit_text": "피부 장벽을 구성하는 성분과 비슷해 부드러운 사용감을 줘요.",
        "caution_text": "",
        "usage_reason_text": "유화 도움 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정에 쓰이는 성분이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "소르비탄 이소스테아레이트",
      "name_en": "Sorbitan Isostearate",
      "display_grade": "base",
      "label_rank": 13,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "물기름 섞기",
          "description": "유화를 돕는 계면활성 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "물과 기름을 섞어주는 유화제예요.",
        "benefit_text": "",
        "caution_text": "모공을 살짝 막을 수 있어요 (경미한 수준).",
        "usage_reason_text": "유화제 목적으로 배합.",
        "caution_group_text": "모공막힘 가능 성분",
        "combo_recommendation": "트러블성 피부라면 사용감을 지켜보는 게 좋아요."
      }
    },
    {
      "name_kr": "이소헥사데칸",
      "name_en": "Isohexadecane",
      "display_grade": "base",
      "label_rank": 14,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "보들 매끈 · 용매",
          "description": "발림성을 도와주는 용매 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "발림성을 부드럽게 해주는 용매 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "발림성 개선 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 보조 성분이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "폴리소르베이트 60",
      "name_en": "Polysorbate 60",
      "display_grade": "base",
      "label_rank": 15,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "물기름 섞기 · 세정",
          "description": "유화와 계면활성을 돕는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "물과 기름을 섞어주는 유화·계면활성 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "유화·계면활성 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정에 쓰이는 성분이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "폴리아크릴레이트 크로스폴리머-6",
      "name_en": "Polyacrylate Crosspolymer-6",
      "display_grade": "base",
      "label_rank": 16,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "제형·점도 잡기",
          "description": "텍스처를 조절해주는 점증제."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "텍스처를 매끄럽게 잡아주는 점증제예요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "텍스처 조절 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정 목적이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "트리소듐 에틸렌디아민 디숙시네이트",
      "name_en": "Trisodium EDDS",
      "display_grade": "base",
      "label_rank": 17,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "성분 안정화",
          "description": "금속 이온을 붙잡아 제품 변질을 막아주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "제품이 변질되지 않도록 잡아주는 안정화 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "성분 안정화 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정 목적이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "살리실산나트륨",
      "name_en": "Sodium Salicylate",
      "display_grade": "base",
      "label_rank": 18,
      "safety_level": "주의",
      "purposes": [
        {
          "name": "보존",
          "description": "제품이 상하지 않도록 지켜주는 성분."
        }
      ],
      "restricted": {
        "regulate_type": "주의",
        "limit_cond": "만 3세 이하 영유아용 제품에는 사용할 수 없는 성분이에요."
      },
      "llm_summary": {
        "summary_text": "보존을 돕는 살리실산 계열 성분이에요.",
        "benefit_text": "",
        "caution_text": "만 3세 이하 영유아 제품에는 쓰이지 않는 성분이에요.",
        "usage_reason_text": "보존 목적으로 배합.",
        "caution_group_text": "사용상 주의사항 표시 대상 성분",
        "combo_recommendation": "일반 성인 사용 제품에서는 크게 신경쓰지 않아도 돼요."
      }
    },
    {
      "name_kr": "구연산",
      "name_en": "Citric Acid",
      "display_grade": "base",
      "label_rank": 19,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "산도(pH) 조절",
          "description": "제품의 산도를 피부에 맞게 맞춰주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "제품의 pH를 피부 친화적으로 맞춰주는 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "산도(pH) 조절 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정 목적이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "염화나트륨",
      "name_en": "Sodium Chloride",
      "display_grade": "base",
      "label_rank": 20,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "제형·점도 잡기",
          "description": "점도를 조절해주는 소금 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "점도를 잡아주는 소금 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "점도 조절 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 안정 목적이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "소르빈산칼륨",
      "name_en": "Potassium Sorbate",
      "display_grade": "base",
      "label_rank": 21,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "보존",
          "description": "제품이 상하지 않도록 지켜주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "널리 쓰이는 순한 보존 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "보존 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 보존제와 함께 배합돼 안정성을 높여요."
      }
    },
    {
      "name_kr": "소듐벤조에이트",
      "name_en": "Sodium Benzoate",
      "display_grade": "base",
      "label_rank": 22,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "보존",
          "description": "제품이 상하지 않도록 지켜주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "널리 쓰이는 보존 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "보존 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 보존제와 함께 배합돼 안정성을 높여요."
      }
    },
    {
      "name_kr": "펜틸렌 글리콜",
      "name_en": "Pentylene Glycol",
      "display_grade": "base",
      "label_rank": 23,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "용매 · 수분 지킴이",
          "description": "보습을 돕고 다른 성분을 녹이는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "보습을 도우면서 다른 성분을 녹여주는 용매예요.",
        "benefit_text": "가벼운 보습 도움을 줘요.",
        "caution_text": "",
        "usage_reason_text": "용매·보습 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "보존제와 함께 쓰이면 방부력도 보완해줘요."
      }
    },
    {
      "name_kr": "에톡시디글리콜",
      "name_en": "Ethoxydiglycol",
      "display_grade": "base",
      "label_rank": 24,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "용매 · 수분 · 착향",
          "description": "성분이 잘 섞이도록 돕는 용매 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "성분들이 고르게 섞이도록 돕는 용매예요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "용매 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "제형 보조 성분이라 궁합 이슈는 거의 없어요."
      }
    },
    {
      "name_kr": "페녹시에탄올",
      "name_en": "Phenoxyethanol",
      "display_grade": "base",
      "label_rank": 25,
      "safety_level": "주의",
      "purposes": [
        {
          "name": "보존",
          "description": "널리 쓰이는 방부 성분."
        }
      ],
      "restricted": {
        "regulate_type": "한도",
        "limit_cond": "배합 한도 1% 이하로 제한되는 보존제예요."
      },
      "llm_summary": {
        "summary_text": "화장품에 가장 널리 쓰이는 방부 성분이에요.",
        "benefit_text": "",
        "caution_text": "배합 한도가 정해져 있는 성분이라 정해진 한도 내에서만 쓰여요.",
        "usage_reason_text": "보존 목적으로 배합.",
        "caution_group_text": "배합 한도 성분",
        "combo_recommendation": "다른 보존제와 함께 낮은 농도로 배합되는 경우가 많아요."
      }
    },
    {
      "name_kr": "클로르페네신",
      "name_en": "Chlorphenesin",
      "display_grade": "base",
      "label_rank": 26,
      "safety_level": "일반",
      "purposes": [
        {
          "name": "보존 · 항균",
          "description": "세균 번식을 억제해주는 성분."
        }
      ],
      "restricted": null,
      "llm_summary": {
        "summary_text": "세균 번식을 막아주는 보존·항균 성분이에요.",
        "benefit_text": "",
        "caution_text": "",
        "usage_reason_text": "보존·항균 목적으로 배합.",
        "caution_group_text": "",
        "combo_recommendation": "다른 보존제와 함께 배합돼 안정성을 높여요."
      }
    }
  ]
};
