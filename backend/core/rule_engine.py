"""Rule Engine — loads YAML rule-packs, evaluates boolean checks. No eval()."""
from __future__ import annotations
import ast
import operator
import os
from pathlib import Path
from typing import Any

import yaml

RULE_PACK_DIR = Path(__file__).resolve().parents[2] / "rule_packs"

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod}
_CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
        ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}
_BOOL = {ast.And: all, ast.Or: any}


def _ev(node, ctx):
    if isinstance(node, ast.Expression):
        return _ev(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ("True", "true"):
            return True
        if node.id in ("False", "false"):
            return False
        return ctx.get(node.id)
    if isinstance(node, ast.BoolOp):
        return _BOOL[type(node.op)](_ev(v, ctx) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _ev(node.operand, ctx)
    if isinstance(node, ast.BinOp):
        return _BIN[type(node.op)](_ev(node.left, ctx), _ev(node.right, ctx))
    if isinstance(node, ast.Compare):
        left = _ev(node.left, ctx)
        for op, comp in zip(node.ops, node.comparators):
            right = _ev(comp, ctx)
            if not _CMP[type(op)](left, right):
                return False
            left = right
        return True
    raise ValueError("unsupported expression")


def safe_eval(expr: str, ctx: dict[str, Any]) -> Any:
    return _ev(ast.parse(expr, mode="eval"), ctx)


def load_packs(directory: Path | None = None) -> list[dict[str, Any]]:
    directory = directory or RULE_PACK_DIR
    packs = []
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".yaml"):
            data = yaml.safe_load((directory / fn).read_text(encoding="utf-8")) or {}
            if data.get("rules") is not None:
                packs.append(data)
    return packs


def evaluate(context, doc_type="RFP", directory=None) -> list[dict[str, Any]]:
    findings = []
    for pack in load_packs(directory):
        for rule in pack["rules"]:
            if doc_type not in rule.get("applies_to", ["RFP"]):
                continue
            try:
                passed = bool(safe_eval(rule["check"], context))
            except Exception:
                passed = False
            if not passed:
                findings.append({
                    "rule_id": rule["id"], "pack": pack["pack"],
                    "framework": pack["label"], "severity": rule["severity"],
                    "message": rule["message"], "fix_hint": rule.get("fix_hint", ""),
                    "citation": rule.get("citation", ""), "clause": rule.get("clause", ""),
                })
    return findings


def all_rules(directory=None, doc_type="RFP") -> list[dict[str, Any]]:
    out = []
    for pack in load_packs(directory):
        for rule in pack["rules"]:
            if doc_type in rule.get("applies_to", ["RFP"]):
                out.append({**rule, "pack": pack["pack"], "framework": pack["label"]})
    return out
