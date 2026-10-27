"""Графічна побудова дерева ПЗКС ЛР2 (Tkinter)."""
import tkinter as tk
from tkinter import ttk
try:
    from .tree_builder import build_tree, operation_levels, operation_metrics, expression_text
except ImportError:
    from tree_builder import build_tree, operation_levels, operation_metrics, expression_text

EXAMPLES = [
 ('М1 · паралельне додавання','a+b+c+d+e+f+g+h'),
 ('М2 · паралельне віднімання','a-b-c-d-e-f-g-h'),
 ('М3 · паралельне ділення','a/b/c/d/e/f/g/h'),
 ('М4 · пріоритети','a*(b-4) - 2*b*c - c*d - a*c*d/e/f/g - g-h-i-j'),
 ('P1 · дужки з плюсом','a+(b+c+d+(e+f)+g)+h'),
 ('P2 · дужки з мінусом','a-((b-c-d)-(e-f)-g)-h'),
 ('E1 · числове ділення','5040/8/7/6/5/4/3/2'),
 ('E2 · числове віднімання','10-9-8-7-6-5-4-3-2-1'),
 ('E3 · дужки і константи','64-(32-16)-8-(4-2-1)'),
 ('S1 · спрощення','-(-i)/1.0 + 0 - 0*k*h + 2 - 4.8/2 + 1*e/2'),
 ('S2 · ділення на нуль','a*2/0 + b/(b+b*0-1*b) - 1/(c*2*4.76*(1-2+1))'),
]

W, H, HG, VG = 84, 38, 18, 85

def label(n):
    if n.op == 'neg': return '−'
    if n.op == 'inv': return '1/x'
    if n.op.startswith('call:'): return n.op[5:] + '()'
    return n.op

def coords(root):
    pos = {}
    leaf = 0
    def walk(n, depth):
        nonlocal leaf
        if not n.children:
            x = 30 + leaf * (W + HG)
            leaf += 1
        else:
            xs = [walk(c, depth + 1) for c in n.children]
            x = (xs[0] + xs[-1]) / 2
        pos[id(n)] = (x, 40 + depth * VG)
        return x
    walk(root, 0)
    return pos, max(x for x,y in pos.values())+W+40, max(y for x,y in pos.values())+H+40

def render(canvas, root):
    """Малює дерево в доступній області Canvas, зменшуючи його за потреби."""
    canvas.delete('all')
    canvas.update_idletasks()
    points, total_w, total_h = coords(root)
    available_w = max(1, canvas.winfo_width() - 24)
    available_h = max(1, canvas.winfo_height() - 24)
    scale = min(1.0, available_w / total_w, available_h / total_h)

    # Якщо дерево надзвичайно велике, зберігаємо читабельний мінімум
    # масштабу і залишаємо прокручування.
    scale = max(0.28, scale)
    drawn_w, drawn_h = total_w * scale, total_h * scale
    offset_x = max(0, (canvas.winfo_width() - drawn_w) / 2)
    offset_y = max(0, (canvas.winfo_height() - drawn_h) / 2)
    node_w, node_h = W * scale, H * scale
    font_size = max(7, round(11 * scale))

    def point(n):
        x, y = points[id(n)]
        return offset_x + x * scale, offset_y + y * scale

    def visit(n):
        x, y = point(n)
        for child in n.children:
            cx, cy = point(child)
            canvas.create_line(x + node_w / 2, y + node_h,
                               cx + node_w / 2, cy,
                               fill='#344054', width=max(1, 2 * scale))
            visit(child)
        shape = canvas.create_oval if n.children else canvas.create_rectangle
        shape(x, y, x + node_w, y + node_h,
              outline='#4975b0' if n.children else '#667085',
              fill='#e7efff' if n.children else '#fafafa',
              width=max(1, 2 * scale))
        canvas.create_text(x + node_w / 2, y + node_h / 2,
                           text=label(n), font=('Segoe UI', font_size, 'bold'))

    visit(root)
    canvas.configure(scrollregion=(0, 0,
        max(canvas.winfo_width(), offset_x + drawn_w + 12),
        max(canvas.winfo_height(), offset_y + drawn_h + 12)))
    canvas.xview_moveto(0)
    canvas.yview_moveto(0)

