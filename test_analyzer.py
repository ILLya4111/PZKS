import unittest
from analyzer import analyze
from examples import EXAMPLES


class AnalyzerTests(unittest.TestCase):
    def test_valid(self):
        for s in ['a+2*b', '-x', '+x', 'a*(-b)', 'a+(+b)', 'a-(-b)',
                  'f()', 'f(a,g(),-x)', '(a+b)/(c-d)', '.71+172.',
                  '_x + A_1 + 0.5', 'f ( a , b )', '\t x\n+ 2', '1/0']:
            with self.subTest(s=s):
                self.assertEqual(analyze(s)[1], [])

    def test_strict_operator_sequences(self):
        for op in '+-*/':
            for sign in '+-':
                for gap in ['', ' ', '\t']:
                    source = 'a' + op + gap + sign + 'b'
                    with self.subTest(source=source):
                        errors = analyze(source)[1]
                        self.assertEqual(len(errors), 1)
                        self.assertEqual(errors[0].code, 'UNEXPECTED_OPERATOR')
                        self.assertEqual(errors[0].start, 2 + len(gap))
                self.assertEqual(analyze('a' + op + '(' + sign + 'b)')[1], [])
        for source in ['-a*b+c', '+a/b', 'f(-x,+y)', '(-a)+(+b)', 'a + (-1)']:
            self.assertEqual(analyze(source)[1], [])

    def test_invalid(self):
        cases = {'': 'EMPTY_EXPRESSION', '  ': 'EMPTY_EXPRESSION',
                 '*a': 'UNEXPECTED_OPERATOR', 'a+': 'INCOMPLETE',
                 'a b': 'MISSING_OPERATOR', '2(t)': 'MISSING_OPERATOR',
                 '(a)(b)': 'MISSING_OPERATOR', '()': 'EMPTY_GROUP',
                 ')a(': 'EXTRA_CLOSE', '(a': 'UNCLOSED', 'f(,)': 'MISSING_ARGUMENT',
                 'f(a,)': 'MISSING_ARGUMENT', 'f(,a)': 'MISSING_ARGUMENT',
                 'f((a,b))': 'COMMA_OUTSIDE', 'a,b': 'COMMA_OUTSIDE',
                 'a+++b': 'UNEXPECTED_OPERATOR', '--a': 'UNEXPECTED_OPERATOR',
                 'a/*b': 'UNEXPECTED_OPERATOR', '2var': 'INVALID',
                 '0.72.3': 'INVALID', '0xAB': 'INVALID', 'ім’я': 'INVALID',
                 'a$b': 'UNKNOWN', '1e3': 'INVALID', '.': 'INVALID'}
        for s, code in cases.items():
            with self.subTest(s=s):
                self.assertIn(code, [e.code for e in analyze(s)[1]])

    def test_positions_and_multiple_errors(self):
        source = '*a + 2bad / (b - ) + c$'
        tokens, errors = analyze(source)
        self.assertEqual({e.code for e in errors},
                         {'UNEXPECTED_OPERATOR', 'INVALID', 'MISSING_OPERAND', 'UNKNOWN'})
        self.assertEqual([(e.start,e.end) for e in errors], [(0,1),(5,9),(17,18),(22,23)])
        for token in tokens:
            self.assertEqual(source[token.start:token.end], token.text)

    def test_instructor_examples(self):
        self.assertEqual(len(EXAMPLES), 20)
        for name, expression in EXAMPLES:
            with self.subTest(name=name):
                tokens, errors = analyze(expression)
                self.assertEqual(not errors, name.startswith('Коректний'))
                self.assertTrue(all(0 <= e.start <= e.end <= len(expression) for e in errors))

    def test_long_input_without_recursion(self):
        self.assertEqual(analyze('(' * 2000 + 'x' + ')' * 2000)[1], [])
        self.assertEqual(len(analyze('(' * 1000 + 'x')[1]), 1000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
