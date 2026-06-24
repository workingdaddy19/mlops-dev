# mlops 포탈 — k8s Secret 설정 요청 (인프라팀)

포탈 앱은 **비밀이 아닌 설정은 앱 코드 기본값 + DB(`system_settings`, 관리자 Settings 화면)** 에서 관리합니다.
따라서 k8s Secret에는 **DB에 담을 수 없는 부트스트랩 + 순수 자격증명(계정·비밀번호·토큰)만** 필요합니다.

> 인프라팀에 요청드리는 것: 아래 **8개 키**를 담은 `Secret`을 `mlops` 네임스페이스에 생성/적용해 주세요.
> (비밀이 아닌 AWS 리전 등은 앱 Deployment에 일반 env로 이미 포함되어 있어 별도 요청 불필요)

---

## 1. 적용할 Secret (운영)

`backend-secret.yaml` (실제 값으로 `<...>` 치환):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: mlops
type: Opaque
stringData:
  DB_HOST: "<RDS_ENDPOINT>"
  DB_PORT: "5432"
  DB_NAME: "mlops"
  DB_USER: "mlops"
  DB_PASSWORD: "<DB_PASSWORD>"
  APP_SECRET_KEY: "<RANDOM_APP_SECRET_KEY>"
  JUPYTERHUB_ADMIN_TOKEN: "<JUPYTERHUB_ADMIN_TOKEN>"
  JUPYTERHUB_JWT_SECRET: "<JUPYTERHUB_JWT_SECRET>"
```

## 2. 키 설명

| 키 | 설명 | 비밀? | 담당 |
|----|------|:----:|------|
| `DB_HOST` | RDS PostgreSQL 엔드포인트 | 부분 | 인프라/DBA |
| `DB_PORT` | 기본 `5432` | X | 인프라 |
| `DB_NAME` | DB명 `mlops` (dev도 동일 DB 공유) | X | 인프라 |
| `DB_USER` | DB 계정 `mlops` | 계정 | 인프라/DBA |
| `DB_PASSWORD` | DB 비밀번호 | **비밀** | 인프라/DBA |
| `APP_SECRET_KEY` | 앱 마스터 키(비밀번호 해시·JWT salt) | **비밀** | 앱팀(고정값 유지) |
| `JUPYTERHUB_ADMIN_TOKEN` | JupyterHub Admin API 토큰 | **비밀** | JupyterHub 관리자 |
| `JUPYTERHUB_JWT_SECRET` | JupyterHub JWT SSO 시크릿 | **비밀** | JupyterHub 관리자 |

## 3. ⚠️ 중요 주의사항

- **`APP_SECRET_KEY`는 절대 임의로 바꾸지 마세요.** 이 값으로 기존 사용자 비밀번호 해시가 만들어져 있어, 변경 시 **전 사용자 로그인 불가**(전원 비밀번호 재설정 필요). 신규 생성이 꼭 필요하면 앱팀과 사전 협의. 신규값 생성은 `openssl rand -hex 32`.
  - 참고: `APP_SECRET_KEY`는 기존 `SECRET_KEY`를 이름만 명확히 한 것입니다(역할: 비밀번호 해시 pepper + JWT 서명). 앱은 **두 이름 모두 인식**(`APP_SECRET_KEY` 우선)하므로, 기존 `SECRET_KEY` 키가 있는 Secret도 그대로 동작합니다.
- **`JUPYTERHUB_JWT_SECRET`은 JupyterHub 측 `jupyterhub_config.py`의 값과 동일**해야 SSO가 동작합니다.
- **개발(dev)도 동일 `mlops` DB를 공유**합니다. 그래서 dev Secret(`backend-secret-dev`)은 **이 8개 값과 동일**(특히 `APP_SECRET_KEY` 동일)하게 두면 됩니다. → `k8s/dev/backend-secret-dev.example.yaml` 참고.
- 실제 값이 든 Secret 파일(`backend-secret.yaml`, `backend-secret-dev.yaml`)은 `.gitignore`로 **저장소에 커밋되지 않습니다.**

## 4. 적용 명령

```bash
# 값 채운 뒤
kubectl apply -f backend-secret.yaml -n mlops
# (개발) kubectl apply -f dev/backend-secret-dev.yaml -n mlops

# Pod에 반영(env는 재시작 시 주입)
kubectl rollout restart deployment/mlops -n mlops
# (개발) kubectl rollout restart deployment/mlops-dev -n mlops
```

> 참고: `kubectl apply`는 이전 Secret에 있던 불필요한 키(과거 URL/리전/버킷 등)를 자동 제거합니다.
> 비밀이 아닌 서비스 설정(MLflow/Jupyter/Athena/S3 URL·리전·버킷)은 앱이 코드 기본값/DB에서 읽으므로 Secret에 넣지 않습니다.

## 5. 비밀 회전(rotate) 권장

`DB_PASSWORD`, `JUPYTERHUB_*` 토큰은 과거 노출 이력이 있을 수 있어 **주기적 회전**을 권장합니다.
(`APP_SECRET_KEY` 회전은 위 주의사항대로 전 사용자 영향 → 계획된 점검 시에만)
