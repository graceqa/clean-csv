# Merchant Name CSV Cleaner – User Guide

This tool cleans, standardizes, and enriches merchant names in CSV files:
- **Formats Casing:** Title / Sentence case while keeping acronyms uppercase (HVAC, RX, MD, PC, state abbreviations, etc.).
- **Removes Legal Suffixes:** Strips `Inc.`, `LLC`, variations, and trailing cutoffs (`LL`, `IN`, `I`).
- **Recovers Truncated Words:** Uses the owner's email address and business vocabulary to complete cutoff words.
- **Flags Suspicious Records:** Puts `Attention` in Column R for any entries containing the word `"old"`, test accounts (`do not use`), or ambiguous cutoffs.

---

## 🌟 Method 1: The Web Interface (Easiest & Most Visual)

*No coding, no terminal, and no installation required!*

### How to use it locally:
1. Simply **double-click** `index.html` (or `cleaner.html`) in this folder.
2. It will open in your default browser (Chrome, Safari, Edge, Firefox).
3. **Drag and drop your CSV file** into the upload box (or click "Browse Files").
   - *Error checking:* If you accidentally upload an Excel file (`.xlsx`), PDF, or image, the page will immediately display a red alert explaining that only `.csv` files are accepted.
4. The page will clean the data in ~1 second.
5. **Your cleaned file automatically downloads** to your computer's **Downloads** folder (`<your_file>_cleaned.csv`).
6. You will also see a summary card on the screen with:
   - Total records processed
   - Truncations completed
   - Records flagged for Attention
   - A **"Download File Again"** button if you need another copy.

### How to use it via GitHub Hosting (GitHub Pages):
Once this repository is pushed to GitHub, you can enable **GitHub Pages** in the repository settings (`Settings > Pages > Branch: main / root`). Your colleague can then simply visit:
`https://<your-username>.github.io/<repo-name>/`
and run it directly in her browser from any computer, phone, or tablet without needing any files locally!

---

## 🖥️ Method 2: One-Click Desktop Launchers

If your colleague prefers desktop shortcuts:

- **On Mac:** Double-click `run_on_mac.command`.
- **On Windows:** Double-click `run_on_windows.bat`.

Follow the on-screen prompt: press **Enter** to clean `mailing list.csv`, or drag and drop any CSV file into the window and press Enter.

---

## 💻 Method 3: Command Line (Terminal / Command Prompt)

For technical users:

```bash
# Clean default 'mailing list.csv'
python3 clean_merchants.py

# Clean a specific file
python3 clean_merchants.py "path/to/my_file.csv"

# Clean a specific file with custom output name
python3 clean_merchants.py "input.csv" "output.csv"
```

---

## 📊 Reviewing the Results in Excel or Google Sheets

Open the cleaned CSV file:
- **Column Q (`cleaned_merchant_name`):** Contains the polished, standardized merchant names.
- **Column R (`attention`):** Click the filter dropdown on the header and filter for **`Attention`** to review any flagged accounts (such as accounts containing the word "old", test accounts, or unresolved single-letter cutoffs). All normal, high-confidence rows are left blank.
