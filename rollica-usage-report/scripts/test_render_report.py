import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from render_report import load_input, render, validate

def sample():
    return {"start":"2026-01-01","end":"2026-01-30","observed_at":"2026-01-31T01:00:00+00:00","all_work":3,"all_issue":2,"unmatched":0,"users":[{"name":"示例","email":"sample@example.invalid","registered":"2025-12-01","accounts":1,"total":5,"daily":[[0,3,0],[4,0,2]]},{"name":"零消息","email":"zero@example.invalid","registered":"2026-01-10","accounts":1,"total":0,"daily":[]}]}

class RenderTests(unittest.TestCase):
    def test_render(self):
        text = render(sample())
        self.assertNotIn("__REPORT_DATA__",text)
        self.assertNotIn("__DAYS__",text)
        self.assertIn("2026-01-01 → 2026-01-30",text)
        self.assertIn("length:30",text)
        self.assertIn("个人相对峰值",text)
        self.assertNotIn("baijihang",text)
    def test_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"input.csv"
            output=io.StringIO()
            writer=csv.writer(output);writer.writerow(["report"]);writer.writerow([json.dumps(sample())])
            path.write_text(output.getvalue(),encoding="utf-8-sig")
            self.assertEqual(load_input(path),sample())
    def test_mismatch(self):
        x=sample();x["all_work"]=4
        with self.assertRaises(ValueError):validate(x)
    def test_duplicate_email(self):
        x=sample();x["users"].append(copy.deepcopy(x["users"][0]))
        with self.assertRaises(ValueError):validate(x)
    def test_bad_day(self):
        x=sample();x["users"][0]["daily"][1][0]=30
        with self.assertRaises(ValueError):validate(x)
    def test_unmatched(self):
        x=sample();x["unmatched"]=1
        with self.assertRaises(ValueError):validate(x)
    def test_incomplete_day(self):
        x=sample();x["observed_at"]="2026-01-30T12:00:00+00:00"
        with self.assertRaises(ValueError):validate(x)
    def test_injection(self):
        x=sample();x["users"][0]["name"]="<"+"/script><script>alert(1)<"+"/script>"
        text=render(x)
        self.assertNotIn(x["users"][0]["name"],text)
    def test_new_window_and_empty(self):
        x=sample();x.update(start="2026-02-01",end="2026-02-07",observed_at="2026-02-08T01:00:00+00:00",users=[],all_work=0,all_issue=0)
        text=render(x)
        self.assertIn("length:7",text)
        self.assertIn("2026-02-01 → 2026-02-07",text)

if __name__=="__main__":
    unittest.main()
