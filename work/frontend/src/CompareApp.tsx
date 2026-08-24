import { useEffect, useState } from 'react';
import ResultCard from './components/ResultCard';
import { mapDetailToIngredientResult, type ApiProductDetail } from './api';
import type { IngredientResult } from './data/ingredientResult';
import './ResultView.css';
import './CompareView.css';

/**
 * LLM 모델 비교 화면 — 실제 성분 요약 결과 페이지(ResultCard)를 그대로 재사용해서 좌우로
 * 나란히 띄운다. DB에서 오는 부분(성분 카드/배지/배합목적/relations)은 두 쪽 다 동일하고,
 * `scripts/generate_compare.py`가 덮어쓴 LLM 생성 부분(요약/설명/궁합팁)만 모델별로 다르다.
 *
 * 데이터 출처: `public/eval/compare_{productId}_{modelSlug}.json` (generate_compare.py가
 * `work/3366_project/eval/`과 함께 이곳에도 같은 내용을 저장한다) — 백엔드 서버 없이도 뜬다.
 */

interface CompareProduct {
  id: string;
  label: string;
}

// 새 제품/모델로 비교를 넓히려면 여기만 추가하면 된다 (파일명 규칙은 generate_compare.py와 동일).
const PRODUCTS: CompareProduct[] = [
  { id: 'p-69250fe7725a', label: '아누아 피디알엔 히알루론산 세럼' },
  { id: 'p-73a62005295a', label: '디오디너리 레티놀 0.5% 인 스쿠알란' },
];

const MODELS = ['gemma2:2b', 'qwen2.5:3b'];

function slugifyModel(model: string): string {
  return model.replace(/:/g, '-').replace(/\//g, '-');
}

interface EvalFile {
  product_id: string;
  model: string;
  generated_at: string;
  total_elapsed_seconds: number;
  detail: ApiProductDetail;
}

type SideState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'done'; result: IngredientResult; elapsedSeconds: number };

function useCompareData(productId: string, model: string): SideState {
  const [state, setState] = useState<SideState>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });

    fetch(`/eval/compare_${productId}_${slugifyModel(model)}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<EvalFile>;
      })
      .then((data) => {
        if (cancelled) return;
        setState({
          status: 'done',
          result: mapDetailToIngredientResult(data.detail),
          elapsedSeconds: data.total_elapsed_seconds,
        });
      })
      .catch((err) => {
        console.error('[모델 비교] 결과 파일 로드 실패', err);
        if (!cancelled) setState({ status: 'error' });
      });

    return () => {
      cancelled = true;
    };
  }, [productId, model]);

  return state;
}

function CompareSide({ productId, model }: { productId: string; model: string }) {
  const state = useCompareData(productId, model);

  return (
    <div className="compare-side">
      <div className="compare-side-header">
        <span className="compare-model-name">{model}</span>
        {state.status === 'done' && (
          <span className="compare-elapsed">응답 {state.elapsedSeconds.toFixed(1)}초</span>
        )}
      </div>

      {state.status === 'loading' && <p className="compare-status">불러오는 중...</p>}
      {state.status === 'error' && (
        <p className="compare-status compare-status--error">
          결과 파일을 못 찾았습니다 — scripts/generate_compare.py로 먼저 생성해주세요.
        </p>
      )}
      {state.status === 'done' && (
        <ResultCard product={state.result.product} ingredients={state.result.ingredients} isScan={false} />
      )}
    </div>
  );
}

export default function CompareApp() {
  const [productIndex, setProductIndex] = useState(0);
  const product = PRODUCTS[productIndex];

  return (
    <div className="result-view compare-view">
      <header className="compare-header">
        <h1 className="compare-title">LLM 모델 비교 — {product.label}</h1>
        <div className="compare-product-toggle">
          {PRODUCTS.map((p, i) => (
            <button
              key={p.id}
              type="button"
              className={`compare-toggle-btn${i === productIndex ? ' is-active' : ''}`}
              onClick={() => setProductIndex(i)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </header>

      <div className="compare-grid">
        {MODELS.map((model) => (
          <CompareSide key={model} productId={product.id} model={model} />
        ))}
      </div>
    </div>
  );
}
