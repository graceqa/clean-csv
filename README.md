# Clean CSV – Merchant Name Cleaner

A lightweight tool to clean, standardize, and format merchant names in CSV files.

- **Web Interface:** [https://graceqa.github.io/clean-csv/](https://graceqa.github.io/clean-csv/)
- **Casing:** Formats into Sentence/Title case while preserving business and state acronyms (`HVAC`, `RX`, `MD`, `PC`, etc.).
- **Entity Removal:** Removes `Inc.`, `LLC`, variations, and 24-character truncation artifacts (`LL`, `IN`, `I`).
- **Truncation Completion:** Uses `owner_email` and business terms to recover cutoff words.
- **Attention Flagging:** Flags accounts containing the word `"old"`, test accounts (`do not use`), and ambiguous cutoffs for human review in Column R.

## Usage

### In Browser
Open [`index.html`](index.html) or visit the [GitHub Pages live interface](https://graceqa.github.io/clean-csv/).

### Command Line
```bash
python3 clean_merchants.py "input.csv" "output.csv"
```
