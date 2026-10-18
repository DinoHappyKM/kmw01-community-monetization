import copy
import importlib.util
import unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/"skills/creative-farm-business-workflow/scripts/m08_quote.py"
spec=importlib.util.spec_from_file_location("quote",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE={"price":"6500","items":[
 {"name":"材料","kind":"cash","quantity":1,"unit_cost":"1800"},
 {"name":"運輸","kind":"cash","quantity":1,"unit_cost":"600"},
 {"name":"損耗","kind":"cash","quantity":1,"unit_cost":"200"},
 {"name":"設計","kind":"labor","quantity":2,"unit_cost":"300"},
 {"name":"製作","kind":"labor","quantity":3,"unit_cost":"300"},
 {"name":"現場","kind":"labor","quantity":1,"unit_cost":"300"}],
 "exclusions":["固定費","稅費"]}
class QuoteTests(unittest.TestCase):
    def test_known_worked_example(self):
        # Independently worked: cash2600 + six hours*300 =4400; 6500-4400=2100.
        r=m.calculate(BASE)
        self.assertEqual((r["total_cost"],r["balance_after_labor"]),("4400.00","2100.00"))
        self.assertEqual(r["balance_rate_percent"],"32.31")
        self.assertEqual(r["cash_return_per_hour_before_labor"],"650.00")
        self.assertEqual(r["balance_per_hour_after_labor"],"350.00")
    def test_unknown_not_zero(self):
        d=copy.deepcopy(BASE);d["items"][0]["unit_cost"]=None
        r=m.calculate(d)
        self.assertEqual(r["status"],"incomplete_costs")
        self.assertEqual(r["known_subtotal"],"2600.00")
        self.assertIsNone(r["total_cost"])
        self.assertIsNone(r["balance_after_labor"])
        self.assertEqual(r["missing_costs"],["材料"])
    def test_change_adds_cost_once(self):
        d=copy.deepcopy(BASE)
        d["items"].append({"name":"追加製作","kind":"labor","quantity":2,"unit_cost":"300"})
        r=m.calculate(d)
        self.assertEqual(r["total_cost"],"5000.00")
        self.assertEqual(r["balance_after_labor"],"1500.00")
        self.assertEqual(r["total_hours"],"8.00")
    def test_zero_price_and_hours(self):
        d={"price":0,"items":[{"name":"材料","kind":"cash","quantity":1,"unit_cost":100}]}
        r=m.calculate(d)
        self.assertIsNone(r["balance_rate_percent"])
        self.assertIsNone(r["cash_return_per_hour_before_labor"])
        self.assertEqual(r["balance_after_labor"],"-100.00")
    def test_negative_and_boolean_rejected(self):
        for x in [-1, True, "NaN"]:
            d=copy.deepcopy(BASE);d["items"][0]["unit_cost"]=x
            with self.assertRaises(ValueError):m.calculate(d)
    def test_no_rows_rejected(self):
        with self.assertRaises(ValueError):m.calculate({"price":100,"items":[]})
if __name__=="__main__":unittest.main(verbosity=2)
