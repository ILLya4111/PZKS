from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from itertools import combinations
import math
import random
import re

@dataclass(frozen=True)
class Node:
    op: str
    args: tuple['Node', ...] = ()
    value: str = ''


def val(s: str) -> Node:
    return Node('val', (), str(s))


def make(op: str, *children: Node) -> Node:
    return Node(op, tuple(children))


TOKEN = re.compile(r'\s*(?:(?P<num>(?:\d+(?:\.\d*)?|\.\d+))|(?P<id>[A-Za-z_][A-Za-z_0-9]*)|(?P<op>[()+\-*/^,]))')

class ParseError(ValueError):
    pass

class Parser:
    def __init__(self, text: str):
        self.tokens = []
        p = 0
        while p < len(text):
            if text[p:].strip() == '':
                break
            m = TOKEN.match(text, p)
            if not m:
                raise ParseError(f'Невідомий символ на позиції {p + 1}: {text[p:p+8]!r}')
            kind = m.lastgroup
            self.tokens.append((kind, m.group(kind)))
            p = m.end()
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos][1] if self.pos < len(self.tokens) else None

    def pop(self, expected=None):
        token = self.peek()
        if token is None or (expected is not None and token != expected):
            raise ParseError(f'Очікується {expected or "операнд"}, знайдено {token or "кінець виразу"}')
        self.pos += 1
        return token

    def parse(self):
        if not self.tokens:
            raise ParseError('Порожній вираз')
        result = self.expr()
        if self.peek() is not None:
            raise ParseError(f'Зайвий токен: {self.peek()}')
        return result

    def expr(self):
        left = self.term()
        while self.peek() in ('+', '-'):
            op = self.pop()
            left = make(op, left, self.term())
        return left

    def term(self):
        left = self.unary()
        while self.peek() in ('*', '/'):
            op = self.pop()
            left = make(op, left, self.unary())
        return left

    def unary(self):
        if self.peek() == '+':
            self.pop()
            return self.unary()
        if self.peek() == '-':
            self.pop()
            return make('neg', self.unary())
        return self.power()

    def power(self):
        left = self.primary()
        if self.peek() == '^':
            self.pop()
            return make('^', left, self.unary())
        return left

    def primary(self):
        t = self.pop()
        if t == '(':
            result = self.expr()
            self.pop(')')
            return result
        if re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)', t):
            return val(t)
        if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', t):
            if self.peek() == '(':
                self.pop('(')
                args = []
                if self.peek() != ')':
                    args.append(self.expr())
                    while self.peek() == ',':
                        self.pop(',')
                        args.append(self.expr())
                self.pop(')')
                return Node('func', tuple(args), t)
            return val(t)
        raise ParseError(f'Неочікуваний токен: {t}')


def parse(text: str) -> Node:
    return Parser(text).parse()

PREC = {'+': 1, '-': 1, '*': 2, '/': 2, 'neg': 3, '^': 4, 'func': 5, 'val': 5}

def display(n: Node) -> str:
    if n.op == 'val':
        return n.value
    if n.op == 'func':
        return f'{n.value}(' + ', '.join(display(x) for x in n.args) + ')'
    if n.op == 'neg':
        c = display(n.args[0])
        if PREC[n.args[0].op] < PREC['neg']:
            c = f'({c})'
        return '-' + c
    a, b = n.args
    left, right = display(a), display(b)
    if PREC[a.op] < PREC[n.op]:
        left = f'({left})'
    if (PREC[b.op] < PREC[n.op] or
        (n.op in ('-', '/') and PREC[b.op] <= PREC[n.op]) or
        (n.op == '*' and b.op == '/') or
        (n.op == '+' and b.op == '-')):
        right = f'({right})'
    return f'{left} {n.op} {right}'


def count_operations(n: Node) -> int:
    return (0 if n.op == 'val' else 1) + sum(count_operations(a) for a in n.args)


def height(n: Node) -> int:
    return (0 if n.op == 'val' else 1 + max((height(a) for a in n.args), default=0))


def levels(n: Node):
    grouped = {}
    def visit(cur):
        if cur.op == 'val':
            return 0
        lv = 1 + max((visit(a) for a in cur.args), default=0)
        grouped.setdefault(lv, []).append(display(cur))
        return lv
    visit(n)
    return dict(sorted(grouped.items()))


def nodes(n: Node) -> int:
    return 1 + sum(nodes(a) for a in n.args)


