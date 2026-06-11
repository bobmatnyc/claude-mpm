---
skill_id: xlsx
skill_version: 0.3.0
when_to_use: when reading, writing, generating, or transforming Excel (.xlsx) files programmatically in any language
description: Working with Excel files programmatically.
updated_at: 2025-10-30T17:00:00Z
tags: [excel, xlsx, spreadsheet, data]
effort: low
---

# Excel/XLSX Manipulation

Working with Excel files programmatically.

## Python (openpyxl)

### Reading Excel
```python
from openpyxl import load_workbook

wb = load_workbook('data.xlsx')
ws = wb.active  # Get active sheet

# Read cell
value = ws['A1'].value

# Iterate rows
for row in ws.iter_rows(min_row=2, values_only=True):
    print(row)
```

### Writing Excel
```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "Data"

# Write data
ws['A1'] = 'Name'
ws['B1'] = 'Age'
ws.append(['John', 30])
ws.append(['Jane', 25])

wb.save('output.xlsx')
```

### Formatting
```python
from openpyxl.styles import Font, PatternFill

# Bold header
ws['A1'].font = Font(bold=True)

# Background color
ws['A1'].fill = PatternFill(start_color="FFFF00", fill_type="solid")

# Number format
ws['B2'].number_format = '0.00'  # Two decimals
```

### Formulas
```python
# Add formula
ws['C2'] = '=A2+B2'

# Sum column
ws['D10'] = '=SUM(D2:D9)'
```

## Python (pandas)

### Reading Excel
```python
import pandas as pd

# Read sheet
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# Read multiple sheets
dfs = pd.read_excel('data.xlsx', sheet_name=None)
```

### Writing Excel
```python
# Write DataFrame
df.to_excel('output.xlsx', index=False)

# Multiple sheets
with pd.ExcelWriter('output.xlsx') as writer:
    df1.to_excel(writer, sheet_name='Sheet1')
    df2.to_excel(writer, sheet_name='Sheet2')
```

### Data Transformation
```python
# Filter
filtered = df[df['Age'] > 25]

# Group by
grouped = df.groupby('Department')['Salary'].mean()

# Pivot
pivot = df.pivot_table(values='Sales', index='Region', columns='Product')
```

## JavaScript (xlsx)

```javascript
import XLSX from 'xlsx';

// Read file
const workbook = XLSX.readFile('data.xlsx');
const sheetName = workbook.SheetNames[0];
const worksheet = workbook.Sheets[sheetName];

// Convert to JSON
const data = XLSX.utils.sheet_to_json(worksheet);

// Write file
const newWorksheet = XLSX.utils.json_to_sheet(data);
const newWorkbook = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'Data');
XLSX.writeFile(newWorkbook, 'output.xlsx');
```

## Common Operations

### CSV to Excel
```python
import pandas as pd

df = pd.read_csv('data.csv')
df.to_excel('data.xlsx', index=False)
```

### Excel to CSV
```python
df = pd.read_excel('data.xlsx')
df.to_csv('data.csv', index=False)
```

### Merging Excel Files
```python
dfs = []
for file in ['file1.xlsx', 'file2.xlsx', 'file3.xlsx']:
    df = pd.read_excel(file)
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)
combined.to_excel('merged.xlsx', index=False)
```

## Non-Obvious Patterns (the gotchas)

These are the traps the library quick-starts above will NOT warn you about:

- **`ws['C2'] = '=A2+B2'` stores the formula string, NOT a value** — openpyxl never evaluates formulas. Reading that cell back with `data_only=False` returns `'=A2+B2'`; reading with `load_workbook(..., data_only=True)` returns the cached result **only if Excel saved one** (a file openpyxl wrote has `None` there). To get computed values you must open in Excel/LibreOffice once, or evaluate with a separate engine.
- **`read_only=True` / `write_only=True` modes for large files** — the default mode loads the whole sheet into memory. For 100k+ rows use `load_workbook(path, read_only=True)` (streams rows) and `Workbook(write_only=True)` with `ws.append(...)`; random `ws['A1']` access is unavailable in these modes by design.
- **pandas `to_excel` silently drops formatting and timezone-aware datetimes** — tz-aware columns raise or get coerced; localize/strip tz first. For styled output, write with pandas then re-open the same file with openpyxl to apply styles (or use the `ExcelWriter(engine='openpyxl')` `.book`/`.sheets` handles).
- **Excel's 1900 leap-year bug + the 1,048,576-row / 16,384-column hard limits** — dates before 1900-03-01 and overflow rows fail differently per library; chunk or switch to a real database past the row cap.
- **JS `XLSX.utils.sheet_to_json` skips fully-empty rows and infers types loosely** — pass `{ raw: false, defval: null }` to preserve blanks and stop numeric-string coercion (zip codes, IDs losing leading zeros).
- **Number stored as text vs. number** — `ws['B2'].number_format` only changes *display*; if the underlying value is a `str` Excel shows the green-triangle warning and `SUM` ignores it. Cast to `int`/`float` before writing.

## Remember
- Close workbooks after use
- Handle large files in chunks
- Validate data before writing
- Use pandas for data analysis, openpyxl for formatting
