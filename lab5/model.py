from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, DivisionByZero, InvalidOperation
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab1.analyzer import analyze
from lab2.tree_builder import Parser as Lab2Parser, build_tree as lab2_build_tree
from lab3_4.transformations import Node, parse as parse_expression, display

DEFAULT_TIMES = {'+': 2, '-': 3, '*': 4, '/': 8, 'neg': 3}
EXAMPLE = '((a+b)*(c-d))+((e*f)/(g+h))'
EXAMPLES = [
    ('V1 · 4 незалежні гілки', EXAMPLE),
    ('V2 · Два добутки', '(a+b)*(c+d)'),
    ('V3 · Незалежні суми', 'a*b+c*d+e*f+g*h+i*j+k*l'),
    ('V4 · Залежні операції', '((a*b)+(c/d))*(e+f)'),
    ('V5 · Власний складний', '(a*b+c*d)/(e+f)+(g-h)*(i+j)'),
    ('V6 · З ЛР3 (А3)', 'a*b-2*a+b*c-c*2'),
    ('V7 · З ЛР4 (Д2)', '(a-c)*(b-k+1)'),
]


@dataclass(frozen=True)
class Settings:
    processors: int = 6
    banks: int = 3
    plus: int = 2
    minus: int = 3
    multiply: int = 4
    divide: int = 8
    read: int = 1
    write: int = 1
    policy: str = 'id'
    use_lab2: bool = True

    def validate(self):
        if not 1 <= self.processors <= 32:
            raise ValueError('Кількість процесорів має бути від 1 до 32.')
        if not 1 <= self.banks <= 32:
            raise ValueError('Кількість банків має бути від 1 до 32.')
        for name in ('plus', 'minus', 'multiply', 'divide', 'read', 'write'):
            if not 0 <= getattr(self, name) <= 100:
                raise ValueError(f'Некоректна тривалість: {name} (0…100).')
        if not all(getattr(self, name) >= 1 for name in ('plus','minus','multiply','divide')):
            raise ValueError('Арифметичні операції повинні займати щонайменше 1 такт.')
        if self.policy not in ('id','critical'):
            raise ValueError('Непідтримуваний порядок вибору операцій.')

    def duration(self, op):
        return {'+':self.plus, '-':self.minus, '*':self.multiply, '/':self.divide, 'neg':self.minus}[op]


@dataclass(frozen=True)
class Task:
    id: int
    op: str
    expression: str
    level: int
    dependencies: tuple[int, ...]
    sources: tuple[str, ...]
    path: tuple[int, ...]


@dataclass(frozen=True)
class Segment:
    kind: str
    start: int
    end: int
    pe: int
    bank: int | None
    task: int
    detail: str = ''


@dataclass
class Scheduled:
    task: Task
    pe: int
    word: int
    start: int
    end: int
    result_bank: int
    phases: list[Segment]


@dataclass
class Word:
    number: int
    start: int
    end: int
    jobs: list[Scheduled]


@dataclass
class Simulation:
    expression: str
    settings: Settings
    tasks: list[Task]
    words: list[Word]
    segments: list[Segment]
    total: int
    sequential: int
    speedup: float
    efficiency: float
    busy_compute: int
    graph_lines: list[str]
    modeled_expression: str = ''
    note: str = ''
    comparison: dict[str, tuple[int, int]] = field(default_factory=dict)


def _numeric(n: Node):
    if n.op == 'val':
        try:
            return Decimal(n.value)
        except InvalidOperation:
            return None
    args = [_numeric(x) for x in n.args]
    if any(x is None for x in args):
        return None
    try:
        if n.op == 'neg': return -args[0]
        a, b = args
        if n.op == '+': return a+b
        if n.op == '-': return a-b
        if n.op == '*': return a*b
        if n.op == '/': return a/b if b else None
    except (ArithmeticError, ValueError, InvalidOperation):
        return None
    return None


def _guaranteed_zero(n: Node):
    if n.op == 'neg': return _guaranteed_zero(n.args[0])
    if n.op == '-':
        if n.args[0] == n.args[1]: return True
    if n.op == '*': return any(_guaranteed_zero(x) for x in n.args)
    number = _numeric(n)
    return number == 0 if number is not None else False


def _check_supported(n: Node):
    if n.op not in ('val', '+', '-', '*', '/', 'neg'):
        raise ValueError(f'Для VLIW у ЛР5 підтримуються +, −, *, /. Конструкція {display(n)!r} не підтримується.')
    if n.op == '/' and _guaranteed_zero(n.args[1]):
        raise ValueError(f'Ділення на нуль: знаменник «{display(n.args[1])}» гарантовано дорівнює нулю.')
    for x in n.args:
        _check_supported(x)


