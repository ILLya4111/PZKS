"""Інтерфейс стандартної бібліотеки Tkinter, окремий від аналізатора."""
import tkinter as tk
from tkinter import ttk
from analyzer import analyze
from examples import EXAMPLES


class App:
    def __init__(self, root):
        self.root = root
        root.title('ПЗКС · Лабораторна робота 1 · Аналізатор виразів')
        root.geometry('1080x760')
        root.minsize(760, 540)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        body = ttk.Frame(root, padding=20)
        body.grid(sticky='nsew')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(5, weight=1)
        ttk.Label(body, text='Аналізатор арифметичних виразів', font=('Segoe UI', 20, 'bold')).grid(sticky='w')
        ttk.Label(body, text='Лексичний і синтаксичний аналіз · Python · автомат станів та стек дужок').grid(sticky='w', pady=(4, 16))
        controls = ttk.Frame(body)
        controls.grid(sticky='ew')
        controls.columnconfigure(0, weight=1)
        self.choice = ttk.Combobox(controls, values=[name for name, _ in EXAMPLES], state='readonly')
        self.choice.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.choice.current(0)
        ttk.Button(controls, text='Вставити приклад', command=self.load_example).grid(row=0, column=1)
        self.entry = tk.Text(body, height=4, wrap='word', font=('Consolas', 15), undo=True, padx=10, pady=10)
        self.entry.grid(sticky='ew', pady=12)
        self.entry.tag_configure('error', background='#ffe0e0', foreground='#9d1515', underline=True)
        self.entry.tag_configure('selected_error', background='#ffd080', foreground='#422300')
        buttons = ttk.Frame(body)
        buttons.grid(sticky='ew', pady=(0, 12))
        ttk.Button(buttons, text='Перевірити', command=self.check).pack(side='left')
        self.status = ttk.Label(buttons, text='')
        self.status.pack(side='right')
        tabs = ttk.Notebook(body)
        tabs.grid(sticky='nsew')
        errors_panel = ttk.Frame(tabs)
        tokens_panel = ttk.Frame(tabs)
        rules_panel = ttk.Frame(tabs)
        tabs.add(errors_panel, text='Помилки')
        tabs.add(tokens_panel, text='Токени')
        tabs.add(rules_panel, text='Правила')
        errors_panel.columnconfigure(0, weight=1)
        errors_panel.rowconfigure(0, weight=1)
        self.errors_text = tk.Text(errors_panel, wrap='word', font=('Segoe UI', 11),
                                   padx=12, pady=10, cursor='arrow', state='disabled',
                                   width=1, height=1)
        self.errors_text.grid(row=0, column=0, sticky='nsew')
        errors_scroll = ttk.Scrollbar(errors_panel, orient='vertical', command=self.errors_text.yview)
        errors_scroll.grid(row=0, column=1, sticky='ns')
        self.errors_text.configure(yscrollcommand=errors_scroll.set)
        self.errors_text.tag_configure('heading', font=('Segoe UI', 11, 'bold'), spacing1=6)
        self.errors_text.tag_configure('description', lmargin1=12, lmargin2=12, spacing3=8)
        self.errors_text.tag_configure('selected', background='#fff0cc')
        self.tokens_table = self.make_table(tokens_panel, ('kind', 'value', 'position'),
            ('Тип токена', 'Значення', 'Позиції від 0'), (160, 520, 160))
        rules = tk.Text(rules_panel, wrap='word', font=('Segoe UI', 12), padx=15, pady=15)
        rules.pack(fill='both', expand=True)
        rules.insert('1.0', 'Ідентифікатори: латинська літера або _, далі літери, цифри, _.\n'
            'Числа: 123, 0.71, .71, 172. Десятковий роздільник — крапка.\n'
            'Операції: +, -, *, /. Унарний + або - дозволено на початку виразу, дужок чи аргументу.\n'
            'Після бінарного оператора знак потребує дужок: a+(-b), a*(-b). ++ і -- заборонено.\n'
            'Круглі дужки групують вирази. () заборонено, func() дозволено.\n'
            'Довільні функції: f(), sin(x), max(a,b), f(g(x),-y).\n'
            'Кома розділяє аргументи функції. Неявне множення заборонено: пишіть 2*x.\n'
            'Пробіли, табуляції та переноси рядків пропускаються між токенами.\n'
            'Позиції — абсолютні індекси символів від 0 у введеному тексті.\n'
            'Перевіряється запис виразу, а не його значення: 1/0 синтаксично коректне.\n'
            'Натисніть помилку у списку, щоб перейти до відповідного фрагмента.')
        rules.configure(state='disabled')
        ttk.Label(body, text='Червоне підкреслення позначає помилки. Для помилки в кінці курсор стає після останнього символу.').grid(sticky='w', pady=(10, 0))
        root.bind('<Control-Return>', lambda event: self.check())
        self.entry.bind('<<Modified>>', self.on_edit)
        self.last_source = None
        self.errors = []
        self.load_example()

    @staticmethod
    def make_table(parent, columns, labels, widths):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        table = ttk.Treeview(parent, columns=columns, show='headings', selectmode='browse')
        for column, label, width in zip(columns, labels, widths):
            table.heading(column, text=label)
            table.column(column, width=width, minwidth=80)
        table.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(parent, orient='vertical', command=table.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(parent, orient='horizontal', command=table.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        return table

    def source(self):
        return self.entry.get('1.0', 'end-1c')

    def on_edit(self, event=None):
        if self.entry.edit_modified():
            self.entry.tag_remove('error', '1.0', 'end')
            self.entry.tag_remove('selected_error', '1.0', 'end')
            self.clear_errors()
            self.tokens_table.delete(*self.tokens_table.get_children())
            self.status.configure(text='Вираз змінено — натисніть «Перевірити»')
            self.last_source = None
            self.entry.edit_modified(False)

    def load_example(self):
        self.entry.delete('1.0', 'end')
        self.entry.insert('1.0', EXAMPLES[self.choice.current()][1])
        self.entry.edit_modified(False)
        self.check()

    def check(self):
        source = self.source()
        self.entry.edit_modified(False)
        tokens, self.errors = analyze(source)
        self.last_source = source
        self.entry.tag_remove('error', '1.0', 'end')
        self.entry.tag_remove('selected_error', '1.0', 'end')
        self.clear_errors()
        self.tokens_table.delete(*self.tokens_table.get_children())
        for i, error in enumerate(self.errors):
            pos = str(error.start) if error.end <= error.start + 1 else f'{error.start}–{error.end-1}'
            tag = f'error_{i}'
            self.errors_text.configure(state='normal')
            self.errors_text.insert('end', f'{i + 1}. {error.category} · Позиція {pos} (від 0)\n',
                                    (tag, 'heading'))
            self.errors_text.insert('end', error.message + '\n', (tag, 'description'))
            self.errors_text.tag_bind(tag, '<Button-1>', lambda event, n=i: self.select_error(n))
            self.errors_text.configure(state='disabled')
            if error.end > error.start:
                self.entry.tag_add('error', f'1.0+{error.start}c', f'1.0+{error.end}c')
        for token in tokens:
            self.tokens_table.insert('', 'end', values=(token.kind, token.text, f'{token.start}–{token.end-1}'))
        if not self.errors:
            self.errors_text.configure(state='normal')
            self.errors_text.insert('end', 'Лексичних і синтаксичних помилок не виявлено.')
            self.errors_text.configure(state='disabled')
        self.errors_text.yview_moveto(0)
        self.status.configure(text=f'Помилок: {len(self.errors)}' if self.errors else 'Вираз коректний')

    def clear_errors(self):
        self.errors_text.configure(state='normal')
        self.errors_text.delete('1.0', 'end')
        for tag in self.errors_text.tag_names():
            if tag.startswith('error_'):
                self.errors_text.tag_delete(tag)
        self.errors_text.configure(state='disabled')

    def select_error(self, number):
        if self.last_source != self.source():
            return 'break'
        self.errors_text.tag_remove('selected', '1.0', 'end')
        bounds = self.errors_text.tag_ranges(f'error_{number}')
        if bounds:
            self.errors_text.tag_add('selected', bounds[0], bounds[-1])
        error = self.errors[number]
        index = f'1.0+{error.start}c'
        self.entry.tag_remove('selected_error', '1.0', 'end')
        self.entry.tag_add('selected_error', index, f'1.0+{error.end}c')
        self.entry.mark_set('insert', index)
        self.entry.see(index)
        self.entry.focus_set()
        return 'break'


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
