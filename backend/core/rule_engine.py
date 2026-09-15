"""Rule Engine - loads YAML rule-packs, evaluates boolean checks. No eval()."""
from __future__ import annotations
import ast, operator, os
from pathlib import Path
from typing import Any
import yaml
from backend.logging_setup import get_logger

log = get_logger("rules")
RULE_PACK_DIR = Path(__file__).resolve().parents[2] / "rule_packs"
_BIN = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul,
        ast.Div:operator.truediv, ast.Mod:operator.mod}
_CMP = {ast.Eq:operator.eq, ast.NotEq:operator.ne, ast.Lt:operator.lt,
        ast.LtE:operator.le, ast.Gt:operator.gt, ast.GtE:operator.ge}
_BOOL = {ast.And:all, ast.Or:any}


def _ev(n, ctx):
    if isinstance(n, ast.Expression): return _ev(n.body, ctx)
    if isinstance(n, ast.Constant):   return n.value
    if isinstance(n, ast.Name):
        if n.id in ("True","true"): return True
        if n.id in ("False","false"): return False
        return ctx.get(n.id)
    if isinstance(n, ast.BoolOp): return _BOOL[type(n.op)](_ev(v, ctx) for v in n.values)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not): return not _ev(n.operand, ctx)
    if isinstance(n, ast.BinOp): return _BIN[type(n.op)](_ev(n.left, ctx), _ev(n.right, ctx))
    if isinstance(n, ast.Compare):
        left = _ev(n.left, ctx)
        for op, comp in zip(n.ops, n.comparators):
            right = _ev(comp, ctx)
            if not _CMP[type(op)](left, right): return False
            left = right
        return True
    raise ValueError("unsupported expression")


def safe_eval(expr: str, ctx: dict[str, Any]) -> Any:
    return _ev(ast.parse(expr, mode="eval"), ctx)


def load_packs(directory: Path | None = None) -> list[dict[str, Any]]:
    directory = directory or RULE_PACK_DIR
    out = []
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".yaml"):
            d = yaml.safe_load((directory / fn).read_text(encoding="utf-8")) or {}
            if d.get("rules") is not None: out.append(d)
    return out


def evaluate(context, doc_type="RFP", directory=None) -> list[dict[str, Any]]:
    findings = []
    for pack in load_packs(directory):
        for rule in pack["rules"]:
            if doc_type not in rule.get("applies_to", ["RFP"]): continue
            try: passed = bool(safe_eval(rule["check"], context))
            except Exception as e:
                log.warning("rule %s unevaluable (%s) - FAIL", rule["id"], e); passed = False
            log.debug("  %s %-9s %s", "PASS" if passed else "FAIL", rule["id"], rule["check"])
            if not passed:
                findings.append({"rule_id":rule["id"], "pack":pack["pack"],
                    "framework":pack["label"], "severity":rule["severity"],
                    "message":rule["message"], "fix_hint":rule.get("fix_hint",""),
                    "citation":rule.get("citation",""), "clause":rule.get("clause","")})
    return findings


def all_rules(directory=None, doc_type="RFP") -> list[dict[str, Any]]:
    out = []
    for pack in load_packs(directory):
        for rule in pack["rules"]:
            if doc_type in rule.get("applies_to", ["RFP"]):
                out.append({**rule, "pack":pack["pack"], "framework":pack["label"]})
    return out