def parse_and_validate(expr: str) -> Node:
    tokens, errors = analyze(expr)
    if errors:
        raise ValueError('\n'.join(f'Позиція {e.start+1}: {e.category}: {e.message}' for e in errors[:8]))
    try:
        Lab2Parser(tokens).parse()
        tree = parse_expression(expr)
    except (ValueError, TypeError, IndexError) as exc:
        raise ValueError(f'Не вдалося побудувати дерево: {exc}') from exc
    _check_supported(tree)
    return tree


def _convert_lab2(n) -> Node:
    if not n.children:
        return Node('val', (), n.op)
    if n.op.startswith('call:'):
        raise ValueError('Виклики функцій не моделюються в ЛР5 без заданої тривалості.')
    if n.op == 'neg':
        return Node('neg', (_convert_lab2(n.children[0]),))
    if n.op == 'inv':
        return Node('/', (Node('val', (), '1'), _convert_lab2(n.children[0])))
    if n.op not in ('+','-','*','/'):
        raise ValueError(f'Непідтримуваний вузол дерева ЛР2: {n.op}')
    kids=[_convert_lab2(x) for x in n.children]
    if len(kids)<2:
        raise ValueError('Некоректний операційний вузол ЛР2.')
    node=Node(n.op,(kids[0],kids[1]))
    for child in kids[2:]:
        node=Node(n.op,(node,child))
    return node


def effective_tree(expr: str, use_lab2: bool = True) -> Node:
    original=parse_and_validate(expr)
    if not use_lab2:
        return original
    info,errors=lab2_build_tree(expr)
    if errors:
        raise ValueError('ЛР2: помилка побудови дерева: '+str(errors[0]))
    if info is None or info.get('zero_divisions'):
        raise ValueError('ЛР2: некоректне дерево або ділення на нуль.')
    eq=info.get('equivalence')
    if eq is not None and not eq.get('valid',False):
        raise ValueError('ЛР2: автоматична перевірка паралельної форми виявила розбіжність.')
    tree=_convert_lab2(info['tree'])
    _check_supported(tree)
    return tree


def graph_from_tree(root: Node):
    raw = []
    def visit(n, path):
        if n.op == 'val': return 0
        lv = 1+max((visit(c, path+(i,)) for i,c in enumerate(n.args)),default=0)
        raw.append((lv,path,n))
        return lv
    visit(root,())
    raw.sort(key=lambda x:(x[0],x[1]))
    by_path = {path:i for i,(_,path,_) in enumerate(raw,start=1)}
    result=[]
    for level,path,node in raw:
        deps=[]; sources=[]
        for i, child in enumerate(node.args):
            child_path=path+(i,)
            if child.op == 'val': sources.append(child.value)
            else: deps.append(by_path[child_path])
        result.append(Task(by_path[path],node.op,display(node),level,tuple(deps),tuple(sources),path))
    return result


def _critical_lengths(tasks, settings):
    children={t.id:[] for t in tasks}
    for t in tasks:
        for dep in t.dependencies: children[dep].append(t.id)
    by_id={t.id:t for t in tasks}; memo={}
    def walk(i):
        if i not in memo:
            memo[i]=settings.duration(by_id[i].op)+max((walk(j) for j in children[i]),default=0)
        return memo[i]
    return {t.id:walk(t.id) for t in tasks}


def _first_free(busy, earliest, length):
    if length <= 0: return earliest
    t=earliest
    while True:
        overlap = next(((a,b) for a,b in sorted(busy) if t < b and t+length > a), None)
        if overlap is None: return t
        t=overlap[1]


