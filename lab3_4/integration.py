from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from lab1.analyzer import analyze, tokenize
except ImportError as exc:
    raise RuntimeError('Не знайдено lab1/analyzer.py. Перевір структуру PZKS/lab1.') from exc

try:
    from lab2.tree_builder import Parser as Lab2Parser
except ImportError as exc:
    raise RuntimeError('Не знайдено lab2/tree_builder.py. Перевір структуру PZKS/lab2.') from exc


def validate_with_previous_labs(expression):
    tokens, errors = analyze(expression)
    issues = [(e.start, e.end, f'{e.category}: {e.message}') for e in errors]
    if issues:
        return issues
    try:
        Lab2Parser(tokens).parse()
    except (ValueError, IndexError, TypeError) as exc:
        return [(0, len(expression), f'ЛР2: неможливо побудувати дерево: {exc}')]
    return []


def zero_denominators(tree):
    from transformations import display

    def exact_zero(node):
        op = node.op
        if op == 'val':
            try:
                return float(node.value) == 0
            except ValueError:
                return False
        if op == 'neg':
            return exact_zero(node.args[0])
        if op == '-':
            return node.args[0] == node.args[1] or (all_constant(node) and safe_constant_zero(node))
        if op == '*':
            return any(exact_zero(c) for c in node.args)
        if op in ('+', '/'):
            return all_constant(node) and safe_constant_zero(node)
        return False

    def all_constant(node):
        if node.op == 'val':
            try:
                float(node.value)
                return True
            except ValueError:
                return False
        if node.op in ('+', '-', '*', '/', 'neg'):
            return all(all_constant(c) for c in node.args)
        return False

    def constant_value(node):
        if node.op == 'val':
            return float(node.value)
        if node.op == 'neg':
            return -constant_value(node.args[0])
        a, b = (constant_value(c) for c in node.args)
        if node.op == '+': return a + b
        if node.op == '-': return a - b
        if node.op == '*': return a * b
        if node.op == '/': return a / b
        raise ValueError(node.op)

    def safe_constant_zero(node):
        try:
            return constant_value(node) == 0
        except (ZeroDivisionError, OverflowError, ValueError):
            return False

    result = []
    def walk(node):
        if node.op == '/' and exact_zero(node.args[1]):
            denominator = display(node.args[1])
            if denominator not in result:
                result.append(denominator)
        for child in node.args:
            walk(child)
    walk(tree)
    return result
