"""ЛР2: дерево виразу з паралельним балансуванням асоціативних операцій."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import heapq
from itertools import count
from lab1.analyzer import analyze


@dataclass(frozen=True)
class Node:
    op: str
    children: tuple = ()


def atom(value):
    return Node(value)


def negate(node):
    if node.op == 'neg':
        return node.children[0]
    if node.op == '+' and node.children:
        return Node('+', tuple(negate(c) for c in node.children))
    return Node('neg', (node,))


def reciprocal(node):
    if node.op == 'inv':
        return node.children[0]
    # /((x * y)) = (1/x) * (1/y) ; /((x/y)) = y/x
    if node.op == '*' and node.children:
        return Node('*', tuple(reciprocal(c) for c in node.children))
    return Node('inv', (node,))


def merge(op, left, right):
    children = []
    for node in (left, right):
        if node.op == op and node.children:
            children.extend(node.children)
        else:
            children.append(node)
    return Node(op, tuple(children))


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def current(self):
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return None

    def take(self, kind=None, value=None):
        tok = self.current()
        if tok is None or (kind and tok.kind != kind) or (value and tok.text != value):
            raise ValueError(f'Очікувався {value or kind}, позиція {tok.start if tok else "кінець"}')
        self.i += 1
        return tok

    def parse(self):
        result = self.expression()
        if self.current() is not None:
            raise ValueError(f'Зайвий токен {self.current().text!r}')
        return result

    def expression(self):
        node = self.term()
        while self.current() and self.current().kind == 'OP' and self.current().text in '+-':
            op = self.take('OP').text
            right = self.term()
            node = merge('+', node, right if op == '+' else negate(right))
        return node

    def term(self):
        node = self.primary()
        while self.current() and self.current().kind == 'OP' and self.current().text in '*/':
            op = self.take('OP').text
            right = self.primary()
            node = merge('*', node, right if op == '*' else reciprocal(right))
        return node

    def primary(self):
        tok = self.current()
        if tok is None:
            raise ValueError('Очікується операнд')
        if tok.kind == 'OP' and tok.text in '+-':
            sign = self.take('OP').text
            n = self.primary()
            return n if sign == '+' else negate(n)
        if tok.kind == 'LPAREN':
            self.take('LPAREN')
            n = self.expression()
            self.take('RPAREN')
            return n
        if tok.kind in ('NUMBER', 'IDENTIFIER'):
            self.take()
            if tok.kind == 'IDENTIFIER' and self.current() and self.current().kind == 'LPAREN':
                self.take('LPAREN')
                args = []
                if self.current() and self.current().kind != 'RPAREN':
                    args.append(self.expression())
                    while self.current() and self.current().kind == 'COMMA':
                        self.take('COMMA')
                        args.append(self.expression())
                self.take('RPAREN')
                return Node('call:' + tok.text, tuple(args))
            return atom(tok.text)
        raise ValueError(f'Неочікуваний токен {tok.text!r}')


def normalize(n):
    """Розкриває асоціативні вкладення, але не розкриває добуток дистрибутивно."""
    if not n.children:
        return n
    children = [normalize(c) for c in n.children]
    if n.op == 'neg':
        c = children[0]
        if c.op == 'neg':
            return c.children[0]
        if c.op == '+':
            return normalize(Node('+', tuple(negate(x) for x in c.children)))
        return Node('neg', (c,))
    if n.op == 'inv':
        c = children[0]
        if c.op == 'inv':
            return c.children[0]
        if c.op == '*':
            return normalize(Node('*', tuple(reciprocal(x) for x in c.children)))
        return Node('inv', (c,))
    if n.op in ('+', '*'):
        flat = []
        for c in children:
            flat.extend(c.children if c.op == n.op else (c,))
        return Node(n.op, tuple(flat)) if len(flat) > 1 else flat[0]
    return Node(n.op, tuple(children))


def balance(node):
    """Об'єднує піддерева з найменшою висотою, зберігаючи рівнозначність."""
    if not node.children:
        return node
    kids = [balance(c) for c in node.children]
    if node.op not in ('+', '*') or len(kids) <= 2:
        return Node(node.op, tuple(kids))
    heap = []
    seq = count()
    for child in kids:
        heapq.heappush(heap, (height(child), next(seq), child))
    while len(heap) > 1:
        h1, _, left = heapq.heappop(heap)
        h2, _, right = heapq.heappop(heap)
        joined = Node(node.op, (left, right))
        heapq.heappush(heap, (1 + max(h1, h2), next(seq), joined))
    return heap[0][2]


