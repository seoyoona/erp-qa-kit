from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from erpqa.core.errors import ErpqaError, UsageError
from erpqa.core.module_paths import write_module_text, write_module_yaml
from erpqa.core.yaml_io import load_yaml
from erpqa.screen.extractors import (
    _norm,
    extract_backend_module,
    extract_frontend_feature,
    extract_spec_screen,
    resolve_backend_by_sps,
    resolve_backend_module,
    resolve_frontend_files,
    resolve_spec_file,
)

# Save-path fields that are commonly server-populated (audit / document number),
# so their absence in the frontend is flagged but always left for human review.
_LIKELY_SERVER_FIELDS = {"pg_no", "add_emp_no", "add_emp", "reg_emp_no", "aud", "ins_emp_no"}


_DYNAMIC_COL_RE = re.compile(r"^(spec|day)\d+$")


def _clean_key(param: str, alias_map: dict[str, str], alias_ci: dict[str, str]) -> str:
    # Prefer the backend alias bridge (exact, then case-insensitive) so that a
    # spec param like `IYMF` maps to `ym_from` via serialization_alias="iYMF".
    if param in alias_map:
        return alias_map[param]
    if param.lower() in alias_ci:
        return alias_ci[param.lower()]
    base = param[1:] if param[:1] in ("i", "I") and param[1:2].isupper() else param
    return re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower()


def _fe_has(clean: str, fe_keys: set[str]) -> bool:
    flat = {k.replace("_", "") for k in fe_keys}
    return clean in fe_keys or clean.replace("_", "") in flat


def _load_manifest(project_path: Path, module: str) -> dict:
    manifest = load_yaml(project_path / "qa-context" / "modules" / module / "module_manifest.yaml")
    return manifest if isinstance(manifest, dict) else {}


def _roots_from_manifest(project_path: Path, module: str, manifest: dict | None = None) -> dict[str, Path]:
    manifest = manifest if manifest is not None else _load_manifest(project_path, module)
    roots: dict[str, Path] = {}
    src = manifest.get("source_roots", {}) if isinstance(manifest.get("source_roots"), dict) else {}
    for kind in ("spec", "frontend", "backend"):
        rels = src.get(kind) or [f"extracted/{module}/{kind}"]
        rels = [rels] if isinstance(rels, str) else rels
        roots[kind] = (project_path / str(rels[0])).resolve()
    return roots


def _screen_binding(manifest: dict, screen_id: str) -> dict:
    """Explicit, maintained screen→source bindings override the SP/id heuristics
    for screens that share generic stored procedures (the 진행현황/PRG group),
    where heuristic resolution over-binds several screens onto one module. Shape::

        screen_bindings:
          PDT_PRG_003M: {backend: <path>, frontend: <path>}

    Keys are matched on the normalized screen id so `PDT-PRG-003M` / `PDT_PRG_003M`
    are equivalent. Paths are resolved relative to the matching source root, then
    the project root, then as an absolute path."""
    raw = manifest.get("screen_bindings")
    if not isinstance(raw, dict):
        return {}
    want = _norm(screen_id)
    for key, val in raw.items():
        if _norm(str(key)) == want and isinstance(val, dict):
            return val
    return {}


def _resolve_binding_path(value: object, *roots: Path) -> Path | None:
    if not value:
        return None
    for root in roots:
        cand = (root / str(value))
        if cand.exists():
            return cand.resolve()
    cand = Path(str(value))
    return cand.resolve() if cand.is_absolute() and cand.exists() else None


def _frontend_all_text(frontend_root: Path) -> str:
    """All frontend source as one NFC-normalized blob — Korean labels live across
    feature files, shared models, and header-config, so a label-presence check
    searches the whole slice, not just one screen's cluster."""
    parts: list[str] = []
    for ts in list(frontend_root.rglob("*.ts")) + list(frontend_root.rglob("*.tsx")):
        parts.append(ts.read_text(encoding="utf-8", errors="replace"))
    return unicodedata.normalize("NFC", "\n".join(parts))


