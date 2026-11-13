import tkinter as tk
from tkinter import ttk
from integration import validate_with_previous_labs, zero_denominators
from transformations import (ASSOCIATIVE_TESTS, DISTRIBUTIVE_TESTS, ParseError,
    parse, generate, display, height, count_operations, validate_equivalent,
    form_sort_key, distribution_remaining)


class Window:
    def __init__(self, root):
        self.root = root
        root.title('ПЗКС · Лабораторні №3–4 · Еквівалентні форми')
        root.geometry('1240x800')
        root.minsize(880, 600)
        self.mode = tk.StringVar(value='factor')
        self.test = tk.StringVar()
        self.forms = []
        self.original = None
        self.visible_indices = []

        top = ttk.Frame(root, padding=12)
        top.pack(fill='x')
        ttk.Label(top, text='Генерація еквівалентних форм арифметичного виразу',
                  font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(top, text='ЛР3 — винесення спільних множників; ЛР4 — розкриття дужок').pack(anchor='w', pady=(0, 10))
        modeframe = ttk.Frame(top)
        modeframe.pack(fill='x')
        ttk.Radiobutton(modeframe, text='ЛР3 · Асоціативний (винесення за дистрибутивністю)', variable=self.mode,
                        value='factor', command=self.change_mode).pack(side='left', padx=(0, 16))
        ttk.Radiobutton(modeframe, text='ЛР4 · Дистрибутивний (розкриття)', variable=self.mode,
                        value='distribute', command=self.change_mode).pack(side='left')
        self.testbox = ttk.Combobox(top, textvariable=self.test, state='readonly')
        self.testbox.pack(fill='x', pady=(10, 5))
        self.testbox.bind('<<ComboboxSelected>>', self.select_test)
        self.source = tk.Text(top, height=3, font=('Consolas', 12), wrap='word', undo=True)
        self.source.pack(fill='x')
        self.source.tag_configure('invalid', background='#ffe2e2', foreground='#9a2020')
        self._loading_example = False
        self.source.bind('<<Modified>>', self.source_modified)

        def paste_formula(event=None):
            try:
                value = self.root.clipboard_get()
            except tk.TclError:
                return 'break'
            if self.source.tag_ranges('sel'):
                self.source.delete('sel.first', 'sel.last')
            self.source.insert('insert', value)
            return 'break'

        def select_all(event=None):
            self.source.tag_add('sel', '1.0', 'end-1c')
            self.source.mark_set('insert', 'end-1c')
            return 'break'

        def keyboard_shortcuts(event):
            if self.root.focus_get() is not self.source or not (event.state & 0x0004):
                return
            key = str(event.keysym).lower()
            # 86/65: фізичні V/A в Windows, незалежно від розкладки.
            if key in ('v', 'cyrillic_ve') or event.keycode == 86:
                return paste_formula(event)
            if key in ('a', 'cyrillic_ef') or event.keycode == 65:
                return select_all(event)

        self.source.bind('<Control-KeyPress>', keyboard_shortcuts)
        self.source.bind('<Shift-Insert>', paste_formula)
        commands = ttk.Frame(top)
        commands.pack(fill='x', pady=(9, 0))
        ttk.Button(commands, text='Згенерувати форми', command=self.calculate).pack(side='left')
        self.display_limit = 20
        self.search_depth = 5
        self.search_limit = 160
        self.search_budget = 1400
        self.summary = ttk.Label(top, text='Вибери тест або введи власний вираз.')
        self.summary.pack(anchor='w', pady=(9, 0))

        main = ttk.Frame(root, padding=(12, 0, 12, 12))
        main.pack(fill='both', expand=True)
        lstframe = ttk.LabelFrame(main, text='Еквівалентні форми (за критерієм обраної лабораторної)', padding=7)
        lstframe.pack(fill='both', expand=True)
        columns = ('number', 'levels', 'ops', 'step', 'formula')
        self.table = ttk.Treeview(lstframe, columns=columns, show='headings', selectmode='browse')
        for col, title, width in [('number', '№', 50), ('levels', 'Ярусів', 70),
                                  ('ops', 'Операцій', 80), ('step', 'Крок', 60),
                                  ('formula', 'Аналітична форма', 800)]:
            self.table.heading(col, text=title)
            self.table.column(col, width=width, stretch=(col == 'formula'), anchor='w')
        scroll_y = ttk.Scrollbar(lstframe, orient='vertical', command=self.table.yview)
        scroll_x = ttk.Scrollbar(lstframe, orient='horizontal', command=self.table.xview)
        self.table.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.table.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')
        lstframe.columnconfigure(0, weight=1)
        lstframe.rowconfigure(0, weight=1)
        self.table.bind('<<TreeviewSelect>>', self.choose)
        detailsframe = ttk.LabelFrame(main, text='Вибрана форма — повний запис і перевірка', padding=7)
        detailsframe.pack(fill='x', pady=(9, 0))
        self.details = tk.Text(detailsframe, height=7, font=('Consolas', 11), wrap='word', state='disabled')
        self.details.pack(fill='x')
        self.change_mode()

    def change_mode(self):
        tests = ASSOCIATIVE_TESTS if self.mode.get() == 'factor' else DISTRIBUTIVE_TESTS
        self.testbox['values'] = list(tests)
        self.testbox.current(0)
        self.select_test()
        for item in self.table.get_children():
            self.table.delete(item)
        self.forms = []
        self.summary.config(text='Вибери тест або введи власний вираз.')
        self.put_details('')

    def source_modified(self, event=None):
        if not self.source.edit_modified():
            return
        self.source.edit_modified(False)
        if self._loading_example:
            return
        tests = ASSOCIATIVE_TESTS if self.mode.get() == 'factor' else DISTRIBUTIVE_TESTS
        current = self.test.get()
        if current in tests and self.source.get('1.0', 'end-1c') != tests[current]:
            self.test.set('Власний вираз')

    def select_test(self, event=None):
        tests = ASSOCIATIVE_TESTS if self.mode.get() == 'factor' else DISTRIBUTIVE_TESTS
        expr = tests.get(self.test.get(), next(iter(tests.values())))
        self._loading_example = True
        try:
            self.source.delete('1.0', 'end')
            self.source.insert('1.0', expr)
            self.source.tag_remove('invalid', '1.0', 'end')
            self.source.edit_modified(False)
        finally:
            self._loading_example = False

    def put_details(self, text):
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', text)
        self.details.configure(state='disabled')

    def show_errors(self, issues):
        self.forms = []
        self.visible_indices = []
        for item in self.table.get_children():
            self.table.delete(item)
        self.source.tag_remove('invalid', '1.0', 'end')
        text = self.source.get('1.0', 'end-1c')
        lines = ['ПОМИЛКИ ВХІДНОГО ВИРАЗУ:']
        for index, (start, end, description) in enumerate(issues, 1):
            if start is None:
                lines.append(f'{index}. {description}')
                continue
            if end <= start and len(text) > 0:
                start, end = max(0, start-1), max(1, start)
            start = min(max(0, start), len(text))
            end = min(max(start, end), len(text))
            self.source.tag_add('invalid', f'1.0+{start}c', f'1.0+{end}c')
            lines.append(f'{index}. Позиція {start + 1}: {description}')
        self.summary.config(text=f'Виявлено помилок: {len(issues)}. Генерацію форм скасовано.')
        self.put_details('\n'.join(lines))

    def calculate(self):
        expr = self.source.get('1.0', 'end-1c')
        self.source.tag_remove('invalid', '1.0', 'end')
        issues = validate_with_previous_labs(expr)
        if issues:
            self.show_errors(issues)
            return
        try:
            self.original = parse(expr)
            bad_divisors = zero_denominators(self.original)
            if bad_divisors:
                self.show_errors([(None, None,
                     'Ділення на нуль: знаменник ' + divisor + ' дорівнює нулю')
                     for divisor in bad_divisors])
                return
            self.forms = generate(self.original, self.mode.get(),
                                  limit=self.search_limit,
                                  max_depth=self.search_depth,
                                  search_budget=self.search_budget)
        except (ParseError, ValueError, RecursionError) as exc:
            self.show_errors([(None, None, f'Помилка обробки: {exc}')])
            return
        for item in self.table.get_children():
            self.table.delete(item)
        self.visible_indices = sorted(range(len(self.forms)),
             key=lambda i: (*form_sort_key(self.forms[i], self.mode.get()), i))[:self.display_limit]
        for rank, index in enumerate(self.visible_indices, start=1):
            f = self.forms[index]
            self.table.insert('', 'end', iid=str(index), values=(rank, height(f.tree),
                        count_operations(f.tree), f.step, display(f.tree)))
        if not self.visible_indices:
            self.summary.config(text='Для цього виразу не вдалося сформувати результати.')
            self.put_details('')
            return
        best = self.forms[self.visible_indices[0]]
        if self.mode.get() == 'distribute':
            best_sites = distribution_remaining(best.tree)
            self.summary.config(text=
                f'Показано форм: {len(self.visible_indices)} із {len(self.forms)} відібраних  |  '
                f'Кроків розкриття у вибраній формі: {best.step}  |  '
                f'Місць для подальшого розкриття: {best_sites}  |  '
                + ('Для цієї форми розкриття завершено' if best_sites == 0 else
                 'Пошук обмежений: повне розкриття не гарантоване'))
        else:
            comment = ('Не знайдено спільних множників для винесення за правилом ЛР3.'
                       if len(self.forms) == 1 else
                       'Пошук обмежений: глобальний оптимум не гарантований')
            self.summary.config(text=f'Показано найкращих форм: {len(self.visible_indices)} із {len(self.forms)} відібраних  |  '
                f'Початкова висота: {height(self.original)}  →  найменша знайдена: {height(best.tree)}  |  '
                f'Операцій: {count_operations(self.original)}  →  {count_operations(best.tree)}  |  '
                + comment)
        self.table.selection_set(str(self.visible_indices[0]))
        self.table.focus(str(self.visible_indices[0]))
        self.table.see(str(self.visible_indices[0]))
        self.choose()

    def choose(self, event=None):
        selected = self.table.selection()
        if not selected or not self.forms:
            return
        i = int(selected[0])
        f = self.forms[i]
        status, explanation = validate_equivalent(self.original, f.tree)
        chain = []
        current = i
        while current is not None:
            x = self.forms[current]
            if x.parent is not None:
                chain.append(f'Крок {x.step}: {x.rule}')
            current = x.parent
        chain.reverse()
        self.put_details(f'ФОРМУЛА:\n{display(f.tree)}\n\n'
            f'Ярусів: {height(f.tree)}  |  Операцій: {count_operations(f.tree)}\n'
            f'ПЕРЕТВОРЕННЯ: ' + ('; '.join(chain) if chain else 'Початковий вираз') + '\n'
            f'ПЕРЕВІРКА: {explanation}')


def run():
    root = tk.Tk()
    Window(root)
    root.mainloop()