def height(node):
    return 1 + max((height(child) for child in node.children), default=0)


def width(node):
    levels = []
    def visit(n, level):
        if len(levels) <= level:
            levels.append(0)
        levels[level] += 1
        for c in n.children:
            visit(c, level + 1)
    visit(node, 0)
    return max(levels)


def tree_lines(node):
    out = []
    def visit(n, prefix='', last=True, root=True):
        op = n.op[5:] + '()' if n.op.startswith('call:') else {'neg':'− (унарний)', 'inv':'1 / (обернений)'}.get(n.op, n.op)
        out.append(('' if root else prefix + ('└── ' if last else '├── ')) + op)
        for i, c in enumerate(n.children):
            visit(c, prefix + ('' if root else ('    ' if last else '│   ')), i == len(n.children)-1, False)
    visit(node)
    return '\n'.join(out)


def _decimal(node):
    try:
        if not node.children:
            return Decimal(node.op)
        vals = [_decimal(c) for c in node.children]
        if any(v is None for v in vals):
            return None
        if node.op == 'neg':
            return -vals[0]
        if node.op == 'inv':
            return 1 / vals[0] if vals[0] != 0 else None
        if node.op == '+':
            return sum(vals, Decimal(0))
        if node.op == '*':
            result = Decimal(1)
            for v in vals:
                result *= v
            return result
    except (InvalidOperation, ZeroDivisionError, ArithmeticError):
        return None
    return None


def divide_by_zero(node):
    found = []
    def walk(n):
        if n.op == 'inv' and _decimal(n.children[0]) == 0:
            found.append(n)
        for c in n.children:
            walk(c)
    walk(node)
    return len(found)


def _number(node):
    if node.children:
        return None
    try:
        return Decimal(node.op)
    except InvalidOperation:
        return None


def _constant(value):
    if value == 0:
        return atom('0')
    return atom(format(value.normalize(), 'f'))


def _terms(node, op):
    if node.op == op and node.children:
        return [item for child in node.children for item in _terms(child, op)]
    return [node]


def _coefficient(node):
    if node.op == 'neg':
        coefficient, base = _coefficient(node.children[0])
        return -coefficient, base
    if node.op == '*' and node.children:
        factors = _terms(node, '*')
        value = Decimal(1)
        rest = []
        for factor in factors:
            num = _number(factor)
            if num is None:
                rest.append(factor)
            else:
                value *= num
        if len(rest) == 1:
            return value, rest[0]
        if rest:
            return value, Node('*', tuple(rest))
        return value, None
    num = _number(node)
    if num is not None:
        return num, None
    return Decimal(1), node