def run_screen_audit(
    project_path: str | Path, module: str, screen_id: str, with_labels: bool = False
) -> dict:
    project_path = Path(project_path).resolve()
    if not (project_path / "qa-context" / "modules" / module).exists():
        raise ErpqaError(f"module {module} is not initialized; run `erpqa module-init` first")

    manifest = _load_manifest(project_path, module)
    roots = _roots_from_manifest(project_path, module, manifest)
    binding = _screen_binding(manifest, screen_id)
    spec_file = resolve_spec_file(roots["spec"], screen_id)
    if spec_file is None:
        raise ErpqaError(f"no spec xlsx found for screen {screen_id} under {roots['spec']}")

    spec = extract_spec_screen(spec_file, screen_id)
    # Resolve the backend, recording HOW it was bound so findings can be trusted
    # accordingly:
    #   explicit   — maintained screen_bindings entry (deterministic, 1:1)
    #   id-code    — screen-id matches a module dir (exact, or transposition-tolerant
    #                so PDT_PRG_003M -> pdt_pgr_003m; digits are in the multiset so
    #                003 never collides with 004)
    #   sp-fallback— specificity-weighted stored-proc matching; used only when the id
    #                does not map to a module. This is the one path that can over-bind
    #                screens sharing generic SPs (the 진행현황/PRG group), so findings
    #                derived from it are explicitly marked low-confidence below.
    sp_names = [sp["proc"] for sp in spec.sps]
    backend_dir = _resolve_binding_path(binding.get("backend"), roots["backend"], project_path)
    resolution_method = "explicit"
    if backend_dir is None:
        backend_dir = resolve_backend_module(roots["backend"], screen_id)
        resolution_method = "id-code"
    if backend_dir is None:
        backend_dir = resolve_backend_by_sps(roots["backend"], sp_names)
        resolution_method = "sp-fallback"
    if backend_dir is None:
        raise ErpqaError(f"no backend module found for screen {screen_id} under {roots['backend']}")
    resolution_uncertain = resolution_method == "sp-fallback"

    backend = extract_backend_module(backend_dir)
    alias_ci = {k.lower(): v for k, v in backend.alias_to_clean.items()}
    fe_feature_dir = _resolve_binding_path(binding.get("frontend"), roots["frontend"], project_path)
    fe_files, anchor, missing_shared = resolve_frontend_files(
        roots["frontend"], backend, screen_id, fe_feature_dir
    )
    frontend = extract_frontend_feature(fe_files, anchor)
    fe_keys = {k.lower() for k in frontend.zod_fields}

    findings: list[dict] = []
    save_params = spec.params_for_role("IU") + spec.params_for_role("I") + spec.params_for_role("U")
    filter_params = spec.params_for_role("S")
    matched: list[str] = []
    rel_spec = spec_file.name
    src_files = [rel_spec, _rel(backend_dir, project_path), _frontend_rel(frontend, project_path)]

    fe_all = fe_keys
    fe_filters = {k.lower() for k in frontend.filter_fields} or fe_all
    fe_columns = {k.lower() for k in frontend.column_fields} or fe_all
    # If the screen's zod model was not resolved into the cluster (e.g. shared
    # src/models/ was not included in the extracted slice), the frontend field
    # picture is incomplete. Emit ONE honest diagnostic instead of dozens of
    # false "missing" findings.
    fe_model_resolved = bool(frontend.zod_fields)

    # ---- dimension: search filters (조회) — spec S-proc input params are source of truth
    filter_matched: list[str] = []
    seen_f: set[str] = set()
    for param in filter_params:
        clean = _clean_key(param, backend.alias_to_clean, alias_ci)
        if clean in seen_f:
            continue
        seen_f.add(clean)
        if _fe_has(clean, fe_filters) or _fe_has(clean, fe_all):
            filter_matched.append(clean)
            continue
        if not fe_model_resolved:
            continue
        findings.append({
            "screen_id": screen_id, "module": module, "mismatch_type": "SearchFilterMissingInFrontend",
            "field": clean, "spec_param": param,
            "expected_from_source_of_truth": f"조회 SP 입력 파라미터 {param} (= {clean})",
            "actual_frontend": "프론트 검색필터에 없음",
            "severity": "MAJOR", "suggested_fix_type": "add-search-filter",
            "source_files": src_files, "confidence": "medium", "needs_human_confirmation": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": f"화면 {screen_id}: 명세 검색필터 `{clean}`(SP {param})가 프론트에 없음 → 추가 검토.",
        })

    # ---- info only: grid/result columns. Backend is *evidence*, not source of
    # truth, and grids legitimately show a subset of returned columns, so a
    # backend column absent from the frontend is NOT a defect — we report it as a
    # coverage statistic, never as a finding. (Real grid-column source of truth
    # lives in the spec screenshot/테이블정보 — a future image/vision dimension.)
    column_matched: list[str] = []
    dynamic_cols = [c for c in backend.result_columns if _DYNAMIC_COL_RE.match(c)]
    static_cols = [c for c in backend.result_columns if not _DYNAMIC_COL_RE.match(c)]
    column_only_in_backend: list[str] = []
    for clean in sorted(static_cols):
        if _fe_has(clean, fe_columns) or _fe_has(clean, fe_all):
            column_matched.append(clean)
        else:
            column_only_in_backend.append(clean)

    # 0) spec-coverage gap: the screen looks like a save/입력 screen (its name says
    # 등록/입력/작업보고, or the backend implements IU, or the frontend has a
    # create/update mutation) yet the spec carries NO save-SP (_IU) example, so the
    # save-field dimension could not be evaluated. Emit an honest notice instead of
    # silently reporting the save dimension as clean.
    # macOS stores Hangul filenames in NFD (decomposed); normalize to NFC so the
    # Korean save-screen tokens match regardless of filesystem normalization.
    spec_name = unicodedata.normalize("NFC", spec.source_file)
    name_says_save = any(tok in spec_name for tok in ("등록", "입력", "작업보고"))
    save_expected = (
        name_says_save
        or "IU" in backend.implemented_roles
        or bool(frontend.mutations & {"create", "update"})
    )
    if save_expected and not save_params:
        ev = []
        if name_says_save:
            ev.append("화면명")
        if "IU" in backend.implemented_roles:
            ev.append("백엔드 _IU 구현")
        if frontend.mutations & {"create", "update"}:
            ev.append("프론트 mutation")
        findings.append({
            "screen_id": screen_id, "module": module, "mismatch_type": "SaveSpecExampleMissing",
            "expected_from_source_of_truth": "명세 저장 SP(_IU) 예시 (exec ..._IU @param=)",
            "actual_spec": "명세에 저장 SP 예시 없음 → 저장 필드 비교를 수행하지 못함",
            "backend_evidence": f"저장 화면 추정 근거: {', '.join(ev)}",
            "severity": "MAJOR", "suggested_fix_type": "add-save-sp-example-to-spec",
            "source_files": [rel_spec, _rel(backend_dir, project_path)],
            "confidence": "medium", "needs_human_confirmation": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": (
                f"화면 {screen_id}: 저장 화면으로 보이나 명세 xlsx에 저장 SP(_IU) 예시가 없어 "
                "저장 필드 검증을 건너뜀(거짓 CLEAN 방지). 명세에 저장 SP 예시를 보강하거나, "
                "저장이 없는 조회전용 화면이면 사람이 확인 후 분류할 것."
            ),
        })

    # 1) capability gap: spec defines a save (IU) but backend has no IU implementation
    if save_params and "IU" not in backend.implemented_roles and not (backend.implemented_roles & {"I", "U"}):
        findings.append({
            "screen_id": screen_id, "module": module, "mismatch_type": "SaveCapabilityMissing",
            "expected_from_source_of_truth": f"저장(IU) 정의됨: {spec.sps and '예'}",
            "actual_backend": "백엔드에 _IU 구현 없음",
            "severity": "BLOCKER", "suggested_fix_type": "implement-save-endpoint",
            "source_files": [rel_spec, _rel(backend_dir, project_path)],
            "confidence": "medium", "needs_human_confirmation": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": f"화면 {screen_id} 저장 기능이 명세에 있으나 백엔드 _IU 구현이 없음. 저장 엔드포인트 구현 검토.",
        })

    # 2) per save-field: present in spec save but missing in frontend?
    for param in save_params:
        clean = _clean_key(param, backend.alias_to_clean, alias_ci)
        if _fe_has(clean, fe_keys):
            matched.append(clean)
            continue
        likely_server = clean in _LIKELY_SERVER_FIELDS
        if not fe_model_resolved:
            continue
        findings.append({
            "screen_id": screen_id, "module": module, "mismatch_type": "MissingInFrontend",
            "field": clean, "spec_param": param,
            "expected_from_source_of_truth": f"저장 SP 파라미터 {param} (= {clean})",
            "actual_frontend": "프론트 모델/입력에 없음",
            "backend_evidence": "alias 매핑 있음" if param in backend.alias_to_clean else "추정 매핑(휴리스틱)",
            "severity": "MINOR" if likely_server else "MAJOR",
            "suggested_fix_type": "add-or-confirm-server-populated-field" if likely_server else "add-frontend-field",
            "source_files": [rel_spec, _rel(backend_dir, project_path), _frontend_rel(frontend, project_path)],
            "confidence": "low" if likely_server else "medium",
            "needs_human_confirmation": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": (
                f"화면 {screen_id}: 명세 저장 필드 `{clean}`(SP {param})가 프론트에 없음. "
                + ("서버 자동입력(감사/전표번호) 가능성 → 사람 확인 후 결정."
                   if likely_server else "프론트 입력/모델에 추가 검토.")
            ),
        })

    # ---- dimension: visible labels (opt-in vision). The screen-layout screenshot
    # in the spec carries Korean field labels that exist nowhere in cell text. Read
    # them on-device for free (macOS Vision OCR) and check each against the whole
    # frontend slice: a label shown in the spec whose Korean string appears nowhere
    # in the frontend is a candidate dropped field. OCR is noisy, so every such
    # finding is low-confidence and human-confirmed.
    labels_dim: dict | None = None
    if with_labels:
        from erpqa.screen import vision

        workdir = project_path / "qa-context" / "modules" / module / "screens" / screen_id / "spec_images"
        labels, lmeta = vision.extract_spec_labels(spec_file, workdir)
        fe_text = _frontend_all_text(roots["frontend"])
        label_matched: list[str] = []
        for label in labels:
            norm = unicodedata.normalize("NFC", label)
            if norm in fe_text or norm.replace(" ", "") in fe_text.replace(" ", ""):
                label_matched.append(label)
                continue
            if not lmeta["ocr_available"]:
                continue
            findings.append({
                "screen_id": screen_id, "module": module, "mismatch_type": "LabelMissingInFrontend",
                "field": label,
                "expected_from_source_of_truth": f"명세 화면 스크린샷에 보이는 라벨 `{label}`",
                "actual_frontend": "프론트 슬라이스 어디에서도 해당 한글 문자열을 찾지 못함",
                "severity": "MINOR", "suggested_fix_type": "add-or-confirm-screen-label",
                "source_files": [rel_spec, _frontend_rel(frontend, project_path)],
                "confidence": "low", "needs_human_confirmation": True,
                "frontend_override_forbidden": True,
                "ai_fix_instruction": (
                    f"화면 {screen_id}: 명세 스크린샷의 라벨 `{label}`이 프론트 슬라이스에 없음. "
                    "OCR 오탐 가능성 있으니 사람이 스크린샷과 대조 후 누락 라벨인지 확인할 것."
                ),
            })
        labels_dim = {
            "source": len(labels),
            "matched": len(label_matched),
            "labels": labels,
            "matched_labels": label_matched,
            **lmeta,
        }

    # Copy-step rule enforcement: a seed file imports shared @/models or @/adapters
    # that are NOT in the extracted slice (only feature-*/ was copied). This is the
    # precise, actionable cause behind most FrontendModelUnresolved cases — name the
    # exact missing imports so the slice can be re-extracted correctly.
    if missing_shared:
        sample = ", ".join(sorted(missing_shared)[:8])
        findings.append({
            "screen_id": screen_id, "module": module, "mismatch_type": "FrontendSliceIncomplete",
            "expected_from_source_of_truth": "공유 `src/models/` + `src/adapters/` 포함된 프론트 슬라이스",
            "actual_frontend": f"슬라이스에 없는 공유 import {len(missing_shared)}건: {sample}",
            "severity": "MAJOR", "suggested_fix_type": "re-extract-include-shared-models-and-adapters",
            "source_files": src_files, "confidence": "high", "needs_human_confirmation": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": (
                f"화면 {screen_id}: 프론트 슬라이스가 `feature-*/`만 포함하고 공유 "
                "`src/models/`·`src/adapters/`를 빠뜨림 → 위 import가 해소되지 않아 필드 비교가 불완전함. "
                "copy-step 규칙대로 공유 모듈을 포함해 재추출 후 다시 실행할 것."
            ),
        })

    if not fe_model_resolved:
        findings.append({
            "screen_id": screen_id, "module": module, "mismatch_type": "FrontendModelUnresolved",
            "expected_from_source_of_truth": "프론트 zod 모델 필드",
            "actual_frontend": "클러스터에서 모델을 찾지 못함 (공유 src/models/ 가 추출 슬라이스에 없을 가능성)",
            "severity": "MAJOR", "suggested_fix_type": "re-extract-include-shared-models",
            "source_files": src_files, "confidence": "high", "needs_human_confirmation": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": (
                f"화면 {screen_id}: 프론트 모델이 슬라이스에 없어 필드/필터/컬럼 비교를 생략함. "
                "공유 `src/models/`를 포함해 프론트를 재추출 후 다시 실행 필요. "
                "(거짓 'missing' 방지를 위해 비교를 의도적으로 건너뜀.)"
            ),
        })

    # Honesty guard: when the backend was bound via the specificity-weighted SP
    # fallback (no id-code or explicit binding), the screen may have over-bound to
    # a module it shares a generic procedure with — exactly the unreliable
    # 진행현황/PRG case. Downgrade every finding's confidence and flag it, and emit
    # one notice so a reviewer knows to pin an explicit screen_binding before
    # trusting these findings.
    if resolution_uncertain:
        for f in findings:
            f["confidence"] = "low"
            f["resolution_uncertain"] = True
        findings.insert(0, {
            "screen_id": screen_id, "module": module, "mismatch_type": "ScreenResolutionLowConfidence",
            "expected_from_source_of_truth": "고유/primary SP 또는 명시적 screen_binding으로 1:1 결합",
            "actual_backend": f"공통 SP 가중 매칭으로 추정 결합: {_rel(backend_dir, project_path)}",
            "severity": "MAJOR", "suggested_fix_type": "pin-explicit-screen-binding",
            "source_files": [rel_spec, _rel(backend_dir, project_path)],
            "confidence": "low", "needs_human_confirmation": True, "resolution_uncertain": True,
            "frontend_override_forbidden": True,
            "ai_fix_instruction": (
                f"화면 {screen_id}: 백엔드가 화면ID가 아닌 공통 SP 매칭(sp-fallback)으로 결합됨 → "
                "여러 화면이 같은 모듈로 오결합됐을 수 있음. module_manifest.yaml의 "
                "`screen_bindings`에 이 화면의 backend/frontend 경로를 명시한 뒤 재실행하여 검증할 것. "
                "그 전까지 아래 findings는 신뢰 불가."
            ),
        })

    return {
        "screen_id": screen_id, "module": module,
        "spec_file": rel_spec,
        "frontend_model_resolved": fe_model_resolved,
        "resolution": {
            "method": resolution_method,
            "uncertain": resolution_uncertain,
            "confidence": "low" if resolution_uncertain else "high",
        },
        "backend_module": _rel(backend_dir, project_path),
        "frontend_anchor": _frontend_rel(frontend, project_path),
        "dimensions": {
            "save_fields": {"source": len(save_params), "matched": len(matched), "matched_fields": matched},
            "search_filters": {"source": len(seen_f), "matched": len(filter_matched), "matched_fields": filter_matched},
            "grid_columns": {"source": len(static_cols), "matched": len(column_matched),
                             "only_in_backend": len(column_only_in_backend), "dynamic_skipped": len(dynamic_cols),
                             "note": "info only — backend is evidence, not a defect signal"},
            **({"labels": labels_dim} if labels_dim is not None else {}),
        },
        "backend_implemented_roles": sorted(backend.implemented_roles),
        "frontend_mutations": sorted(frontend.mutations),
        "findings": findings,
        "memory_read": _memory_read(project_path, module),
    }