def _schedule(expr, tasks, settings):
    done={}
    used=set()
    words=[]
    segments=[]
    bank_history={b:[] for b in range(1,settings.banks+1)}
    owners={b:0 for b in bank_history}
    crit=_critical_lengths(tasks,settings)
    time=0
    tasks_by_id={t.id:t for t in tasks}
    while len(done) < len(tasks):
        available=[t for t in tasks if t.id not in done and all(d in done for d in t.dependencies)]
        if not available: raise RuntimeError('У графі знайдено циклічну залежність.')
        if settings.policy=='critical':
            available.sort(key=lambda t:(-crit[t.id],t.id))
        else: available.sort(key=lambda t:t.id)
        picks=available[:settings.processors]
        assignment=[]; pe_free=set(range(1,settings.processors+1))
        for t in picks:
            def pe_rank(pe):
                local=sum(1 for d in t.dependencies if done[d].pe==pe)
                return (-local,pe)
            pe=min(pe_free,key=pe_rank)
            assignment.append((t,pe)); pe_free.remove(pe)

        current=[]
        for t,pe in assignment:
            phases=[]
            cursor=time
            local={d for d in t.dependencies if done[d].pe == pe}
            remote=[d for d in t.dependencies if d not in local]
            read_reqs=[]
            if t.sources:
                read_reqs.append(('Початкові операнди: '+', '.join(t.sources),None))
            for d in remote:
                read_reqs.append((f'Результат R{d}',done[d].result_bank))

            for desc,fixed_bank in read_reqs:
                if settings.read == 0: continue
                if fixed_bank is None:
                    candidates=list(range(1,settings.banks+1))
                else: candidates=[fixed_bank]
                choices=[(_first_free(bank_history[b],cursor,settings.read), owners[b], b) for b in candidates]
                st,_,b=min(choices)
                en=st+settings.read
                bank_history[b].append((st,en))
                owners[b]+=1
                seg=Segment('read',st,en,pe,b,t.id,desc)
                phases.append(seg); segments.append(seg)
                cursor=en
            d=settings.duration(t.op)
            seg=Segment('execute',cursor,cursor+d,pe,None,t.id,t.expression)
            phases.append(seg); segments.append(seg)
            cursor+=d
            if settings.write:
                choices=[(_first_free(bank_history[b],cursor,settings.write),owners[b],b)
                         for b in range(1,settings.banks+1)]
                st,_,bank=min(choices)
                en=st+settings.write
                bank_history[bank].append((st,en))
                owners[bank]+=1
                seg=Segment('write',st,en,pe,bank,t.id,'Запис результату')
                phases.append(seg); segments.append(seg)
                cursor=en
            else:
                bank=min(bank_history,key=lambda b:(owners[b],b))
            current.append(Scheduled(t,pe,len(words)+1,time,cursor,bank,phases))
        end=max(j.end for j in current)
        word=Word(len(words)+1,time,end,current)
        words.append(word)
        for j in current: done[j.task.id]=j
        time=end
    busy_compute=sum(settings.duration(t.op) for t in tasks)
    return words,segments,time,busy_compute


def validate_schedule(tasks: list[Task], words: list[Word], segments: list[Segment],
                      settings: Settings, total: int) -> None:
    expected = {task.id: task for task in tasks}
    seen = {}
    pe_slots = {pe: [] for pe in range(1, settings.processors + 1)}
    bank_slots = {bank: [] for bank in range(1, settings.banks + 1)}
    prev_end = 0
    phase_ids = set()
    for number, word in enumerate(words, 1):
        if word.number != number or word.start != prev_end or word.end <= word.start:
            raise ValueError('Некоректні межі командних слів VLIW.')
        occupied = set()
        if not word.jobs or len(word.jobs) > settings.processors:
            raise ValueError('Некоректна кількість операцій у командному слові.')
        for job in word.jobs:
            task = job.task
            if task.id not in expected or task.id in seen:
                raise ValueError('Повторена або невідома операція R у розкладі.')
            if job.word != number or job.pe not in pe_slots or job.pe in occupied:
                raise ValueError('Конфлікт процесорів у командному слові.')
            occupied.add(job.pe)
            if job.start != word.start or not (job.start < job.end <= word.end):
                raise ValueError('Некоректні часові межі операції.')
            for dep in task.dependencies:
                if dep not in seen or seen[dep].word >= number or seen[dep].end > job.start:
                    raise ValueError(f'Порушена залежність R{dep} → R{task.id}.')
            phases = job.phases
            if not phases or phases[-1].end != job.end:
                raise ValueError('Неповні фази операції.')
            cursor = job.start
            executes = 0
            for phase in phases:
                if phase.pe != job.pe or phase.task != task.id or phase.start < cursor or phase.end <= phase.start:
                    raise ValueError('Некоректна фаза виконання операції.')
                if phase.kind == 'execute':
                    executes += 1
                    if phase.end - phase.start != settings.duration(task.op):
                        raise ValueError('Неправильна тривалість арифметичної операції.')
                elif phase.kind in ('read', 'write'):
                    if phase.bank not in bank_slots:
                        raise ValueError('Некоректний номер банку пам’яті.')
                    if phase.end-phase.start != getattr(settings, phase.kind):
                        raise ValueError('Неправильна тривалість звернення до пам’яті.')
                    bank_slots[phase.bank].append((phase.start,phase.end,task.id))
                else:
                    raise ValueError('Невідомий тип фази.')
                phase_ids.add(id(phase))
                cursor = phase.end
            if executes != 1:
                raise ValueError('Кожна операція повинна мати одну фазу обчислення.')
            pe_slots[job.pe].append((job.start,job.end,task.id))
            seen[task.id] = job
        if max(job.end for job in word.jobs) != word.end:
            raise ValueError('Кінець слова не відповідає операціям.')
        prev_end = word.end
    if set(seen) != set(expected) or prev_end != total:
        raise ValueError('Не всі операції завершені або неправильний Tp.')
    if len(segments) != len(phase_ids) or {id(p) for p in segments} != phase_ids:
        raise ValueError('Фази діаграми не збігаються з командними словами.')
    for resource in [*pe_slots.values(),*bank_slots.values()]:
        intervals = sorted(resource)
        for first, second in zip(intervals, intervals[1:]):
            if first[1] > second[0]:
                raise ValueError('Накладання операцій на одному ресурсі.')


