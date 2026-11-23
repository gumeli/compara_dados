import unittest

from app import compare_data, parse_data, rows_to_csv


class ComparisonAppTests(unittest.TestCase):
    def test_parse_csv_with_quotes(self):
        rows = parse_data('Nome,Valor\n"Silva, Ana",10\nJosé,20\n')
        self.assertEqual(rows, [["Nome", "Valor"], ["Silva, Ana", "10"], ["José", "20"]])

    def test_exact_comparison_is_case_insensitive_by_default(self):
        result = compare_data(
            [["Ana", "10"], ["Pedro", "20"]],
            [["ana", "10"], ["Maria", "30"]],
        )
        self.assertEqual(result["unique"], [["Ana", "10"], ["Pedro", "20"], ["Maria", "30"]])
        self.assertEqual(result["removed"], [["ana", "10"]])
        self.assertEqual(result["onlyA"], [["Pedro", "20"]])
        self.assertEqual(result["onlyB"], [["Maria", "30"]])

    def test_key_comparison_uses_selected_column(self):
        result = compare_data(
            [["Ana", "A001"], ["Bruno", "A002"]],
            [["Outro", "a001"], ["Carla", "A003"]],
            mode="key",
            key_index=2,
            case_sensitive=False,
        )
        self.assertEqual(len(result["unique"]), 3)
        self.assertEqual(len(result["removed"]), 1)
        self.assertEqual(result["onlyA"], [["Bruno", "A002"]])
        self.assertEqual(result["onlyB"], [["Carla", "A003"]])

    def test_csv_export_has_bom_and_semicolon_separator(self):
        csv_text = rows_to_csv([["Ana", "A;1"], ['José "Zé"', "10"]])
        self.assertTrue(csv_text.startswith("\ufeff"))
        self.assertIn(";\"A;1\"", csv_text)
        self.assertIn('José ""Zé""', csv_text)


if __name__ == "__main__":
    unittest.main()