def _rel(p: Path, project_path: Path) -> str:
    try:
        return str(p.resolve().relative_to(project_path))
    except ValueError:
        return str(p)


def _frontend_rel(frontend, project_path: Path) -> str:
    return _rel(Path(frontend.feature_dir), project_path) if frontend.feature_dir else "(frontend cluster)"


def _memory_read(project_path: Path, module: str) -> dict:
    qa = project_path / "qa-context"
    return {
        "project_memory_read": (qa / "project_memory.md").exists(),
        "module_memory_read": (qa / "modules" / module / "module_memory.md").exists(),
    }


def write_screen_audit(
    project_path: str | Path, module: str, screen_id: str, with_labels: bool = False
) -> tuple[Path, Path]:
    result = run_screen_audit(project_path, module, screen_id, with_labels=with_labels)
    rel = f"screens/{screen_id}"
    contract = write_module_yaml(project_path, module, f"{rel}/screen_audit.yaml", result)
    report = write_module_text(project_path, module, f"{rel}/screen_audit_report.md", _render(result))
    return contract, report


def _render(r: dict) -> str:
    L = [f"# Screen Audit — {r['screen_id']} ({r['module']})", ""]
    L.append("Frontend는 검사 대상(implementation under test). 화면설계서(SP 파라미터)+백엔드 증거가 source of truth.")
    L.append("")
    L.append("## Policy / Memory Read")
    L.append(f"- project_memory_read: {r['memory_read']['project_memory_read']}")
    L.append(f"- module_memory_read: {r['memory_read']['module_memory_read']}")
    L.append("")
    L.append("## Sources Resolved")
    res = r.get("resolution", {})
    method = res.get("method", "?")
    conf = res.get("confidence", "?")
    warn = " ⚠️ 휴리스틱 결합 — 명시적 screen_binding 권장" if res.get("uncertain") else ""
    L.append(f"- resolution: `{method}` (신뢰도: {conf}){warn}")
    L.append(f"- spec: `{r['spec_file']}`")
    L.append(f"- backend: `{r['backend_module']}` (구현된 SP roles: {', '.join(r['backend_implemented_roles']) or '없음'})")
    L.append(f"- frontend: `{r['frontend_anchor']}` (mutations: {', '.join(r['frontend_mutations']) or '없음'})")
    L.append("")
    d = r["dimensions"]
    L.append("## Coverage (차원별 일치율)")
    L.append("| 차원 | 정답지 출처 | 항목 수 | 매칭 |")
    L.append("|---|---|---|---|")
    L.append(f"| 저장 필드 | 명세 저장 SP(IU) | {d['save_fields']['source']} | {d['save_fields']['matched']} |")
    L.append(f"| 검색 필터 | 명세 조회 SP(S) 입력 | {d['search_filters']['source']} | {d['search_filters']['matched']} |")
    L.append(f"| 그리드 컬럼 | 백엔드 조회결과(증거) | {d['grid_columns']['source']} | {d['grid_columns']['matched']} |")
    if "labels" in d:
        ld = d["labels"]
        L.append(f"| 화면 라벨(OCR) | 명세 스크린샷 | {ld['source']} | {ld['matched']} |")
    L.append(f"- 총 findings(확인필요 포함): **{len(r['findings'])}**")
    if "labels" in d:
        ld = d["labels"]
        eng = f"{ld['ocr_engine']}" + ("" if ld["ocr_available"] else " (사용불가 — OCR 생략)")
        L.append(f"- 라벨 OCR 엔진: {eng}; 읽은 이미지 {len(ld['images_read'])}개"
                 + (f", 건너뜀 {len(ld['images_skipped'])}개(EMF/WMF)" if ld["images_skipped"] else ""))
        if ld["labels"]:
            L.append(f"- 인식 라벨: {', '.join(ld['labels'])}")
    if d["save_fields"]["matched_fields"]:
        L.append(f"- 저장 매칭 필드: {', '.join(d['save_fields']['matched_fields'])}")
    if d["search_filters"]["matched_fields"]:
        L.append(f"- 검색필터 매칭: {', '.join(d['search_filters']['matched_fields'])}")
    L.append("")
    L.append("## Findings")
    if not r["findings"]:
        L.append("- (없음)")
    for i, f in enumerate(r["findings"], 1):
        L.append(f"### Finding {i}: {f['mismatch_type']}" + (f" — `{f.get('field','')}`" if f.get("field") else ""))
        for key in ("screen_id", "module", "mismatch_type", "field", "spec_param",
                    "expected_from_source_of_truth", "actual_frontend", "actual_backend",
                    "actual_spec", "backend_evidence", "source_files", "confidence", "resolution_uncertain",
                    "needs_human_confirmation", "severity", "suggested_fix_type",
                    "frontend_override_forbidden", "ai_fix_instruction"):
            if key in f:
                L.append(f"- {key}: {f[key]}")
        L.append("")
    L.append("## 사람 확인 필요 (needs_human_confirmation)")
    for f in r["findings"]:
        if f.get("needs_human_confirmation"):
            L.append(f"- [{f['severity']}] {f.get('field', f['mismatch_type'])}: {f['ai_fix_instruction']}")
    return "\n".join(L) + "\n"