def simulate(expr: str, settings: Settings = Settings()) -> Simulation:
    settings.validate()
    if len(expr)>4000: raise ValueError('Вираз занадто великий (максимум 4000 символів).')
    root=effective_tree(expr,settings.use_lab2)
    tasks=graph_from_tree(root)
    if len(tasks)>200:
        raise ValueError('Для наочного моделювання дозволено до 200 операцій.')
    if not tasks: raise ValueError('У виразі немає арифметичних операцій для моделювання.')
    words,segs,total,busy = _schedule(expr,tasks,settings)
    validate_schedule(tasks,words,segs,settings,total)
    single=Settings(1,settings.banks,settings.plus,settings.minus,settings.multiply,
                    settings.divide,settings.read,settings.write,settings.policy,settings.use_lab2)
    _,_,baseline,_=_schedule(expr,tasks,single)
    speedup=baseline/total if total else 1.0
    eff=speedup/settings.processors
    lines=[f'R{t.id}: {t.expression}   | {t.op} | ярус {t.level} | ' +
           ('після '+', '.join('R'+str(d) for d in t.dependencies) if t.dependencies else 'незалежна')
           for t in tasks]
    return Simulation(expr,settings,tasks,words,segs,total,baseline,speedup,eff,busy,lines,display(root),
       'Умовні такти. 1 пакет читання на операцію з початковими даними; однопортові банки; '\
       'результати доступні локально на ПЕ і через банк пам’яті.',{})


def summary(sim: Simulation) -> str:
    s=sim.settings
    parts=[f'Вхідний вираз: {sim.expression}', f'Форма дерева для моделювання: {sim.modeled_expression}',
           'Пріоритет планування: '+({'id':'За номером R','critical':'За критичним шляхом'}[s.policy]),
           'Режим дерева: '+('Паралельна форма ЛР2' if s.use_lab2 else 'Початковий вираз'),
           f'Архітектура: VLIW; ПЕ: {s.processors}; банки: {s.banks}',
           f'Операцій: {len(sim.tasks)}; командних слів: {len(sim.words)}',
           f'Час T1 (1 ПЕ): {sim.sequential} тактів',
           f'Час Tp ({s.processors} ПЕ): {sim.total} тактів',
           f'Прискорення S = T1/Tp = {sim.speedup:.3f}',
           f'Ефективність E = S/P = {sim.efficiency:.3f} ({sim.efficiency*100:.1f}%)',
           f'Завантаження обчислювальних блоків: {sim.busy_compute/(s.processors*sim.total)*100:.1f}%',
           '', 'КОМАНДНІ СЛОВА:']
    for w in sim.words:
        parts.append(f'Слово {w.number:02d} [{w.start}; {w.end}): '+', '.join(
          f'ПЕ{j.pe}=R{j.task.id} ({j.task.op}, {j.start}–{j.end})' for j in w.jobs))
    if sim.comparison:
        parts.extend(['', 'ПОРІВНЯННЯ ПЛАНУВАЛЬНИКІВ:',
            f'За номером R: Tp={sim.comparison["id"][0]}, слів={sim.comparison["id"][1]}',
            f'За критичним шляхом: Tp={sim.comparison["critical"][0]}, слів={sim.comparison["critical"][1]}',
            'Обрано швидший із двох розкладів; глобальний оптимум не гарантується.'])
    parts.extend(['', 'ГРАФ ОПЕРАЦІЙ:',*sim.graph_lines,'',sim.note])
    return '\n'.join(parts)
