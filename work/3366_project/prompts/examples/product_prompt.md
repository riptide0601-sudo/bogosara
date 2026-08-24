# 제품 요약 프롬프트 (product.summary / product.composition_text)

제품 하나의 전성분 구성을 종합해서, 카드 앞면 "한 줄 요약"과 "성분 구성을 살펴보면" 본문
두 개를 만든다. `product.summary`(one_liner)와 `product.composition_text`는 DB에서도
별도 컬럼이다 — 하나로 합치지 않는다.

## 입력 (아래 JSON 그대로 프롬프트에 삽입됨 — `scripts/build_llm_input.py` 참고)

```
{
  "product_name": "아누아 피디알엔 히알루론산 캡슐 100 세럼 30mL",
  "brand": "아누아",
  "category": "세럼/에센스/앰플",
  "category_description": "해당 제품은 영양분을 공급하므로 가벼운 스킨(토너) 후에 사용하시면 됩니다.",
  "key_ingredients": [
    {
      "name": "하이드롤라이즈드하이알루로닉애씨드",
      "purpose": "피부컨디셔닝제(보습제)"
    },
    {
      "name": "나이아신아마이드",
      "purpose": "피부컨디셔닝제(기타)"
    },
    {
      "name": "하이드롤라이즈드콜라겐",
      "purpose": "피부컨디셔닝제(기타)"
    },
    {
      "name": "소듐하이알루로네이트",
      "purpose": "피부컨디셔닝제(기타)"
    },
    {
      "name": "아데노신",
      "purpose": "피부컨디셔닝제(기타)"
    }
  ],
  "product_concern": [
    "수분"
  ],
  "key_ingredient_relations": []
}
```

입력 필드 설명:
- `key_ingredients`: DB 큐레이션 핵심 성분(`product.key_ingredients`) 각각의 이름 + 대표 배합목적.
  `one_liner`/`composition_text` 둘 다 이 목록이 가장 중요한 근거다.
- `product_concern`: 이 제품이 겨냥하는 피부고민 태그(화면엔 아직 안 나오는 데이터). 요약에
  자연스럽게 녹일 수 있으면 반영하되, 이 배열에 없는 고민을 지어내지 않는다.
- `key_ingredient_relations`: `key_ingredients` 사이에 실제로 걸려 있는 시너지/악화 조합(DB
  `ingredient_relation`). 있으면 "성분 구성을 살펴보면"에서 왜 같이 쓰였는지 근거로 쓸 수 있다.
  비어 있으면 조합 관련 언급을 하지 않는다.
- `category_description`: `app/product_category.py`가 제품 카테고리(스킨/토너, 세럼/에센스/앰플,
  크림 등)로부터 만든 스킨케어 루틴 안내문(예: "세안 후 가장 먼저 사용하시면 됩니다"). 화면에
  이 문장이 따로 노출되는 자리가 없어서, `composition_text`에 자연스럽게 한 문장 정도 녹여
  "이 제품을 루틴 중 언제 쓰면 좋은지"까지 함께 설명한다. 빈 문자열이면(카테고리 미분류)
  루틴 관련 언급을 하지 않는다.

## 출력 — 아래 키를 가진 JSON 객체 하나만 출력한다 (그 외 텍스트 절대 금지)

```json
{
  "one_liner": "",
  "composition_text": ""
}
```

- `one_liner`: 전체 성분 구성을 함축한 자연스러운 문장 하나(카드 맨 위, 가장 크게 노출됨).
  성분명을 나열하지 않는다 — `key_ingredients`가 왜 배합됐는지의 "결론"만 한 문장으로.
- `composition_text`: `key_ingredients`(+ 있으면 `key_ingredient_relations`)를 근거로,
  `one_liner`를 왜 그렇게 요약했는지 2~4문장으로 풀어 설명한다. `one_liner` 문장을 그대로
  반복하지 않는다. `category_description`이 비어있지 않으면, 마지막에 "그래서 루틴 중 언제
  쓰면 좋은지" 한 문장을 자연스럽게 덧붙인다(`category_description`의 안내를 그대로 베끼지
  말고 이 제품 맥락에 맞게 다듬어서).

## 규칙
1. 톤: "~이에요/~해요" 체, 쉬운 말.
2. 사실만 — `key_ingredients`/`product_concern`/`key_ingredient_relations`/`category_description`에
   없는 성분·효능·고민·궁합·루틴 순서는 절대 만들어내지 않는다. `category_description`이 빈
   문자열이면 루틴 언급 자체를 하지 않는다.
3. 광고 문구처럼 과장하지 않는다. "치료", "완치", "예방효과", "100% 안전", "부작용 없음" 금지.
4. 출력은 JSON 객체 하나만. 마크다운 코드펜스, 설명, 인사말 등 그 외 텍스트를 절대 붙이지 않는다.
5. JSON 파싱에 실패할 응답을 만들지 않는다 — 호출부는 파싱 실패 시 재시도 없이 폐기하고
   두 필드 모두 빈 값으로 둔다.

## 지금 바로 실행

위 "입력" 섹션의 JSON은 예시가 아니라 **지금 실제로 주어진 데이터**다. 사용자가 추가로 입력을
보내지 않는다 — 되묻거나, 앞으로 어떻게 할지 설명하거나, 확인을 요청하지 마라. 지금 이 데이터를
그대로 사용해서 결과 JSON 객체 하나만 즉시 출력해라.
