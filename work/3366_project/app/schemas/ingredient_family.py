from pydantic import BaseModel


class FamilyRankRead(BaseModel):
    family_name: str
    # 이 제품이 큐레이션은 돼있지만(product_family_member) 실제 전성분표에서 이 계열 성분을
    # 하나도 못 찾았을 때 False — 이땐 아래 필드가 전부 None/0이고, 프론트는 순위 카드 대신
    # "{family_name} 성분 비교 데이터가 없어요" 안내만 보여준다(get_product_family_rank 참고).
    has_data: bool = True
    representative_ingredient: str | None = None
    # 라벨에 함량이 적혀있을 때만("2,400ppm", "0.2%" 등 원문 그대로) — 없으면 None.
    representative_concentration: str | None = None
    label_rank: int | None = None
    rank: int | None = None
    total_count: int | None = None
    average_label_rank: float | None = None
    # "상위 N%" 라벨용 — 작을수록 좋음(1등이면 항상 1, 0은 없음). ceil(rank / total_count * 100).
    top_percentile: int | None = None
    # 계열 내 큐레이션 제품들의 대표 성분 함량을 전부 %로 환산한 평균 — 라벨에 함량이 아예
    # 안 적힌 제품은 계산에서 빠진다(None이면 함량 표시된 제품이 하나도 없다는 뜻).
    average_concentration_percent: float | None = None
    # 위 평균이 몇 개 제품 값으로 계산됐는지(전체 total_count 중 일부일 수 있음) — 프론트가
    # "N개 제품 기준" 같은 신뢰도 문구를 붙일 때 쓴다.
    concentration_sample_count: int = 0
