# 성분 요약 프롬프트 (ingredient llm_summary)

성분 하나를 화장품 성분 정보에 익숙하지 않은 사용자에게 설명하는 문구를 만든다.
이 프롬프트가 만드는 값은 `llm_summary` 테이블의 `summary_text` / `benefit_text` /
`usage_reason_text` / `combo_recommendation` / `caution_text` 다.

## 입력 (아래 JSON 그대로 프롬프트에 삽입됨 — `scripts/build_llm_input.py` 참고)

```
{
  "product": {
    "product_name": "아누아 피디알엔 히알루론산 캡슐 100 세럼 30mL",
    "brand": "아누아",
    "category": "세럼/에센스/앰플",
    "key_ingredients": [
      "나이아신아마이드",
      "소듐하이알루로네이트",
      "아데노신",
      "하이드롤라이즈드콜라겐",
      "하이드롤라이즈드하이알루로닉애씨드"
    ],
    "key_purposes": [
      "보습",
      "컨디셔닝",
      "탄력",
      "주름개선"
    ],
    "product_concern": [
      "수분"
    ]
  },
  "ingredient": {
    "name_kr": "나이아신아마이드",
    "name_en": "Niacinamide",
    "safety_level": null,
    "is_key": true,
    "purposes": [
      {
        "name": "피부컨디셔닝제(기타)",
        "description": "벗겨짐을 줄이고 탄력을 회복시켜 건조하고 손상된 피부의 외관을 개선시키는 성분."
      },
      {
        "name": "헤어컨디셔닝제",
        "description": "모발에 특별한 효과를 부여하는 성분으로 모발의 외형과 느낌 개선, 유연성 증대, 스타일 증진, 윤택 및 광택 부여, 모발의 질감 개선 등을 목적으로 함."
      }
    ],
    "relations": [
      {
        "relation_type": "시너지",
        "related_ingredient": "트라넥사믹애씨드",
        "note": "두 성분이 함께 작용해서 미백 효과를 더 끌어올려주는 조합이에요. 실제 임상시험에서도 색소침착 개선 효과가 확인됐어요"
      },
      {
        "relation_type": "시너지",
        "related_ingredient": "아세틸글루코사민",
        "note": "서로 다른 방식으로 미백에 작용해서, 함께 쓰면 효과가 더 좋아질 수 있다고 임상적으로 확인된 조합이에요"
      }
    ],
    "skin_scores": [
      {
        "skin_type": "건성",
        "is_risk": false,
        "function": null,
        "caution": "배양 각질형성세포 및 인체 피부 실험 — 니코틴아마이드가 세라마이드 생합성을 용량 의존적으로 4.1~5.5배 증가(SPT 효소 mRNA 발현 촉진 기전), 유리지방산 2.3배·콜레스테롤 1.5배 증가. 건성 피부 국소도포 시 TEWL 감소 확인(원문 확인됨)"
      },
      {
        "skin_type": "지성",
        "is_risk": false,
        "function": null,
        "caution": "100명 이중맹검 위약대조 시험, 2% 도포 4주 후 피지 분비율(SER) 유의하게 감소"
      }
    ]
  }
}
```

입력 필드 설명:
- `product`: 이 성분이 들어있는 제품 맥락 (제품명/브랜드/카테고리/핵심성분/핵심배합목적/피부고민 태그).
  화면엔 없어도 `product_concern`은 근거로 넘어온다.
- `ingredient.is_key`: 이 제품의 큐레이션된 핵심 성분(`product.key_ingredients`)에 포함되는지.
  true면 더 비중 있게, 구체적으로 설명한다.
- `ingredient.purposes`: DB 배합목적 + 정의문. 이 성분이 "왜" 들어가는지의 유일한 근거.
- `ingredient.relations`: 이 성분과 다른 성분의 시너지/악화 조합 (사람이 미리 검수한 문장 `note`
  포함). `combo_recommendation`은 반드시 이 배열에 있는 내용만 근거로 쓴다 — 배열이 비어 있으면
  `combo_recommendation`도 반드시 빈 문자열.
- `ingredient.skin_scores`: 피부타입별 적합도(화면엔 아직 안 나오는 데이터). 요약을 풍부하게 할
  근거로만 쓰고, 화면에 없는 개념(피부타입별 점수 등)을 직접 언급하지는 않는다 — 자연스럽게 녹여서만.
- `ingredient.safety_level`: 값이 있을 때만 `caution_text`의 근거가 된다. null이면 `caution_text`는
  반드시 빈 문자열.

## 출력 — 아래 키를 가진 JSON 객체 하나만 출력한다 (그 외 텍스트 절대 금지)

```json
{
  "summary_text": "",
  "benefit_text": "",
  "usage_reason_text": "",
  "combo_recommendation": "",
  "caution_text": ""
}
```

- `summary_text`: 이 성분이 화장품에서 어떤 역할을 하는지 1~2문장. `purposes`(+있으면 `skin_scores`)
  가 근거.
- `benefit_text`: 사용자 입장에서 좋은 점 1문장. `purposes`/`skin_scores`가 근거.
- `usage_reason_text`: "왜 이 제품에 배합됐는지" 1문장. `purposes`가 근거.
- `combo_recommendation`: `relations`가 있을 때만, 그 안의 `relation_type`/`related_ingredient`/
  `note`를 문장으로 다듬어 1~2문장. `relations`가 비어 있으면 반드시 `""`.
- `caution_text`: `safety_level`이 있을 때만 그걸 근거로 1문장. null이면 반드시 `""`.

## 규칙
1. 톤: "~이에요/~해요" 체, 쉬운 말. 각 필드 1~2문장을 넘기지 않는다.
2. 사실만 — 입력 JSON에 없는 성분명·효능·궁합·규제는 절대 만들어내지 않는다. 짐작·창작 금지.
3. `relations`/`purposes`/`safety_level`/`is_key`는 이미 DB에서 읽어 화면에 표시되는 값이다 —
   여기서 그 값을 다시 나열/반복하지 말고, 그 근거로 "문장"만 새로 만든다.
4. "치료", "완치", "예방효과", "100% 안전", "부작용 없음" 같은 의학적 단정 표현 금지.
5. `is_key: true`인 성분은 더 구체적이고 비중 있게 쓰고, `false`(일반 성분)는 담백하게 짧게 쓴다.
6. 출력은 JSON 객체 하나만. 마크다운 코드펜스, 설명, 인사말 등 그 외 텍스트를 절대 붙이지 않는다.
7. JSON 파싱에 실패할 응답(코드펜스로 감싸거나 트레일링 텍스트가 붙는 등)을 만들지 않는다 —
   호출부는 파싱 실패 시 전체를 재시도 없이 폐기하고 필드를 빈 값으로 둔다(원문 description
   폴백은 호출부 책임).

## 지금 바로 실행

위 "입력" 섹션의 JSON은 예시가 아니라 **지금 실제로 주어진 데이터**다. 사용자가 추가로 입력을
보내지 않는다 — 되묻거나, 앞으로 어떻게 할지 설명하거나, 확인을 요청하지 마라. 지금 이 데이터를
그대로 사용해서 결과 JSON 객체 하나만 즉시 출력해라.