def paths(n: Node, path=()):
    yield path, n
    for i, c in enumerate(n.args):
        yield from paths(c, path + (i,))


def replace(n: Node, path: tuple[int, ...], with_node: Node):
    if not path:
        return with_node
    i = path[0]
    children = list(n.args)
    children[i] = replace(children[i], path[1:], with_node)
    return Node(n.op, tuple(children), n.value)


def flatten_add(n: Node, sign=1):
    if n.op == '+':
        return flatten_add(n.args[0], sign) + flatten_add(n.args[1], sign)
    if n.op == '-':
        return flatten_add(n.args[0], sign) + flatten_add(n.args[1], -sign)
    if n.op == 'neg':
        return flatten_add(n.args[0], -sign)
    return [(sign, n)]


def sum_signed(terms):
    assert terms
    result = None
    for sign, node in terms:
        if result is None:
            result = node if sign == 1 else make('neg', node)
        else:
            result = make('+' if sign == 1 else '-', result, node)
    return result


def product(items):
    if not items:
        return val('1')
    cur = items[0]
    for item in items[1:]:
        cur = make('*', cur, item)
    return cur


def factor_parts(n: Node):
    if n.op == '*':
        a, b = factor_parts(n.args[0]), factor_parts(n.args[1])
        return (a[0] + b[0], a[1] + b[1])
    if n.op == '/':
        a, b = factor_parts(n.args[0]), factor_parts(n.args[1])
        return (a[0] + b[1], a[1] + b[0])
    return ([n], [])


def key(n: Node):
    if n.op in ('*', '+'):
        return (n.op,) + tuple(sorted((key(x) for x in n.args), key=repr))
    return (n.op, n.value, tuple(key(a) for a in n.args))


def common_factors(first, second):
    common = set(key(x) for x in first) & set(key(x) for x in second)
    return [next(x for x in first if key(x) == k) for k in common]


def subtract_one(items, factor):
    out = list(items)
    for i, x in enumerate(out):
        if key(x) == key(factor):
            return out[:i] + out[i+1:]
    raise ValueError('Множник відсутній')


def term_without_factor(n, factor, denominator=False):
    nums, dens = factor_parts(n)
    if denominator:
        dens = subtract_one(dens, factor)
    else:
        nums = subtract_one(nums, factor)
    numerator = product(nums)
    return numerator if not dens else make('/', numerator, product(dens))


def factor_rewrites(n: Node):
    if n.op not in ('+', '-', 'neg'):
        return []
    terms = flatten_add(n)
    if len(terms) < 2:
        return []
    output = []
    fmap = {}
    for i, (_, t) in enumerate(terms):
        nums, dens = factor_parts(t)
        for denominator, factors in ((False, nums), (True, dens)):
            for f in factors:
                if f.op == 'val' and f.value in ('1', '-1'):
                    continue
                k = (denominator, key(f))
                if k not in fmap:
                    fmap[k] = (f, set())
                fmap[k][1].add(i)
    for (denominator, _), (f, indices) in fmap.items():
        if len(indices) < 2:
            continue
        groups = [tuple(sorted(indices))] + [pair for pair in combinations(sorted(indices), 2)]
        used = set()
        for group in groups:
            if group in used:
                continue
            used.add(group)
            reduced = [(terms[i][0], term_without_factor(terms[i][1], f, denominator)) for i in group]
            grouped_sum = sum_signed(reduced)
            new_term = make('/', grouped_sum, f) if denominator else make('*', f, grouped_sum)
            remaining = [terms[i] for i in range(len(terms)) if i not in group]
            remaining.insert(min(group[0], len(remaining)), (1, new_term))
            candidate = sum_signed(remaining)
            if key(candidate) != key(n):
                output.append((candidate, f'Винесли {display(f)}' if not denominator else f'Об’єднали дроби зі знаменником {display(f)}'))
    return output


