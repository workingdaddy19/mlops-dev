# Plan — Models: Experiments & Pipelines 통합 페이지

## Executive Summary

| 항목 | 내용 |
|------|------|
| Feature | `experiments-pipelines` — Models 하위 MLflow 메뉴를 "Experiments & Pipelines" 통합 페이지로 개편 |
| 작성일 | 2026-06-24 |
| 범위 | 메뉴 1개 리네임 + 페이지 1개 개편 + 설정키 2개 신설(KFP/Katib) |
| 영향 파일(예상) | 6 (config, system_settings, settings_service, web.py, base.html, 템플릿) |

**Value Delivered (4-perspective)**

| 관점 | 내용 |
|------|------|
| Problem | MLflow만 메뉴로 있고, 새로 도입한 Kubeflow Pipelines(KFP)·Katib(HPO)로의 진입점이 포탈에 없음 |
| Solution | 기존 MLflow 메뉴를 "Experiments & Pipelines" 한 페이지로 통합, 3개 외부도구 "열기" 카드 제공 |
| Function·UX Effect | 모델 실험·파이프라인·튜닝 도구를 한곳에서 새 탭으로 진입. 사이드바 항목은 그대로(1개) 유지 |
| Core Value | ML 워크플로 도구 진입점 일원화 + URL은 코드기본값+DB(Settings)로 무재배포 관리 |

---

## 1. 배경 / 문제

- 현재 Models 메뉴: `MLFlow`(/aiml/mlflow), `Inference Test`, `Airflow`.
- MLflow 페이지는 "MLFlow 열기" 단일 카드(새 탭) + 헬스 배지 + `mlflow` 권한 게이팅 구조.
- 신규 도구 **Kubeflow Pipelines(KFP)**, **Katib(하이퍼파라미터 튜닝)** 진입점이 없음.
- 사용자 결정: 메뉴를 늘리지 않고 **단일 통합 페이지 "Experiments & Pipelines"** 로 3개 링크 제공.

## 2. 목표 / 비목표

**목표**
- Models 하위 `MLFlow` 메뉴 → **`Experiments & Pipelines`** 로 리네임(항목 수 유지).
- 해당 페이지에 3개 "열기" 카드 제공:
  1. **Model Experiments** → MLflow `http://mlflow.mlops.click/` (기존)
  2. **Model Pipeline** → KFP `http://kfp.kubeflow.mlops.click/` (신규)
  3. **Hyperparameter Tuning** → Katib `http://katib.kubeflow.mlops.click/katib/` (신규)
- 3개 URL은 **하드코딩 금지** — `config.py` 기본값 + DB(`system_settings`, 관리자 Settings 화면)에서 관리(최근 설정 리팩터 방침 준수).

**비목표 (Out of scope)**
- Kubeflow/Katib 자체 배포·인그레스·DNS(인프라 영역). 포탈은 **링크 진입만** 제공.
- KFP/Katib로의 SSO(각 도구가 자체 인증). 본 작업은 새 탭 오픈까지.
- KFP/Katib 상태(health) 체크 — v1에서는 MLflow만 기존 헬스 유지, 신규 2개는 링크만(후속 옵션).

## 3. 설계

### 3.1 메뉴 (base.html)
- Models `sidebar-sub` 의 `MLFlow` 항목:
  - label: `MLFlow` → `Experiments & Pipelines`
  - href: `/aiml/mlflow` → `/aiml/experiments` (active_page: `experiments`)
  - 아이콘: 🧪 유지(또는 📈)
- `Inference Test`, `Airflow` 항목 변경 없음.

### 3.2 페이지 (templates)
- `pages/mlflow.html` → `pages/experiments.html` 로 개편(또는 신규 후 기존 제거).
- 단일 카드 → **3개 카드 그리드**. 각 카드: 아이콘 · 제목 · URL 텍스트 · "열기" 버튼(`window.open(url, '_blank')`).
- 권한 게이팅: 기존과 동일하게 **`mlflow` 권한** 재사용(통합 페이지 1개 → 권한 1개). 권한 없으면 버튼 비활성 + 안내.
  - (대안/후속: `kubeflow`·`katib` 세분화 권한 신설 — 본 plan에서는 단순화 위해 `mlflow` 재사용)
