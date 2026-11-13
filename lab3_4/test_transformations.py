import unittest
from transformations import (parse, display, generate, height, count_operations,
                             validate_equivalent, ASSOCIATIVE_TESTS, DISTRIBUTIVE_TESTS)

class TestTransformations(unittest.TestCase):
    def test_parser_roundtrip(self):
        for expression in [*ASSOCIATIVE_TESTS.values(), *DISTRIBUTIVE_TESTS.values()]:
            self.assertEqual(validate_equivalent(parse(expression), parse(display(parse(expression))))[0], 'pass', expression)

    def test_associative_basic(self):
        f = [display(x.tree) for x in generate(parse('a*b+a*c'), 'factor')]
        self.assertTrue(any('a * (b + c)' in s for s in f), f)

    def test_associative_denominator(self):
        f = [display(x.tree) for x in generate(parse('a/b-c/b+2/b'), 'factor')]
        self.assertTrue(any(' / b' in s and s.count('/ b') == 1 for s in f[1:]), f)

    def test_distribute(self):
        f = generate(parse('(a+b)*(c+d)'), 'distribute')
        self.assertGreaterEqual(len(f), 3)
        for x in f:
            self.assertNotEqual(validate_equivalent(f[0].tree, x.tree)[0], 'fail')

    def test_all_samples(self):
        for mode, tests in [('factor', ASSOCIATIVE_TESTS), ('distribute', DISTRIBUTIVE_TESTS)]:
            for name, expression in tests.items():
                with self.subTest(name=name):
                    original = parse(expression)
                    forms = generate(original, mode, limit=85, max_depth=4)
                    self.assertGreater(len(forms), 1, name)
                    for f in forms:
                        status, msg = validate_equivalent(original, f.tree, trials=8)
                        self.assertNotEqual(status, 'fail', f'{name}: {display(f.tree)} | {msg}')

class TestIntegration(unittest.TestCase):
    def test_previous_lab_checks(self):
        from integration import validate_with_previous_labs
        self.assertFalse(validate_with_previous_labs('a*b+a*c'))
        self.assertTrue(validate_with_previous_labs('a++b'))
        self.assertTrue(validate_with_previous_labs('a*(b+c'))
        self.assertTrue(validate_with_previous_labs('a+b*'))

    def test_division_by_zero(self):
        from integration import zero_denominators
        self.assertEqual(len(zero_denominators(parse('a/0+b/(1-1)+c/(x-x)'))), 3)
        self.assertFalse(zero_denominators(parse('a/(x+1)')))

# Додаткові перевірки можна запускати командою:
# python -m unittest -v test_transformations


class TestDistributionPriority(unittest.TestCase):
    def test_distributed_form_first(self):
        from transformations import form_sort_key, distribution_remaining
        source = parse('a*(b+c)')
        forms = generate(source, 'distribute', limit=30, max_depth=3)
        best = min(forms, key=lambda item: form_sort_key(item, 'distribute'))
        self.assertGreater(best.step, 0)
        self.assertEqual(distribution_remaining(best.tree), 0)

    def test_factor_form_still_prefers_fewer_ops(self):
        from transformations import form_sort_key
        source = parse('a*b+a*c')
        forms = generate(source, 'factor', limit=30, max_depth=3)
        best = min(forms, key=lambda item: form_sort_key(item, 'factor'))
        self.assertLess(count_operations(best.tree), count_operations(source))

if __name__ == "__main__":
    unittest.main()

class TestDeepDistribution(unittest.TestCase):
    def test_large_expression_progresses_past_four_steps(self):
        from transformations import distribution_remaining, form_sort_key
        expr = ('A*(i+1)*(b+c)-B*(j-1)*(d-e)+s*(a-b)-t/(k-2)'
                '+(m*m)*(p+q)-r/(u-v)+((a+b)*(a+b))/(z-1)+C*(i+2)*(f-g)')
        original = parse(expr)
        forms = generate(original, 'distribute', limit=160, max_depth=5,
                         search_budget=1400)
        best = min(forms, key=lambda f: form_sort_key(f, 'distribute'))
        self.assertEqual(distribution_remaining(best.tree), 0)
        self.assertGreater(best.step, 4)
        self.assertEqual(validate_equivalent(original, best.tree, trials=20)[0], 'pass')

    def test_large_factor_only_one_form_is_valid_result(self):
        expr = ('A*(i+1)*(b+c)-B*(j-1)*(d-e)+s*(a-b)-t/(k-2)'
                '+(m*m)*(p+q)-r/(u-v)+((a+b)*(a+b))/(z-1)+C*(i+2)*(f-g)')
        forms = generate(parse(expr), 'factor', limit=160, max_depth=5,
                         search_budget=1400)
        self.assertGreaterEqual(len(forms), 1)
        self.assertEqual(validate_equivalent(parse(expr), forms[0].tree)[0], 'pass')

class TestRegressionCases(unittest.TestCase):
    def test_detect_nested_zero_denominator_without_exception(self):
        from integration import zero_denominators
        problems = zero_denominators(parse('a/(1/0)+b/(x-x)'))
        self.assertIn('0', problems)
        self.assertIn('x - x', problems)

    def test_subtraction_and_parentheses(self):
        from transformations import form_sort_key, distribution_remaining
        for expression in ('-(a-b)*(c-d)', '(a-(b-c))*(d-(e-f))'):
            original = parse(expression)
            forms = generate(original, 'distribute', limit=80, max_depth=5)
            best = min(forms, key=lambda f: form_sort_key(f, 'distribute'))
            self.assertEqual(distribution_remaining(best.tree), 0)
            self.assertEqual(validate_equivalent(original, best.tree)[0], 'pass')

    def test_invalid_input_is_rejected_by_previous_labs(self):
        from integration import validate_with_previous_labs
        for expr in ('a++b', 'A[++i]*(b+c)', 'a*(b+c', 'a+b*'):
            self.assertTrue(validate_with_previous_labs(expr), expr)
        self.assertFalse(validate_with_previous_labs('(a-b)*(c+d)'))

class TestMinusParenthesesRegression(unittest.TestCase):
    def check_best(self, source, expected):
        from transformations import form_sort_key, distribution_remaining
        original = parse(source)
        forms = generate(original, 'distribute', limit=160, max_depth=5, search_budget=1400)
        best = min(forms, key=lambda f: form_sort_key(f, 'distribute'))
        self.assertEqual(distribution_remaining(best.tree), 0, display(best.tree))
        self.assertEqual(validate_equivalent(original, best.tree, trials=30)[0], 'pass')
        self.assertEqual(display(best.tree).replace(' ', ''), expected.replace(' ', ''))

    def test_negative_product(self):
        self.check_best('-(a-b)*(c-d)', '-(a*c)+a*d+b*c-b*d')

    def test_double_nested_minus(self):
        self.check_best('(a-(b-c))*(d-(e-f))',
                        'a*d-a*e+a*f-b*d+b*e-b*f+c*d-c*e+c*f')

    def test_subtraction_of_brackets(self):
        self.check_best('a-(b-c)', 'a-b+c')

    def test_plus_with_subtraction(self):
        self.check_best('a+(b-c)', 'a+b-c')

    def test_nested_negative(self):
        self.check_best('-(-(a-b))', 'a-b')

    def test_subtract_product_difference(self):
        self.check_best('a-(b*c-d*e)', 'a-b*c+d*e')
