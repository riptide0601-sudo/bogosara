/**
 * 보고사라 — 스캔 결과 페이지 렌더러.
 *
 * 이 페이지는 아래 render(data) 하나만으로 전체 화면을 그린다.
 * data의 형태(JSON 계약)는 mock/result.json을 참고 — product/ingredients 두 키만 갖는다.
 *
 * 지금은 mock 데이터를 쓰지만, 실제 API가 준비되면 loadData() 안의
 * "TODO: API 연결" 지점 한 줄만 실제 엔드포인트로 바꾸면 된다.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------
  // 0. 데이터 로드 — mock → (나중엔) 실제 API
  // ---------------------------------------------------------
  async function loadData() {
    // TODO: API 연결 — 준비되면 아래 두 줄을 다음처럼 바꾸면 된다.
    //   const res = await fetch('/api/scan-result?id=...');
    //   return await res.json();
    try {
      const res = await fetch('./mock/result.json');
      if (!res.ok) throw new Error('mock/result.json 응답 실패: ' + res.status);
      return await res.json();
    } catch (err) {
      // result.html을 서버 없이 file://로 직접 열면 fetch가 항상 실패한다(CORS).
      // 그런 경우엔 result.html에 <script>로 미리 심어둔 동일한 목 데이터로 폴백한다.
      console.warn('[보고사라][결과 페이지] fetch 실패 — 인라인 목 데이터로 대체합니다.', err);
      if (window.__MOCK_RESULT__) return window.__MOCK_RESULT__;
      throw err;
    }
  }

  // ---------------------------------------------------------
  // 1. 등급별 배지 라벨
  // ---------------------------------------------------------
  var GRADE_ORDER = { star: 0, good: 1, base: 2 };
  var GRADE_BADGE = {
    star: { className: 'b-star', html: '슈퍼<br>스타' },
    good: { className: 'b-good', html: '구디' },
    base: { className: 'b-base', html: '기본' },
  };

  function el(tag, className, html) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (html !== undefined) node.innerHTML = html;
    return node;
  }

  // ---------------------------------------------------------
  // 2. 전성분 한 줄(row) 만들기
  //    등급 배지 + 성분명(국/영문) + usage_reason_text 한 줄 + (규제 성분이면) caution pill
  // ---------------------------------------------------------
  function buildIngredientRow(ingredient) {
    var badge = GRADE_BADGE[ingredient.display_grade] || GRADE_BADGE.base;

    var row = el('div', 'ing-row sticker');

    var badgeEl = el('div', 'r-badge ' + badge.className, badge.html);
    row.appendChild(badgeEl);

    var main = el('div', 'r-main');

    var nameEl = el(
      'div',
      'r-name',
      escapeHtml(ingredient.name_kr) + ' <span class="r-en">' + escapeHtml(ingredient.name_en) + '</span>',
    );
    main.appendChild(nameEl);

    var reasonText = (ingredient.llm_summary && ingredient.llm_summary.usage_reason_text) || '';
    if (reasonText) {
      main.appendChild(el('div', 'r-func', escapeHtml(reasonText)));
    }

    if (ingredient.restricted) {
      var pills = el('div', 'r-pills');
      var pill = el('span', 'pill warn', '⚠ ' + escapeHtml(ingredient.restricted.regulate_type));
      pill.title = ingredient.restricted.limit_cond || '';
      pills.appendChild(pill);
      main.appendChild(pills);
    }

    row.appendChild(main);
    return row;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // ---------------------------------------------------------
  // 3. 요약 노트 한 줄 만들기 (key_purposes / product_character / similar_or_conflict / restricted_notes)
  // ---------------------------------------------------------
  function buildSummaryNote(label, text, isRestricted) {
    var note = el('div', 'summary-note' + (isRestricted ? ' restricted' : ''));
    note.innerHTML = '<b>' + escapeHtml(label) + '</b>' + escapeHtml(text);
    return note;
  }

  // ---------------------------------------------------------
  // 4. 메인 렌더 — data 하나만 받아서 화면 전체를 그린다
  // ---------------------------------------------------------
  function render(data) {
    var product = data.product;
    var summary = product.summary;
    var ingredients = data.ingredients.slice();

    document.title = '보고사라 — ' + product.product_name + ' 스캔 결과';

    // ---- 왼쪽: 스캔 원본 카드 ----
    document.getElementById('raw-text-left').textContent = product.raw_ingredients;
    document.getElementById('raw-text-bottom').textContent = product.raw_ingredients;

    // ---- 요약 블록 ----
    document.getElementById('prod-name').textContent =
      '📄 ' + product.product_name + ' · 전성분 ' + summary.total_count + '종';
    document.getElementById('oneline').textContent = '✎ ' + summary.one_liner;
    document.getElementById('stat-star').textContent = summary.star_count;
    document.getElementById('stat-good').textContent = summary.good_count;
    document.getElementById('stat-total').textContent = summary.total_count;

    var notesWrap = document.getElementById('summary-notes');
    notesWrap.innerHTML = '';
    if (summary.key_purposes) notesWrap.appendChild(buildSummaryNote('핵심 성분 ', summary.key_purposes));
    if (summary.product_character) notesWrap.appendChild(buildSummaryNote('제품 특징 ', summary.product_character));
    if (summary.similar_or_conflict) notesWrap.appendChild(buildSummaryNote('궁합 팁 ', summary.similar_or_conflict));
    // restricted_notes는 값이 있을 때만 코랄로 강조해서 보여준다
    if (summary.restricted_notes) {
      notesWrap.appendChild(buildSummaryNote('⚠ 주의 ', summary.restricted_notes, true));
    }

    // ---- 전성분 리스트: star → good → base 순으로 정렬 ----
    ingredients.sort(function (a, b) {
      var byGrade = GRADE_ORDER[a.display_grade] - GRADE_ORDER[b.display_grade];
      if (byGrade !== 0) return byGrade;
      return a.label_rank - b.label_rank;
    });

    var primaryList = document.getElementById('ing-list-primary');
    var baseList = document.getElementById('ing-list-base');
    primaryList.innerHTML = '';
    baseList.innerHTML = '';

    var baseCount = 0;
    ingredients.forEach(function (ingredient) {
      var row = buildIngredientRow(ingredient);
      if (ingredient.display_grade === 'base') {
        baseList.appendChild(row);
        baseCount += 1;
      } else {
        // 주요 성분(슈퍼스타·구디)은 항상 펼쳐서 보여준다
        primaryList.appendChild(row);
      }
    });

    // ---- "기본 성분 더보기" 토글 ----
    var moreToggle = document.getElementById('more-toggle');
    moreToggle.querySelector('.label').textContent = '기본 성분 더보기 (' + baseCount + '개)';
    moreToggle.addEventListener('click', function () {
      var expanded = baseList.classList.toggle('expanded');
      moreToggle.classList.toggle('expanded', expanded);
      moreToggle.setAttribute('aria-expanded', String(expanded));
      moreToggle.querySelector('.label').textContent = expanded
        ? '기본 성분 접기'
        : '기본 성분 더보기 (' + baseCount + '개)';
    });
  }

  // ---------------------------------------------------------
  // 5. 하단 액션 버튼 — 아직 실제 라우팅/카메라 연동 없음 (스텁)
  // ---------------------------------------------------------
  function bindActions() {
    document.getElementById('rescan-btn').addEventListener('click', function () {
      // TODO: 실제로는 스캔 오버레이(랜딩페이지)로 이동/재실행
      console.log('[보고사라][결과 페이지 스텁] "다른 제품 스캔하기" 클릭');
    });
    document.getElementById('back-btn').addEventListener('click', function () {
      // TODO: 실제로는 검색/스캔 진입 화면으로 이동
      console.log('[보고사라][결과 페이지 스텁] "다시 스캔" 클릭');
    });
  }

  // ---------------------------------------------------------
  // 부트스트랩
  // ---------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    bindActions();
    loadData()
      .then(render)
      .catch(function (err) {
        console.error('[보고사라][결과 페이지] 데이터 로드 실패', err);
        document.getElementById('prod-name').textContent = '데이터를 불러오지 못했어요.';
      });
  });
})();