def simplify(node):
    """Обчислення констант та безпечні локальні алгебраїчні спрощення.

    Не виконує повної комп'ютерної алгебри та не доводить нерівність знаменників нулю.
    """
    if not node.children:
        return node
    kids = tuple(simplify(child) for child in node.children)
    op = node.op
    if op == 'neg':
        child = kids[0]
        val = _number(child)
        if val is not None:
            return _constant(-val)
        if child.op == 'neg':
            return child.children[0]
        if child.op == '+':
            return simplify(Node('+', tuple(Node('neg', (x,)) for x in child.children)))
        return Node(op, kids)
    if op == 'inv':
        child = kids[0]
        val = _number(child)
        if val is not None and val != 0:
            return _constant(Decimal(1) / val)
        if child.op == 'inv':
            # Only where the operand is defined and nonzero; do not cancel 1/(1/0).
            return child.children[0] if not divide_by_zero(child) else Node(op, kids)
        return Node(op, kids)
    if op == '*':
        factors = [x for child in kids for x in _terms(child, '*')]
        number = Decimal(1)
        others = []
        for factor in factors:
            val = _number(factor)
            if val is not None:
                number *= val
            else:
                others.append(factor)
        if number == 0:
            # Do not mask e.g. 0*(1/0).
            if not any(divide_by_zero(x) for x in others):
                return atom('0')
        if number != 1 or not others:
            others.insert(0, _constant(number))
        if len(others) == 1:
            return others[0]
        return Node('*', tuple(others))
    if op == '+':
        terms = [x for child in kids for x in _terms(child, '+')]
        # Collect like terms without expanding products distributively.
        summed = {}
        for term in terms:
            coeff, base = _coefficient(term)
            summed[base] = summed.get(base, Decimal(0)) + coeff
        result = []
        for base, coeff in summed.items():
            if coeff == 0:
                continue
            if base is None:
                result.append(_constant(coeff))
            elif coeff == 1:
                result.append(base)
            elif coeff == -1:
                result.append(Node('neg', (base,)))
            else:
                result.append(Node('*', (_constant(coeff), base)))
        if not result:
            return atom('0')
        return Node('+', tuple(result)) if len(result) > 1 else result[0]
    return Node(op, kids)


def _zero_denominators(node):
    """Перевіряє знаменники після локального символьного спрощення."""
    detected = 0
    def check(current):
        nonlocal detected
        if current.op == 'inv' and current.children:
            denominator = simplify(normalize(current.children[0]))
            if _number(denominator) == 0:
                detected += 1
        for child in current.children:
            check(child)
    check(node)
    return detected


def operation_levels(root):
    """ASAP-яруси: листки — вхідні дані, рахуємо лише операції."""
    levels = {}
    def walk(node):
        if not node.children:
            return 0
        level = max((walk(child) for child in node.children), default=0) + 1
        levels.setdefault(level, []).append(node)
        return level
    walk(root)
    return dict(sorted(levels.items()))


def operation_metrics(root):
    levels = operation_levels(root)
    return len(levels), max((len(items) for items in levels.values()), default=0)


def expression_text(node):
    if not node.children:
        return node.op
    if node.op == 'neg':
        return f'(-{expression_text(node.children[0])})'
    if node.op == 'inv':
        return f'(1/{expression_text(node.children[0])})'
    if node.op.startswith('call:'):
        return node.op[5:] + '(' + ', '.join(expression_text(x) for x in node.children) + ')'
    return '(' + (' ' + node.op + ' ').join(expression_text(x) for x in node.children) + ')'


def numeric_result(root):
    value = _decimal(root)
    return format(value.normalize(), 'f') if value is not None else None


def contains_variables(node):
    if not node.children:
        return _number(node) is None
    return any(contains_variables(child) for child in node.children)



def _pair_tree(items, operator):
    items = list(items)
    if len(items) == 1:
        return items[0]
    while len(items) > 1:
        items = [Node(operator, tuple(items[i:i+2])) if i+1 < len(items) else items[i]
                 for i in range(0, len(items), 2)]
    return items[0]


def method_two(items, primary, dual):
    """Ланцюжок x-y-z-... або x/y/z/... без унарних вузлів."""
    items = list(items)
    if len(items) < 2:
        return items[0]
    current = [Node(primary, (items[0], items[1]))]
    for i in range(2, len(items), 2):
        current.append(Node(dual, (items[i], items[i+1])) if i+1 < len(items) else items[i])
    while len(current) > 1:
        new = [Node(primary, (current[0], current[1]))]
        for i in range(2, len(current), 2):
            new.append(Node(dual, (current[i], current[i+1])) if i+1 < len(current) else current[i])
        current = new
    return current[0]


