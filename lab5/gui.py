from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from lab5.model import EXAMPLES, Settings, Simulation, simulate

COLORS = {'read':'#64B5F6','execute':'#70C69E','write':'#F4A25A',
          'wait':'#E1E5EA','barrier':'#f7f7f7'}


class VLIWWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ПЗКС · ЛР5 · VLIW · Варіант №79')
        self.geometry('1400x810')
        self.minsize(980,640)
        self.option_add('*Font', '{Segoe UI} 10')
        self.current: Simulation | None = None
        self._internal_edit=False
        self._build()
        self.example_box.current(0)
        self.set_example()
        self.after(200,self.generate)

    def _build(self):
        root=ttk.Frame(self,padding=12)
        root.pack(fill='both',expand=True)
        ttk.Label(root,text='Моделювання виконання арифметичного виразу на VLIW',
                  font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(root,text='ЛР5 · Варіант 79 · 6 процесорних елементів · 3 банки пам’яті · командні слова та потактові ресурси').pack(anchor='w',pady=(0,8))
        settings=ttk.LabelFrame(root,text='Параметри системи (тривалість в умовних тактах)',padding=8)
        settings.pack(fill='x',pady=(0,7))
        self.param={}
        for j,(name,caption,default) in enumerate([
            ('processors','ПЕ',6),('banks','Банків',3),('+','+',2),('-','−',3),
            ('*','×',4),('/','÷',8),('read','Читання',1),('write','Запис',1)]):
            ttk.Label(settings,text=caption).grid(row=0,column=2*j,padx=(6,2),sticky='w')
            v=tk.IntVar(value=default)
            w=ttk.Spinbox(settings,from_=1 if name not in ('read','write') else 0,to=32 if name in ('processors','banks') else 100,
                           width=4,textvariable=v)
            w.grid(row=0,column=2*j+1,padx=(0,7),sticky='w')
            self.param[name]=v
        self.policy=tk.StringVar(value='id')
        ttk.Label(settings,text='Пріоритет').grid(row=1,column=0,columnspan=2,sticky='w',pady=(7,0))
        ttk.Combobox(settings,textvariable=self.policy,values=('За номером R','За критичним шляхом'),
                     state='readonly',width=21).grid(row=1,column=2,columnspan=5,sticky='w',pady=(7,0))
        self.policy.set('За номером R')

        inframe=ttk.LabelFrame(root,text='Вхідний вираз',padding=8)
        inframe.pack(fill='x',pady=(0,7))
        self.example=tk.StringVar()
        self.example_box=ttk.Combobox(inframe,textvariable=self.example,state='readonly',
                   values=[label for label,_ in EXAMPLES])
        self.example_box.pack(fill='x',pady=(0,4))
        self.example_box.bind('<<ComboboxSelected>>',self.set_example)
        self.formula=tk.Text(inframe,height=2,font=('Consolas',11),wrap='word',undo=True)
        self.formula.pack(fill='x')
        self.formula.bind('<<Modified>>',self._modified)
        self.formula.bind('<KeyPress>', self._formula_shortcuts)

        toolbar=ttk.Frame(root)
        toolbar.pack(fill='x',pady=(0,7))
        ttk.Button(toolbar,text='▶ Змоделювати VLIW',command=self.generate).pack(side='left')
        self.status=tk.StringVar(value='')
        ttk.Label(toolbar,textvariable=self.status,foreground='#344B63').pack(side='left',padx=12)

        metrics=ttk.Frame(root)
        metrics.pack(fill='x',pady=(0,8))
        self.metric_labels={}
        for i,(key,head) in enumerate([('ops','Операцій'),('words','Командних слів'),('t1','Послідовний час T1'),
                    ('tp','Час VLIW Tp'),('speed','Прискорення S'),('eff','Ефективність E')]):
            panel=ttk.LabelFrame(metrics,text=head,padding=(8,5))
            panel.pack(side='left',fill='x',expand=True,padx=(0,5))
            lab=ttk.Label(panel,text='—',font=('Segoe UI',15,'bold'))
            lab.pack(anchor='center')
            self.metric_labels[key]=lab

        self.notebook=ttk.Notebook(root)
        self.notebook.pack(fill='both',expand=True)
        self.tab_gantt=ttk.Frame(self.notebook,padding=6)
        self.tab_words=ttk.Frame(self.notebook,padding=6)
        self.tab_tasks=ttk.Frame(self.notebook,padding=6)
        self.notebook.add(self.tab_gantt,text='Часова діаграма ПЕ та пам’яті')
        self.notebook.add(self.tab_words,text='Командні слова VLIW')
        self.notebook.add(self.tab_tasks,text='Граф задач та залежності')
        self._create_gantt()
        self._create_words()
        self._create_tasks()

    def _modified(self,event):
        if self.formula.edit_modified():
            if not self._internal_edit:
                self.example.set('')
            self.formula.edit_modified(False)

    def _formula_shortcuts(self, event):
        if not (event.state & 0x0004):  # натиснуто Ctrl
            return None
        k = str(event.keysym).lower()
        a_pressed = k in ('a', 'cyrillic_ef') or (self.tk.call('tk', 'windowingsystem') == 'win32' and event.keycode == 65)
        v_pressed = k in ('v', 'cyrillic_em') or (self.tk.call('tk', 'windowingsystem') == 'win32' and event.keycode == 86)
        if a_pressed:
            return self._select_all(event)
        if v_pressed:
            return self._paste(event)
        return None

    def _select_all(self,event):
        self.formula.tag_add('sel','1.0','end-1c')
        self.formula.mark_set('insert','1.0')
        self.formula.see('insert')
        return 'break'

    def _paste(self,event):
        try: clip=self.clipboard_get()
        except tk.TclError: return 'break'
        try: self.formula.delete('sel.first','sel.last')
        except tk.TclError: pass
        self.formula.insert('insert',clip)
        return 'break'

    def set_example(self,event=None):
        val=self.example.get()
        for label,expr in EXAMPLES:
            if val==label:
                self._internal_edit=True
                self.formula.delete('1.0','end')
                self.formula.insert('1.0',expr)
                self.formula.edit_modified(False)
                self._internal_edit=False
                break

    def _create_gantt(self):
        parent=self.tab_gantt
        legend=ttk.Frame(parent);legend.pack(fill='x',pady=(1,5))
        for name,color in [('Читання (R)',COLORS['read']),('Обчислення',COLORS['execute']),('Запис (W)',COLORS['write']),('Очікування бар’єра',COLORS['wait'])]:
            swatch=tk.Canvas(legend,width=14,height=14,highlightthickness=0)
            swatch.create_rectangle(1,1,13,13,fill=color,outline='#888')
            swatch.pack(side='left',padx=(12,2))
            ttk.Label(legend,text=name).pack(side='left',padx=(0,9))
        frame=ttk.Frame(parent)
        frame.pack(fill='both',expand=True)
        self.gantt=tk.Canvas(frame,background='white',highlightthickness=1,highlightbackground='#CBD2DA')
        sx=ttk.Scrollbar(frame,orient='horizontal',command=self.gantt.xview)
        sy=ttk.Scrollbar(frame,orient='vertical',command=self.gantt.yview)
        self.gantt.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.gantt.grid(row=0,column=0,sticky='nsew')
        sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)

    def _create_words(self):
        panes=ttk.PanedWindow(self.tab_words,orient=tk.VERTICAL)
        panes.pack(fill='both',expand=True)
        frame=ttk.Frame(panes)
        panes.add(frame,weight=4)
        details=ttk.LabelFrame(panes,text='Пояснення вибраного командного слова',padding=6)
        panes.add(details,weight=2)
        cols=['word','start','end']+[f'pe{x}' for x in range(1,7)]
        self.word_tree=ttk.Treeview(frame,columns=cols,show='headings',height=12)
        for c,h,w in [('word','Слово',64),('start','Початок',80),('end','Кінець',80)]+[(f'pe{x}',f'ПЕ{x}',140) for x in range(1,7)]:
            self.word_tree.heading(c,text=h)
            self.word_tree.column(c,width=w,anchor='center' if c in ('word','start','end') else 'w',stretch=True)
        sy=ttk.Scrollbar(frame,orient='vertical',command=self.word_tree.yview)
        sx=ttk.Scrollbar(frame,orient='horizontal',command=self.word_tree.xview)
        self.word_tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        self.word_tree.grid(row=0,column=0,sticky='nsew')
        sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)
        self.word_tree.bind('<<TreeviewSelect>>',self._word_selected)

        self.details=tk.Text(details,height=6,wrap='word',font=('Consolas',10),state='disabled')
        detail_scroll=ttk.Scrollbar(details,orient='vertical',command=self.details.yview)
        self.details.configure(yscrollcommand=detail_scroll.set)
        self.details.grid(row=0,column=0,sticky='nsew')
        detail_scroll.grid(row=0,column=1,sticky='ns')
        details.columnconfigure(0,weight=1)
        details.rowconfigure(0,weight=1)

    def _create_tasks(self):
        frame=self.tab_tasks
        cols=['id','op','level','time','deps','expr']
        t=self.task_tree=ttk.Treeview(frame,columns=cols,show='headings')
        for c,h,w in [('id','R',65),('op','Операція',85),('level','Ярус',70),('time','Час',65),
                      ('deps','Залежності',150),('expr','Арифметичний підвираз',660)]:
            t.heading(c,text=h);t.column(c,width=w,stretch=True,anchor='w' if c in ('expr','deps') else 'center')
        sy=ttk.Scrollbar(frame,orient='vertical',command=t.yview)
        sx=ttk.Scrollbar(frame,orient='horizontal',command=t.xview)
        t.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        t.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)

    def _update_details(self,text):
        self.details.configure(state='normal')
        self.details.delete('1.0','end');self.details.insert('1.0',text)
        self.details.configure(state='disabled')

    def _word_selected(self,event=None):
        if self.current is None:return
        selected=self.word_tree.selection()
        if selected:
            try: n=int(selected[0])
            except ValueError:return
            self.show_word(n)

    def show_word(self,num):
        sim=self.current
        if sim is None or not 1<=num<=len(sim.words):return
        w=sim.words[num-1]
        text=f'СЛОВО {w.number} · [{w.start}; {w.end}) · {w.end-w.start} тактів\n'
        for j in w.jobs:
            p='; '.join(f'{s.kind.upper()} {s.start}–{s.end}' + (f' (Б{s.bank})' if s.bank else '') for s in j.phases)
            text+=f'ПЕ{j.pe} → R{j.task.id}: {j.task.expression}\n    {p}\n'
        absent=[f'ПЕ{p}' for p in range(1,sim.settings.processors+1) if p not in {j.pe for j in w.jobs}]
        if absent:text+='Простій на цьому слові: '+', '.join(absent)+'\n'
        text+='Наступне командне слово може стартувати тільки після завершення всіх фаз поточного.'
        self._update_details(text)

    def generate(self):
        expression=self.formula.get('1.0','end-1c').strip()
        try:
            s=Settings(self.param['processors'].get(),self.param['banks'].get(),
                self.param['+'].get(),self.param['-'].get(),self.param['*'].get(),
                self.param['/'].get(),self.param['read'].get(),self.param['write'].get(),
                'critical' if self.policy.get()=='За критичним шляхом' else 'id',
                True)
            sim=simulate(expression,s)
        except (ValueError,tk.TclError) as exc:
            self.status.set('Помилка: генерацію зупинено')
            self._update_details('ПОМИЛКА ВХІДНИХ ДАНИХ:\n'+str(exc))
            messagebox.showerror('Перевір вираз / налаштування',str(exc))
            return
        self.current=sim
        self.status.set(f'Готово: {len(sim.words)} командних слів; {len(sim.tasks)} операцій')
        for key,txt in [('ops',str(len(sim.tasks))),('words',str(len(sim.words))),
          ('t1',str(sim.sequential)),('tp',str(sim.total)),('speed',f'{sim.speedup:.3f}'),
          ('eff',f'{sim.efficiency*100:.1f}%')]:
            self.metric_labels[key].configure(text=txt)
        self._render_words();self._render_tasks();self._render_gantt()
        self.show_word(1)

    def _render_words(self):
        t=self.word_tree
        t.delete(*t.get_children())
        pe_count=self.current.settings.processors
        cols=['word','start','end']+[f'pe{x}' for x in range(1,pe_count+1)]
        t.configure(columns=cols)
        for c,h,wid in [('word','Слово',64),('start','Початок',80),('end','Кінець',80)]+[(f'pe{x}',f'ПЕ{x}',140) for x in range(1,pe_count+1)]:
            t.heading(c,text=h)
            t.column(c,width=wid,anchor='center' if c in ('word','start','end') else 'w',stretch=True)
        for w in self.current.words:
            mapped={j.pe:f'R{j.task.id}: {j.task.op}' for j in w.jobs}
            t.insert('', 'end', iid=str(w.number),values=[w.number,w.start,w.end]+[
                mapped.get(p,'—') for p in range(1,pe_count+1)])

    def _render_tasks(self):
        t=self.task_tree;t.delete(*t.get_children())
        for task in self.current.tasks:
            t.insert('', 'end',values=(f'R{task.id}',task.op,task.level,
                self.current.settings.duration(task.op),', '.join('R'+str(x) for x in task.dependencies) or '—',
                task.expression))

    def _render_gantt(self):
        canvas=self.gantt;canvas.delete('all')
        sim=self.current
        top=46; row=34; left=78; P=sim.settings.processors; B=sim.settings.banks
        tick=30 if sim.total<65 else max(5,min(22,int(1800/sim.total)))
        right=left+max(1,sim.total)*tick+70
        height=top+(P+B)*row+40
        canvas.create_text(10,13,anchor='w',text=f'Часова діаграма · {sim.total} тактів · 1 клітинка = 1 такт',font=('Segoe UI',10,'bold'))
        for w in sim.words:
            x0=left+w.start*tick;x1=left+w.end*tick
            if w.number%2==0:
                canvas.create_rectangle(x0,top-14,x1,height-25,fill='#F8FAFC',outline='')
            canvas.create_line(x0,top-14,x0,height-25,fill='#b8c1cd',dash=(4,3))
            if x1-x0>35:
                canvas.create_text((x0+x1)/2,top-24,text=f'Слово {w.number}',font=('Segoe UI',8))
        for p in range(P+B):
            y=top+p*row
            name=f'ПЕ{p+1}' if p<P else f'Б{p-P+1}'
            canvas.create_text(9,y+row/2,anchor='w',text=name,font=('Segoe UI',10,'bold'))
            canvas.create_line(left,y+row-3,right-20,y+row-3,fill='#E9EDF2')
        for t in range(0,sim.total+1):
            if tick>=16 or t%5==0:
                x=left+t*tick
                canvas.create_line(x,top-14,x,height-25,fill='#f0f2f4')
                canvas.create_text(x,top-3,text=str(t),font=('Segoe UI',8),anchor='s')
        for s in sim.segments:
            if s.end<=s.start:continue
            y=top+(s.pe-1)*row+6
            x0=left+s.start*tick;x1=left+s.end*tick
            canvas.create_rectangle(x0+1,y,x1-1,y+row-13,fill=COLORS[s.kind],outline='#7b899b')
            if x1-x0>25:
                canvas.create_text((x0+x1)/2,y+10,text=f'R{s.task}',font=('Segoe UI',8))
            if s.bank:
                by=top+(P+s.bank-1)*row+6
                canvas.create_rectangle(x0+1,by,x1-1,by+row-13,fill=COLORS[s.kind],outline='#7b899b')
                if x1-x0>25:
                    canvas.create_text((x0+x1)/2,by+10,text=f'R{s.task}',font=('Segoe UI',8))
        for w in sim.words:
            for j in w.jobs:
                if j.end<w.end:
                    x0=left+j.end*tick;x1=left+w.end*tick;y=top+(j.pe-1)*row+6
                    canvas.create_rectangle(x0+1,y,x1-1,y+row-13,fill=COLORS['wait'],outline='')
        canvas.create_line(left+sim.total*tick,top-14,left+sim.total*tick,height-25,fill='#34495e',width=2)
        canvas.configure(scrollregion=(0,0,right,height))
        canvas.xview_moveto(0);canvas.yview_moveto(0)


def run():
    app=VLIWWindow();app.mainloop()