def run():
    app = tk.Tk()
    app.title('ПЗКС · Лабораторна робота №2 · Паралельне дерево')
    app.geometry('1280x820')
    app.minsize(800,560)
    wrap = ttk.Frame(app,padding=14)
    wrap.pack(fill='both',expand=True)
    ttk.Label(wrap,text='Побудова паралельного дерева виразу',font=('Segoe UI',20,'bold')).pack(anchor='w')
    ttk.Label(wrap,text='Пріоритет операцій, балансування та спрощення виразу').pack(anchor='w',pady=(0,10))
    choices=ttk.Combobox(wrap,state='readonly',values=[name for name,_ in EXAMPLES])
    choices.current(0)
    choices.pack(fill='x')
    source=tk.Text(wrap,height=3,font=('Consolas',14),wrap='word',undo=True)
    source.pack(fill='x',pady=8)
    controls=ttk.Frame(wrap)
    controls.pack(fill='x',pady=(0,6))
    metrics=ttk.Label(wrap,text='',font=('Segoe UI',11,'bold'))
    metrics.pack(anchor='w',pady=(3,2))
    message=ttk.Label(wrap,text='',font=('Segoe UI',10),wraplength=1150)
    message.pack(anchor='w',pady=(0,7))
    area=ttk.Frame(wrap)
    area.pack(fill='both',expand=True)
    # Список незалежних операцій праворуч від графічного дерева.
    tiers=ttk.LabelFrame(wrap,text='Ярусно-паралельна форма',padding=8)
    tiers.pack(fill='x',pady=(8,0))
    tiers_text=tk.Text(tiers,height=6,font=('Consolas',10),wrap='word')
    tiers_text.pack(side='left',fill='both',expand=True)
    tiers_scroll=ttk.Scrollbar(tiers,orient='vertical',command=tiers_text.yview)
    tiers_scroll.pack(side='right',fill='y')
    tiers_text.configure(yscrollcommand=tiers_scroll.set,state='disabled')
    def display_tiers(node):
        lvls=operation_levels(node)
        lines=[f'Ярус {i} (операцій: {len(items)}): ' + '; '.join(expression_text(x) for x in items)
               for i,items in lvls.items()]
        if not lines: lines=['Операцій немає — лише один операнд.']
        tiers_text.configure(state='normal')
        tiers_text.delete('1.0','end')
        tiers_text.insert('1.0','\n'.join(lines))
        tiers_text.configure(state='disabled')

    area.rowconfigure(0,weight=1)
    area.columnconfigure(0,weight=1)
    canvas=tk.Canvas(area,bg='white',highlightbackground='#aab1bb',highlightthickness=1)
    canvas.grid(row=0,column=0,sticky='nsew')
    ys=ttk.Scrollbar(area,orient='vertical',command=canvas.yview)
    ys.grid(row=0,column=1,sticky='ns')
    xs=ttk.Scrollbar(area,orient='horizontal',command=canvas.xview)
    xs.grid(row=1,column=0,sticky='ew')
    canvas.configure(xscrollcommand=xs.set,yscrollcommand=ys.set)
    details=ttk.LabelFrame(wrap,text='Перевірка результатів / помилки',padding=6)
    details.pack(fill='x',pady=(5,0))
    details_text=tk.Text(details,height=4,font=('Consolas',10),wrap='word')
    details_text.pack(fill='x')
    details_text.configure(state='disabled')
    def set_details(value):
        details_text.configure(state='normal')
        details_text.delete('1.0','end')
        details_text.insert('1.0',value)
        details_text.configure(state='disabled')
    current=[None]
    resize_job=[None]

    def on_canvas_resize(event):
        if resize_job[0] is not None:
            app.after_cancel(resize_job[0])
        def redraw():
            resize_job[0] = None
            if current[0] is not None:
                render(canvas, current[0]['tree'])
        resize_job[0] = app.after(100, redraw)

    canvas.bind('<Configure>', on_canvas_resize)

    def show():
        data=current[0]
        if not data: return
        selected=data['tree']
        render(canvas,selected)
        layers, max_parallel = operation_metrics(selected)
        metrics.configure(text=f'Ярусів операцій: {layers}  |  Макс. паралельних операцій: {max_parallel}')
        display_tiers(selected)
        if data['zero_divisions']:
            message.configure(text=f'ПОМИЛКА: виявлено {data["zero_divisions"]} ділення на нуль. Дерево показано лише для діагностики.')
        elif data['numeric_result'] is not None:
            message.configure(text=f'Числовий результат: {data["numeric_result"]}. Показано дерево операцій до згортання констант.')
        else:
            message.configure(text='Вираз коректний. Показано паралельне дерево операцій.')
        if data['zero_details']:
            set_details('\n'.join(f'{i}. Ділення на нуль: знаменник {d["denominator"]}; після спрощення {d["simplified"]}'
                                   for i,d in enumerate(data['zero_details'],1)))
        elif data['equivalence']:
            eq=data['equivalence']
            if eq['kind']=='numeric':
                set_details(f'Початкове значення: {data["numeric_result"]}\nПісля перебудови: {data["numeric_result"] if eq["valid"] else eq["optimized"]}\nРівність результатів: {"так" if eq["valid"] else "НІ"}')
            else:
                set_details(f'Контрольна підстановка значень змінних: {"розбіжностей не знайдено" if eq["valid"] else "ЗНАЙДЕНО розбіжність"} (не математичний доказ).')
        else: set_details('')
    def check():
        canvas.delete('all')
        try:
            data,errors=build_tree(source.get('1.0','end-1c'))
            if errors:
                current[0]=None
                metrics.configure(text=f'Помилок у виразі: {len(errors)}')
                message.configure(text='; '.join(e.message for e in errors[:3]))
                return
            current[0]=data
            show()
        except (ValueError,RecursionError) as exc:
            current[0]=None
            metrics.configure(text='Не вдалося побудувати дерево')
            message.configure(text=str(exc))
    def load():
        source.delete('1.0','end')
        source.insert('1.0',EXAMPLES[choices.current()][1])
        check()
    ttk.Button(controls,text='Вставити приклад',command=load).pack(side='left',padx=(0,8))
    ttk.Button(controls,text='Побудувати дерево',command=check).pack(side='left')
    app.bind('<Control-Return>',lambda event:check())
    load()
    app.mainloop()
