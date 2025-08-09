# app/services/export_pdf.py
from __future__ import annotations
from datetime import date
from typing import Iterable
import os
import tempfile

from app.models.operation import Operation

_HTML_TMPL = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Отчёт {start} — {end}</title>
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: sans-serif; color: #111; }}
  h1 {{ font-size: 20px; margin: 0 0 12px; }}
  h2 {{ font-size: 16px; margin: 18px 0 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
  th {{ background: #f6f6f6; text-align: left; }}
  .right {{ text-align: right; }}
  .muted {{ color: #666; }}
  .inc {{ color: #177245; font-weight: 600; }}
  .exp {{ color: #B22222; font-weight: 600; }}
  .summary-table td:first-child {{ width: 65%; }}
</style>
</head>
<body>
  <h1>Отчёт {start} — {end}{user_label}</h1>

  <h2>Сводка по категориям</h2>
  <table class="summary-table">
    <thead>
      <tr><th>Категория</th><th class="right">Сумма, BYN</th></tr>
    </thead>
    <tbody>
      {summary_rows}
      <tr>
        <td class="right"><b>Итого расходов</b></td>
        <td class="right exp">-{total_exp:.2f}</td>
      </tr>
      {total_inc_row}
    </tbody>
  </table>

  <h2>Операции</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Дата/время</th>
        <th>Тип</th>
        <th class="right">Сумма</th>
        <th>Категория</th>
        <th>Описание</th>
      </tr>
    </thead>
    <tbody>
      {ops_rows}
    </tbody>
  </table>

  <p class="muted">Сгенерировано автоматически.</p>
</body>
</html>
"""

def _fmt_money(val: float) -> str:
    return f"{val:.2f}"

def _build_summary(ops: Iterable[Operation]) -> tuple[str, float, float]:
    agg: dict[str, float] = {}
    total_exp = 0.0
    total_inc = 0.0
    for o in ops:
        sign = 1.0 if o.type == "income" else -1.0
        val = sign * float(abs(o.amount))
        cat = o.category or "Прочее"
        agg[cat] = agg.get(cat, 0.0) + val
        if val < 0:
            total_exp += abs(val)
        else:
            total_inc += val

    rows = []
    for cat in sorted(agg.keys()):
        val = agg[cat]
        cls = "inc" if val > 0 else ("exp" if val < 0 else "")
        rows.append(
            f"<tr><td>{cat}</td><td class='right {cls}'>{_fmt_money(val)}</td></tr>"
        )
    return "\n".join(rows), round(total_exp, 2), round(total_inc, 2)

def _build_ops_rows(ops: Iterable[Operation]) -> str:
    out = []
    for i, o in enumerate(ops, 1):
        sign = "-" if o.type == "expense" else "+"
        val = _fmt_money(abs(float(o.amount)))
        ts = o.created_at.strftime("%Y-%m-%d %H:%M")
        typ = "Расход" if o.type == "expense" else "Доход"
        out.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{ts}</td>"
            f"<td>{typ}</td>"
            f"<td class='right'>{sign}{val}</td>"
            f"<td>{o.category or ''}</td>"
            f"<td>{(o.description or '').replace('<','&lt;').replace('>','&gt;')}</td>"
            "</tr>"
        )
    return "\n".join(out)

def build_pdf(ops: list[Operation], start: date, end: date, user_label: str = "") -> str:
    """Создаёт PDF и возвращает путь к временному файлу. Импортируем weasyprint лениво."""
    try:
        from weasyprint import HTML  # ленивый импорт, чтобы отсутствие pango не валило загрузку модулей
    except Exception as e:
        raise RuntimeError("PDF-экспорт недоступен: не установлены системные библиотеки weasyprint/pango.") from e

    summary_rows, total_exp, total_inc = _build_summary(ops)
    ops_rows = _build_ops_rows(ops)
    total_inc_row = (
        f"<tr><td class='right'><b>Итого доходов</b></td><td class='right inc'>+{total_inc:.2f}</td></tr>"
        if total_inc > 0 else ""
    )
    html = _HTML_TMPL.format(
        start=start.isoformat(),
        end=end.isoformat(),
        user_label=(" · @" + user_label if user_label else ""),
        summary_rows=summary_rows or "<tr><td colspan='2' class='muted'>Нет данных</td></tr>",
        ops_rows=ops_rows or "<tr><td colspan='6' class='muted'>Нет операций</td></tr>",
        total_exp=total_exp,
        total_inc=total_inc,
        total_inc_row=total_inc_row,
    )

    fd, path = tempfile.mkstemp(prefix="fin_report_", suffix=".pdf")
    os.close(fd)
    HTML(string=html).write_pdf(path)
    return path
