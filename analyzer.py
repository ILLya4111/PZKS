from dataclasses import dataclass
from enum import Enum, auto
import re


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Error:
    category: str
    code: str
    start: int
    end: int
    message: str


class State(Enum):
    OPERAND = auto()
    PRIMARY = auto()
    OPERATOR = auto()


@dataclass
class Frame:
    opening: Token
    function: bool
    empty: bool = True


NUMBER = re.compile(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z')
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\Z')
SINGLE = {'+': 'OP', '-': 'OP', '*': 'OP', '/': 'OP',
          '(': 'LPAREN', ')': 'RPAREN', ',': 'COMMA'}


def tokenize(source):
    """Виділяємо лексеми, зберігаючи їхні початкові позиції."""
    tokens, errors = [], []
    i = 0
    while i < len(source):
        c = source[i]
        if c.isspace():
            i += 1
            continue
        start = i
        if c in SINGLE:
            i += 1
            tokens.append(Token(SINGLE[c], c, start, i))
            continue
        if c.isalnum() or c in '_.':
            i += 1
            while i < len(source) and (source[i].isalnum() or source[i] in '_.'):
                i += 1
            value = source[start:i]
            if NUMBER.fullmatch(value):
                kind = 'NUMBER'
            elif IDENTIFIER.fullmatch(value):
                kind = 'IDENTIFIER'
            else:
                kind = 'INVALID'
                if value[0] in '0123456789.':
                    message = f'Некоректна числова константа або ім’я з цифри: {value!r}.'
                else:
                    message = f'Некоректний ідентифікатор: {value!r}. Дозволено A–Z, a–z, _, цифри.'
                errors.append(Error('Лексична', 'INVALID', start, i, message))
        else:
            i += 1
            value, kind = c, 'UNKNOWN'
            errors.append(Error('Лексична', 'UNKNOWN', start, i,
                                f'Невідомий символ {c!r}.'))
        tokens.append(Token(kind, value, start, i))
    return tokens, errors


def analyze(source):
    tokens, errors = tokenize(source)
    stack = []
    state = State.OPERAND
    previous = None

    def error(code, token, message):
        errors.append(Error('Синтаксична', code, token.start, token.end, message))

    for token in tokens:
        kind = token.kind
        if kind == 'UNKNOWN':
            previous = token
            continue
        if kind == 'LPAREN':
            function = previous is not None and previous.kind == 'IDENTIFIER'
            if state == State.OPERATOR and not function:
                error('MISSING_OPERATOR', token, 'Перед «(» пропущено оператор. Неявне множення не підтримується.')
            if stack:
                stack[-1].empty = False
            stack.append(Frame(token, function))
            state = State.OPERAND
        elif kind == 'RPAREN':
            if not stack:
                error('EXTRA_CLOSE', token, 'Закриваюча дужка не має парної відкриваючої.')
            else:
                frame = stack.pop()
                if state != State.OPERATOR and not (frame.function and frame.empty):
                    if frame.empty:
                        error('EMPTY_GROUP', token, 'Порожній вираз у дужках. Порожні дужки дозволені тільки у виклику функції.')
                    elif previous and previous.kind == 'COMMA':
                        error('MISSING_ARGUMENT', token, 'Пропущено аргумент після коми.')
                    else:
                        error('MISSING_OPERAND', token, 'Перед «)» пропущено операнд.')
                state = State.OPERATOR
        elif kind == 'COMMA':
            if not stack or not stack[-1].function:
                error('COMMA_OUTSIDE', token, 'Кома дозволена лише між аргументами функції на поточному рівні дужок.')
            if state != State.OPERATOR:
                error('MISSING_ARGUMENT', token, 'Перед комою пропущено аргумент або операнд.')
            if stack:
                stack[-1].empty = False
            state = State.OPERAND
        elif kind == 'OP':
            if stack:
                stack[-1].empty = False
            if state == State.OPERATOR:
                state = State.PRIMARY
            elif token.text in '+-' and state == State.OPERAND:
                state = State.PRIMARY
            else:
                error('UNEXPECTED_OPERATOR', token,
                      f'Неочікуваний оператор {token.text!r}: потрібен операнд. Після оператора потрібне число, змінна, функція або дужка; операнд зі знаком візьміть у дужки.')
        else:
            if state == State.OPERATOR:
                error('MISSING_OPERATOR', token, 'Між операндами пропущено арифметичний оператор.')
            if stack:
                stack[-1].empty = False
            state = State.OPERATOR
        previous = token

    eof = Token('EOF', '', len(source), len(source))
    if not tokens:
        error('EMPTY_EXPRESSION', eof, 'Вираз порожній.')
    elif state != State.OPERATOR:
        error('INCOMPLETE', eof, 'Вираз незавершений: наприкінці очікується операнд.')
    for frame in stack:
        error('UNCLOSED', frame.opening, 'Відкриваюча дужка не має парної закриваючої.')
    errors.sort(key=lambda e: (e.start, e.end, e.category, e.code))
    return tokens, errors

