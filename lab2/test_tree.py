import unittest
from lab2.tree_builder import build_tree, operation_metrics, operation_levels

class ParallelTreeTests(unittest.TestCase):
    def test_main(self):
        for s in ['a+b+c+d+e+f+g+h','a-b-c-d-e-f-g-h','a/b/c/d/e/f/g/h',
                  'a*(b-4) - 2*b*c - c*d - a*c*d/e/f/g - g-h-i-j',
                  'a+(b+c+d+(e+f)+g)+h','a-((b-c-d)-(e-f)-g)-h']:
            result, errors = build_tree(s)
            self.assertFalse(errors, s)
            self.assertGreaterEqual(operation_metrics(result['tree'])[0], 1)
        result, _ = build_tree('a+b+c+d+e+f+g+h')
        self.assertEqual(operation_metrics(result['tree']), (3,4))
        self.assertEqual([len(v) for v in operation_levels(result['tree']).values()], [4,2,1])
        for expression in ['a-b-c-d-e-f-g-h', 'a/b/c/d/e/f/g/h']:
            result, _ = build_tree(expression)
            self.assertEqual(operation_metrics(result['tree']), (3,4))
            self.assertTrue(result['equivalence']['valid'])

    def test_numeric_keeps_tree(self):
        for s, expected in [('5040/8/7/6/5/4/3/2','0.125'),
                            ('10-9-8-7-6-5-4-3-2-1','-35'),
                            ('64-(32-16)-8-(4-2-1)','39')]:
            with self.subTest(s=s):
                result, errors = build_tree(s)
                self.assertFalse(errors)
                self.assertEqual(result['numeric_result'],expected)
                self.assertTrue(result['tree'].children)
                self.assertTrue(result['equivalence']['valid'])

    def test_simplification_and_zero(self):
        result, errors = build_tree('-(-i)/1.0 + 0 - 0*k*h + 2 - 4.8/2 + 1*e/2')
        self.assertFalse(errors)
        self.assertEqual(operation_metrics(result['tree'])[0], 2)
        result, errors = build_tree('a*2/0 + b/(b+b*0-1*b) - 1/(c*2*4.76*(1-2+1))')
        self.assertFalse(errors)
        self.assertEqual(result['zero_divisions'],3)
        self.assertEqual(len(result['zero_details']),3)

    def test_invalid(self):
        for s in ['a++b','a*/b','2x','f(a,)']:
            self.assertTrue(build_tree(s)[1])

if __name__ == '__main__':
    unittest.main()
