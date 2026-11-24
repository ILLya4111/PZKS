"""Автоматичні тести. Запуск: python -m unittest lab5.test_model -v"""
import unittest
from lab5.model import Settings, EXAMPLE, graph_from_tree, parse_and_validate, simulate

class ModelTests(unittest.TestCase):
    def test_reference_graph(self):
        t=graph_from_tree(parse_and_validate(EXAMPLE))
        self.assertEqual(len(t),7)
        self.assertEqual([x.op for x in t],['+','-','*','+','*','/','+'])
        self.assertEqual(t[-1].dependencies,(5,6))

    def test_metrics_reference(self):
        result=simulate(EXAMPLE)
        self.assertEqual(result.settings.processors,6)
        self.assertEqual(result.settings.banks,3)
        self.assertEqual(result.sequential,36)
        self.assertEqual(len(result.words),3)
        self.assertEqual(result.words[-1].jobs[-1].task.id,7)
        self.assertGreater(result.total,0)
        self.assertGreater(result.speedup,0)
        self.assertAlmostEqual(result.efficiency,result.speedup/6)

    def test_one_processor(self):
        sim=simulate('a+b*c',Settings(processors=1,banks=3))
        self.assertEqual(sim.total,sim.sequential)
        self.assertAlmostEqual(sim.speedup,1)
        self.assertAlmostEqual(sim.efficiency,1)

    def test_independent_in_one_word(self):
        sim=simulate('a*b+c*d+e*f+g*h',Settings(processors=6,banks=3))
        self.assertGreaterEqual(len(sim.words),2)
        self.assertEqual(len(sim.words[0].jobs),4)

    def test_memory_bank_conflicts(self):
        sim=simulate('a*b+c*d+e*f+g*h',Settings(processors=6,banks=3))
        for bank in range(1,sim.settings.banks+1):
            slots=sorted((s.start,s.end) for s in sim.segments if s.bank==bank)
            for a,b in zip(slots,slots[1:]):
                self.assertLessEqual(a[1],b[0])

    def test_dependencies_in_previous_words(self):
        sim=simulate(EXAMPLE)
        assignments={j.task.id:j.word for w in sim.words for j in w.jobs}
        for t in sim.tasks:
            for dep in t.dependencies:
                self.assertLess(assignments[dep],assignments[t.id])

    def test_invalid(self):
        for expr in ('a/(b-b)','a++b','a**b','sin(a)','A[++i]'):
            with self.subTest(expr=expr):
                with self.assertRaises(ValueError): simulate(expr)

    def test_unary_minus(self):
        sim=simulate('-(a-b)*(c-d)')
        self.assertGreater(len(sim.tasks),2)

    def test_critical_policy(self):
        r=simulate(EXAMPLE,Settings(policy='critical'))
        self.assertEqual(len(r.tasks),7)
        self.assertEqual(r.sequential,36)

    def test_zero_mem_latency(self):
        s=Settings(read=0,write=0)
        sim=simulate('(a+b)*(c+d)',s)
        self.assertEqual(sim.sequential,8)
        self.assertLessEqual(sim.total,sim.sequential)

if __name__=='__main__':unittest.main()

class AutoAndIntegrityTests(unittest.TestCase):
    def test_integrity_detects_overlapping_bank_phases(self):
        from lab5.model import validate_schedule, Segment
        sim = simulate('(a+b)*(c+d)', Settings(processors=2, banks=1))
        target = next(x for x in sim.segments if x.kind == 'read')
        # Alter the bank assignment in-place through frozen-dataclass replacement;
        # the same list is shared by words and segment table.
        other = next(x for x in sim.segments if x.kind == 'read' and x is not target)
        from dataclasses import replace
        overlapping = replace(other, start=target.start, end=target.end)
        job = next(j for w in sim.words for j in w.jobs if other in j.phases)
        job.phases[job.phases.index(other)] = overlapping
        sim.segments[sim.segments.index(other)] = overlapping
        with self.assertRaises(ValueError):
            validate_schedule(sim.tasks, sim.words, sim.segments, sim.settings, sim.total)

    def test_all_examples_both_priorities(self):
        for label, expr in __import__('lab5.model', fromlist=['EXAMPLES']).EXAMPLES:
            for count, banks in ((1,1), (2,1), (6,3)):
                with self.subTest(label=label, count=count, banks=banks):
                    for policy in ('id','critical'):
                        simulate(expr, Settings(processors=count, banks=banks, policy=policy))
