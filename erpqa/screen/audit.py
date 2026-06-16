from __future__ import annotations

import re
from pathlib import Path

from erpqa.core.errors import ErpqaError, UsageError
from erpqa.core.module_paths import write_module_text, write_module_yaml
from erpqa.core.yaml_io import load_yaml
from erpqa.screen.extractors import (
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


def _roots_from_manifest(project_path: Path, module: str) -> dict[str, Path]:
    manifest = load_yaml(project_path / "qa-context" / "modules" / module / "module_manifest.yaml")
    roots: dict[str, Path] = {}
    src = (manifest or {}).get("source_roots", {}) if isinstance(manifest, dict) else {}
    for kind in ("spec", "frontend", "backend"):
        rels = src.get(kind) or [f"extracted/{module}/{kind}"]
        rels = [rels] if isinstance(rels, str) else rels
        roots[kind] = (project_path / str(rels[0])).resolve()
    return roots


def run_screen_audit(project_path: str | Path, module: str, screen_id: str) -> dict:
    project_path = Path(project_path).resolve()
    if not (project_path / "qa-context" / "modules" / module).exists():
        raise ErpqaError(f"module {module} is not initialized; run `erpqa module-init` first")

    roots = _roots_from_manifest(project_path, module)
    spec_file = resolve_spec_file(roots["spec"], screen_id)
    if spec_file is None:
        raise ErpqaError(f"no spec xlsx found for screen {screen_id} under {roots['spec']}")

    spec = extract_spec_screen(spec_file, screen_id)
    # Resolve backend by the screen-id code first (exact, then transposition-tolerant
    # so PDT_PRG_003M -> pdt_pgr_003m), then fall back to specificity-weighted SP
    # matching for screens whose id does not map to a module.
    sp_names = [sp["proc"] for sp in spec.sps]
    backend_dir = resolve_backend_module(roots["backend"], screen_id) or resolve_backend_by_sps(roots["backend"], sp_names)
    if backend_dir is None:
        raise ErpqaError(f"no backend module found for screen {screen_id} under {roots['backend']}")

    backend = extract_backend_module(backend_dir)
    alias_ci = {k.lower(): v for k, v in backend.alias_to_clean.items()}
    fe_files, anchor = resolve_frontend_files(roots["frontend"], backend, screen_id)
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

    return {
        "screen_id": screen_id, "module": module,
        "spec_file": rel_spec,
        "frontend_model_resolved": fe_model_resolved,
        "backend_module": _rel(backend_dir, project_path),
        "frontend_anchor": _frontend_rel(frontend, project_path),
        "dimensions": {
            "save_fields": {"source": len(save_params), "matched": len(matched), "matched_fields": matched},
            "search_filters": {"source": len(seen_f), "matched": len(filter_matched), "matched_fields": filter_matched},
            "grid_columns": {"source": len(static_cols), "matched": len(column_matched),
                             "only_in_backend": len(column_only_in_backend), "dynamic_skipped": len(dynamic_cols),
                             "note": "info only — backend is evidence, not a defect signal"},
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


def write_screen_audit(project_path: str | Path, module: str, screen_id: str) -> tuple[Path, Path]:
    result = run_screen_audit(project_path, module, screen_id)
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
    L.append(f"- 총 findings(확인필요 포함): **{len(r['findings'])}**")
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
                    "backend_evidence", "source_files", "confidence", "needs_human_confirmation",
                    "severity", "suggested_fix_type", "frontend_override_forbidden", "ai_fix_instruction"):
            if key in f:
                L.append(f"- {key}: {f[key]}")
        L.append("")
    L.append("## 사람 확인 필요 (needs_human_confirmation)")
    for f in r["findings"]:
        if f.get("needs_human_confirmation"):
            L.append(f"- [{f['severity']}] {f.get('field', f['mismatch_type'])}: {f['ai_fix_instruction']}")
    return "\n".join(L) + "\n"