def distribute_rewrites(n: Node):
    out = []
    if n.op == '*':
        a, b = n.args
        for idx, side in enumerate((a, b)):
            terms = flatten_add(side)
            if len(terms) < 2:
                continue
            other = b if idx == 0 else a
            if len(terms) > 8:
                continue
            expanded = sum_signed([(s, make('*', other, t) if idx == 0 else make('*', t, other)) for s, t in terms])
            out.append((expanded, f'Розкрили дужки: множення на {display(other)}'))
    elif n.op == '/':
        numerator, denominator = n.args
        terms = flatten_add(numerator)
        if 2 <= len(terms) <= 8:
            out.append((sum_signed([(s, make('/', t, denominator)) for s, t in terms]), 'Розподілили ділення чисельника на спільний знаменник'))
    elif n.op == 'neg' and n.args[0].op in ('+', '-', 'neg'):
        out.append((sum_signed(flatten_add(n)), 'Розкрили дужки після мінуса'))
    elif n.op in ('+', '-'):
        normalized = sum_signed(flatten_add(n))
        if display(normalized) != display(n):
            out.append((normalized, 'Розкрили дужки після плюса/мінуса зі збереженням знаків'))
    return out

def distribution_remaining(n: Node) -> int:
    count = 0
    if n.op == '*':
        for side in n.args:
            terms = flatten_add(side)
            if 2 <= len(terms) <= 8:
                count += len(terms) - 1
    elif n.op == '/':
        terms = flatten_add(n.args[0])
        if 2 <= len(terms) <= 8:
            count += len(terms) - 1
    elif n.op == 'neg' and n.args[0].op in ('+', '-', 'neg'):
        count += 1
    elif n.op in ('+', '-'):
        if display(sum_signed(flatten_add(n))) != display(n):
            count += 1
    return count + sum(distribution_remaining(child) for child in n.args)


def form_sort_key(form: 'Form', mode: str):
    if mode == 'distribute':
        return (distribution_remaining(form.tree), -form.step,
                height(form.tree), count_operations(form.tree))
    return (height(form.tree), count_operations(form.tree), form.step)


@dataclass
class Form:
    tree: Node
    step: int
    rule: str
    parent: int | None