- 하단 "사용 안내" 카드 유지(문구만 갱신).

### 3.3 설정 (config + DB)
- `app/core/config.py`: 신설
  - `kfp_base_url: str = Field(default="http://kfp.kubeflow.mlops.click/", alias="KFP_BASE_URL")`
  - `katib_base_url: str = Field(default="http://katib.kubeflow.mlops.click/katib/", alias="KATIB_BASE_URL")`
  - (`mlflow_base_url` 기존 유지)
- `app/models/system_settings.py` `SETTINGS_SEED`: `KFP_BASE_URL`, `KATIB_BASE_URL` 추가(group 예: `models`), `MLFLOW_BASE_URL` 기존 유지. → 관리자 Settings 화면에서 수정 가능.
- `app/services/settings_service.py` `_env_fallback`: `KFP_BASE_URL`, `KATIB_BASE_URL`, `MLFLOW_BASE_URL` 매핑 추가(DB→env 폴백).
- `admin_settings.html` `GROUP_LABELS`: `models: '📈 Models'` 추가(신규 group 사용 시).

### 3.4 라우트 (web.py)
- `/aiml/mlflow` → `/aiml/experiments` (active_page `experiments`), 템플릿 `experiments.html`.
- 라우트에서 **SettingsService로 3개 URL을 읽어** 템플릿에 전달:
  - `mlflow_url = svc.get("MLFLOW_BASE_URL", settings.mlflow_base_url)`
  - `kfp_url   = svc.get("KFP_BASE_URL",   settings.kfp_base_url)`
  - `katib_url = svc.get("KATIB_BASE_URL", settings.katib_base_url)`
- 기존 `/api/mlflow/*`(experiments/health) 엔드포인트는 그대로 유지(MLflow 카드 헬스용).

## 4. 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `app/core/config.py` | KFP/Katib URL 필드 신설 |
| `app/models/system_settings.py` | SETTINGS_SEED에 KFP/Katib URL 추가 |
| `app/services/settings_service.py` | _env_fallback 매핑 추가 |
| `app/api/routes/web.py` | 라우트 리네임 + 3개 URL 전달 |
| `app/templates/base.html` | Models 메뉴 라벨/href 변경 |
| `app/templates/pages/experiments.html` | (mlflow.html 개편) 3개 카드 |
| `app/templates/pages/admin_settings.html` | (선택) models 그룹 라벨 |

## 5. 수용 기준 (Acceptance Criteria)

- [ ] 사이드바 Models 하위에 `Experiments & Pipelines` 1개 항목(MLflow 대체), 나머지 2개 유지.
- [ ] 페이지에 3개 "열기" 카드 노출, 각 버튼이 올바른 URL을 **새 탭**으로 연다.
- [ ] 3개 URL이 `config.py` 기본값으로 동작하고, 관리자 Settings 화면에서 수정 시 즉시 반영(무재배포).
- [ ] `mlflow` 권한 없는 사용자는 "열기" 버튼 비활성 + 안내.
- [ ] 앱 import/기동 정상, 기존 `/api/mlflow/*` 동작 유지.

## 6. 리스크 / 메모

- KFP/Katib URL(`kfp.kubeflow.mlops.click`, `katib.kubeflow.mlops.click`)의 **DNS/인그레스는 인프라가 사전 구성**되어 있어야 링크가 동작(포탈은 링크만).
- 권한을 `mlflow` 재사용 → 추후 도구별 접근 통제가 필요하면 `kubeflow`/`katib` feature 신설(권한 신청 워크플로 재사용 가능).
- 라우트 경로 변경(`/aiml/mlflow`→`/aiml/experiments`): 외부 북마크 영향 적음(내부 메뉴). 필요 시 기존 경로 301 리다이렉트 추가 옵션.

## 7. 다음 단계

- 본 Plan 승인 → 구현(Do). 소규모라 Design 문서는 생략 가능(원하면 `/pdca design experiments-pipelines`).