def parallelize(node):
    """Згортає унарні -/1/x у двійкові операції, зберігаючи знаки."""
    if not node.children:
        return node
    children = [parallelize(c) for c in node.children]
    if node.op in ('+', '*'):
        minus = 'neg' if node.op == '+' else 'inv'
        main = '-' if node.op == '+' else '/'
        positive, negative = [], []
        sequence = []
        for c in children:
            if c.op == minus and len(c.children) == 1:
                negative.append(c.children[0]); sequence.append((False, c.children[0]))
            else:
                positive.append(c); sequence.append((True, c))
        if not negative:
            return _pair_tree(children, node.op) if len(children)>1 else children[0]
        if len(positive) == 1 and sequence[0][0] and all(not sign for sign, _ in sequence[1:]):
            return method_two([c for _, c in sequence], main, node.op)
        # General case: combine positive / negative terms independently.
        if positive:
            left = _pair_tree(positive, node.op)
            right = _pair_tree(negative, node.op)
            return Node(main, (left, right))
        if node.op == '+':
            return Node('-', (atom('0'), _pair_tree(negative, '+')))
        return Node('/', (atom('1'), _pair_tree(negative, '*')))
    return Node(node.op, tuple(children))


def _safe_value(node, bindings=None):
    if not node.children:
        v = _number(node)
        if v is not None: return v
        if bindings and node.op in bindings: return bindings[node.op]
        return None
    values = [_safe_value(c, bindings) for c in node.children]
    if any(v is None for v in values): return None
    try:
        if node.op == 'neg': return -values[0]
        if node.op == 'inv': return Decimal(1)/values[0]
        if node.op == '+': return sum(values, Decimal(0))
        if node.op == '-': return values[0]-values[1]
        if node.op == '*':
            v=Decimal(1)
            for x in values: v*=x
            return v
        if node.op == '/': return values[0]/values[1]
    except (ZeroDivisionError, ArithmeticError, InvalidOperation):
        return None
    return None


def _variables(node):
    if not node.children: return {node.op} if _number(node) is None else set()
    return set().union(*(_variables(c) for c in node.children))


def equivalence_check(original, optimized):
    """Числове порівняння або кілька пробних підстановок; не формальний доказ."""
    variables = sorted(_variables(original) | _variables(optimized))
    if not variables:
        a,b = _safe_value(original), _safe_value(optimized)
        return {'original': str(a) if a is not None else None,
                'optimized':str(b) if b is not None else None,
                'valid': a is not None and a == b, 'kind':'numeric'}
    for seed in (2, 3, 5, 7, 11):
        vals = {v:Decimal(seed+i) for i,v in enumerate(variables)}
        a,b = _safe_value(original,vals),_safe_value(optimized,vals)
        if a is None or b is None: continue
        if abs(a-b) > Decimal('0.00000001') * max(abs(a), abs(b), Decimal(1)):
            return {'original':None,'optimized':None,'valid':False,'kind':'samples'}
    return {'original':None,'optimized':None,'valid':True,'kind':'samples'}


def zero_denominator_details(root):
    found = []
    def traverse(node):
        if node.op == 'inv' and node.children:
            raw = node.children[0]
            simplified = simplify(normalize(raw))
            if _number(simplified) == 0:
                found.append({'numerator':'1', 'denominator':expression_text(raw),
                              'simplified':expression_text(simplified),
                              'reason':'Знаменник після спрощення дорівнює нулю'})
        for child in node.children: traverse(child)
    traverse(root)
    return found


def build_tree(source):
    tokens, errors = analyze(source)
    if errors: return None, errors
    raw = Parser(tokens).parse()
    normalized = normalize(raw)
    issues = zero_denominator_details(raw)
    before = balance(normalized)
    numerical = not contains_variables(raw) and not issues
    transformed = parallelize(normalize(simplify(normalized))) if not issues and not numerical else parallelize(normalized)
    verification = equivalence_check(raw, transformed) if not issues else None
    return {
        'tree': transformed, 'original':raw, 'before':before,
        'zero_divisions':len(issues), 'zero_details':issues,
        'numeric_result':numeric_result(raw) if numerical else None,
        'equivalence':verification
    }, []