def generate(source: Node, mode: str, limit=100, max_depth=4, max_nodes=140,
             search_budget=800):
    if mode not in ('factor', 'distribute'):
        raise ValueError('Невідомий режим')
    limit = max(1, int(limit))
    search_budget = max(limit, min(2500, int(search_budget)))
    all_forms = [Form(source, 0, 'Початкова форма', None)]
    seen = {display(source)}
    frontier = [0]
    if mode == 'distribute':
        current_idx = 0
        max_expansion_steps = min(60, max(12, nodes(source)))
        for _ in range(max_expansion_steps):
            original = all_forms[current_idx].tree
            choices = []
            for path, sub in paths(original):
                for changed, rule in distribute_rewrites(sub):
                    candidate = replace(original, path, changed)
                    if nodes(candidate) > max(350, max_nodes):
                        continue
                    cand_text = display(candidate)
                    if cand_text in seen:
                        continue
                    choices.append((distribution_remaining(candidate),
                                    nodes(candidate), len(cand_text),
                                    candidate, rule, cand_text))
            if not choices or len(all_forms) >= search_budget:
                break
            _, _, _, chosen, rule, chosen_text = min(choices, key=lambda x: x[:3])
            seen.add(chosen_text)
            all_forms.append(Form(chosen, all_forms[current_idx].step + 1,
                                  rule, current_idx))
            current_idx = len(all_forms) - 1
            if distribution_remaining(chosen) == 0:
                break
    beam_width = max(70, min(240, search_budget // max(2, max_depth)))

    def rank(idx):
        f = all_forms[idx]
        return (*form_sort_key(f, mode), idx)

    for _ in range(max_depth):
        if not frontier or len(all_forms) >= search_budget:
            break
        next_frontier = []
        for idx in frontier:
            if len(all_forms) >= search_budget:
                break
            f = all_forms[idx]
            for path, sub in paths(f.tree):
                if len(all_forms) >= search_budget:
                    break
                rewrites = factor_rewrites(sub) if mode == 'factor' else distribute_rewrites(sub)
                for converted, rule in rewrites:
                    candidate = replace(f.tree, path, converted)
                    if nodes(candidate) > max_nodes:
                        continue
                    form_text = display(candidate)
                    if form_text in seen:
                        continue
                    seen.add(form_text)
                    all_forms.append(Form(candidate, f.step + 1, rule, idx))
                    next_frontier.append(len(all_forms) - 1)
                    if len(all_forms) >= search_budget:
                        break
        frontier = sorted(next_frontier, key=rank)[:beam_width]

    if len(all_forms) <= limit:
        return all_forms
    winners = {0}
    for i in sorted(range(1, len(all_forms)), key=rank):
        chain = []
        j = i
        while j is not None and j not in winners:
            chain.append(j)
            j = all_forms[j].parent
        if len(winners) + len(chain) > limit:
            continue
        winners.update(chain)
        if len(winners) >= limit:
            break
    ordered = sorted(winners)
    mapping = {old: new for new, old in enumerate(ordered)}
    return [Form(all_forms[i].tree, all_forms[i].step, all_forms[i].rule,
                 mapping.get(all_forms[i].parent)) for i in ordered]


def evaluate(n: Node, variables: dict[str, float]):
    if n.op == 'val':
        try:
            return float(n.value)
        except ValueError:
            if n.value == 'pi':
                return math.pi
            if n.value == 'e':
                return math.e
            return variables[n.value]
    if n.op == 'neg':
        return -evaluate(n.args[0], variables)
    if n.op == 'func':
        supported = {'sin': math.sin, 'cos': math.cos, 'exp': math.exp, 'log': math.log,
                     'sqrt': math.sqrt, 'abs': abs}
        if n.value not in supported:
            raise ValueError('Неможливо оцінити довільну функцію ' + n.value)
        return supported[n.value](*(evaluate(a, variables) for a in n.args))
    a, b = (evaluate(x, variables) for x in n.args)
    if n.op == '+': return a + b
    if n.op == '-': return a - b
    if n.op == '*': return a * b
    if n.op == '/': return a / b
    if n.op == '^': return a ** b
    raise ValueError(n.op)


def variables_of(n: Node):
    if n.op == 'val' and not re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)', n.value) and n.value not in ('pi', 'e'):
        return {n.value}
    r = set()
    for a in n.args:
        r |= variables_of(a)
    return r


def validate_equivalent(original: Node, transformed: Node, trials=20):
    rng = random.Random(7403)
    names = sorted(variables_of(original) | variables_of(transformed))
    successes = 0
    for _ in range(trials * 5):
        environment = {n: rng.uniform(0.75, 4.5) * (-1 if rng.randrange(2) else 1) for n in names}
        try:
            x = evaluate(original, environment)
            y = evaluate(transformed, environment)
        except (ValueError, KeyError) as exc:
            return 'unknown', f'Автоматична перевірка недоступна: {exc}'
        except (ZeroDivisionError, OverflowError, ArithmeticError):
            continue
        if isinstance(x, complex) or isinstance(y, complex) or not (math.isfinite(x) and math.isfinite(y)):
            continue
        if not math.isclose(x, y, rel_tol=1e-8, abs_tol=1e-8):
            return 'fail', f'ЗНАЙДЕНО РОЗБІЖНІСТЬ: {x:.8g} ≠ {y:.8g}'
        successes += 1
        if successes >= trials:
            return 'pass', f'Збіг на {successes} числових підстановках (не математичний доказ)'
    return 'unknown', f'Перевірено лише {successes} допустимих підстановок; доказу немає'


ASSOCIATIVE_TESTS = {
    'А1 · Спільний множник': 'a*b+a*c+b*c',
    'А2 · Спільна дужка': 'a*(b-2)+c*(b-2)',
    'А3 · Багатокрокове винесення': 'a*b-2*a+b*c-c*2',
    'А4 · Спільний знаменник': 'a/b-c/b+2/b',
    'А5 · Складний знаменник': 'a/(b-1)-c/(b-1)+2/(b-1)-t',
    'А6 · Комбінований вираз': 'a-b*k+b*t-f*f*5.9+f*q+g*f*5.9-g*q-f/(d+q-w)-g/(d+q-w)',
    'А7 · Великий вираз': 'a-b*k+b*t-b*f*f*5.9+b*f*q+b*g*f*5.9-b*g*q-b*w/p+b*y*m/p-b*y/p-x*x/(d+q-w)+3*x/(d+q-w)+3*x/(d+q-w)+3*3/(d+q-w)',
}

DISTRIBUTIVE_TESTS = {
    'Д1 · Дві дужки': 'a*(b+c-1)*d',
    'Д2 · Добуток дужок': '(a-c)*(b-k+1)',
    'Д3 · Ділення': '(1-d)/(a+b-2)/e',
    'Д4 · Вкладені вирази': 'a-b*(k-t)-(f-g)*(f*5.9-q)-(f+g)/(d+q-w)',
    'Д5 · Великий вираз': 'a-b*(k-t+(f-g)*(f*5.9-q)+(w-y*(m-1))/p)-(x-3)*(x+3)/(d+q-w)',
}
