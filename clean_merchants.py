#!/usr/bin/env python3
"""
clean_merchants.py

Intakes a CSV file (e.g., 'mailing list.csv'), cleans and standardizes the merchant names:
1. Removes 'Inc.' and 'LLC.' (including common variations and cutoff truncations like ' LL' or ' IN').
2. Detects truncated merchant names and uses 'owner_email' to complete the truncated last word.
3. Formats merchant names:
   - Sentence / Title casing: First letter of each word capitalized.
   - Acronyms remain UPPERCASE (e.g., HVAC, RX, MD, PC, state codes, Roman numerals, consonant clusters).
   - Handles apostrophes (e.g., Another Man's Treasure), ordinals (5th, 34th), Mc/O' prefixes, and Spanish articles (La, El).
4. Appends two columns at the very end of the CSV:
   - cleaned_merchant_name: The transformed merchant name.
   - attention: Set to 'Attention' if confidence is below 70% or if the entry looks suspicious/incomplete.
"""

import sys
import os
import csv
import re
import argparse
import time

# --- ACRONYMS & VOCABULARY ---

KNOWN_ACRONYMS = {
    # Industry & business abbreviations
    'HVAC', 'RX', 'MD', 'PC', 'DJ', 'TV', 'VIP', 'BBQ', 'BCL', 'ACE', 'IV', 
    'SNA', 'CHS', 'FABB', 'BSPGC', 'CPA', 'DDS', 'DMD', 'RN', 'LPN', 'NP', 
    'PA', 'PT', 'OT', 'DVM', 'DC', 'OD', 'ESQ', 'DBA', 'USA', 'US', 
    'ATM', 'POS', 'BJJ', 'MMA', 'YMCA', 'YWCA', 'VFW', 'POA', 'HOA', 'AAA', 
    'BBB', 'A/C', 'AC', 'IT', 'AI', 'CD', 'DVD', 'FM', 'AM', 'GPS', 'LED', 
    'CCTV', 'RV', 'ATV', 'UTV', 'EMS', 'EMT', 'FD', 'PD', 'HQ', 'NYC', 'SF', 
    'MIA', 'DFW', 'ATL', 'PHX', 'ORD', 'MSP', 'CLT', 'SLC', 'LAS', 'PHL', 
    'NH', 'LV', 'MH', 'VA03', 'FDPOS', 'TCOE', 'MMIS'
}

# 50 US States + DC
STATE_ACRONYMS = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 
    'WI', 'WY', 'DC'
}

# State acronyms that collide with common words - only treat as acronym if context strongly implies it
AMBIGUOUS_STATE_WORDS = {'IN', 'ME', 'OR', 'HI', 'OK', 'AM', 'AS', 'AT', 'BY', 'DO', 'GO', 'HE', 'IF', 'IS', 'IT', 'MY', 'NO', 'ON', 'SO', 'TO', 'UP', 'WE'}

# Spanish articles and common titles that should be capitalized (Title Case), not all caps
TITLE_WORDS = {'MR', 'MRS', 'MS', 'DR', 'ST', 'MT', 'JR', 'SR', 'CORP', 'LTD', 'CO', 'CTR'}
SPANISH_ARTICLES = {'LA', 'EL', 'LAS', 'LOS', 'DEL', 'DE', 'Y', 'MI'}

# Public email domains whose domain names should NOT be used for merchant name completion
PUBLIC_EMAIL_DOMAINS = {
    'gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'comcast',
    'sbcglobal', 'att', 'verizon', 'cox', 'charter', 'msn', 'bellsouth',
    'mail', 'live', 'proton', 'protonmail', 'me', 'earthlink', 'mac', 'ymail'
}

# Common business word completions for truncated words at length 24
BUSINESS_COMPLETIONS = {
    'STOR': 'Store',
    'HOSPIT': 'Hospital',
    'RESTAURAN': 'Restaurant',
    'RESTAURA': 'Restaurant',
    'CLEANER': 'Cleaners',
    'JEWELR': 'Jewelry',
    'BAKER': 'Bakery',
    'PHARMAC': 'Pharmacy',
    'AUTOMOT': 'Automotive',
    'TRANSPORT': 'Transportation',
    'LANDSCAP': 'Landscaping',
    'CONSTRUCT': 'Construction',
    'ENTERPRIS': 'Enterprises',
    'MANAGEM': 'Management',
    'DISTRIB': 'Distribution',
}

# Load system dictionary if available, with built-in fallbacks
DICTIONARY_WORDS = set()
for _dict_path in ['/usr/share/dict/words', '/usr/dict/words']:
    if os.path.exists(_dict_path):
        try:
            with open(_dict_path, mode='r', encoding='utf-8', errors='ignore') as _df:
                DICTIONARY_WORDS.update(line.strip().lower() for line in _df)
            break
        except Exception:
            pass

# Supplement with business words and inflections
DICTIONARY_WORDS.update([
    'hunting', 'crawfish', 'collectibles', 'towing', 'restaurant', 'store', 
    'hospital', 'baseball', 'recovery', 'masonry', 'guntersville', 'services', 
    'solutions', 'products', 'supplies', 'enterprises', 'properties', 'investments', 
    'logistics', 'consulting', 'contractors', 'landscaping', 'restoration', 
    'automotive', 'specialists', 'technologies', 'construction', 'recreation', 
    'photography', 'innovations', 'cleaners', 'bakery', 'jewelry', 'nursery',
    'transportation', 'transport', 'appraisal', 'equipment'
])


def remove_inc_llc(name: str, raw_len: int) -> str:
    """
    Removes 'Inc.' and 'LLC.' and variations from the merchant name.
    Also handles cutoffs at 24 characters (e.g., ' LL' or ' IN' or ' I').
    """
    # Remove standard Inc and LLC occurrences
    t = re.sub(r'(?i)(?:,\s*|\s+|-+\s*)(?:l+\.?l+\.?c+\.?|inc\.?|llc\.?|l\.l\.c\.?|i\.n\.c\.?)(?=[,\s\(\)\-\.]|$)', '', name)
    # Remove glued LLC suffix without space (e.g., SERVICESLLC)
    t = re.sub(r'(?i)(?<=[a-zA-Z0-9])llc\.?$', '', t)
    # If the raw string reached the source cutoff of 24 chars, remove trailing truncated LL, IN, or I
    if raw_len >= 24:
        t = re.sub(r'(?i)(?:,\s*|\s+|-+\s*)(?:ll|in|i)$', '', t)
    # Strip any trailing punctuation left behind
    t = re.sub(r'[, -]+$', '', t).strip()
    return t


def extract_email_tokens(email: str) -> list[str]:
    """
    Extracts informative word tokens from the owner email address.
    Excludes public domains (gmail, yahoo, etc.) to prevent false matches.
    """
    if not email or '@' not in email:
        return []
    
    local, domain = email.split('@', 1)
    domain_name = domain.split('.')[0] if '.' in domain else domain
    
    parts = re.split(r'[^a-zA-Z0-9]+', local)
    if domain_name.lower() not in PUBLIC_EMAIL_DOMAINS:
        parts.extend(re.split(r'[^a-zA-Z0-9]+', domain_name))
        
    tokens = []
    for p in parts:
        # Strip digits from ends (e.g., 'crawfish111' -> 'crawfish')
        clean = re.sub(r'^\d+|\d+$', '', p).lower()
        if len(clean) >= 2:
            tokens.append(clean)
        # Also split internal digits
        for sp in re.split(r'\d+', p):
            if len(sp) >= 2:
                tokens.append(sp.lower())
                
    # Return unique tokens preserving order
    return list(dict.fromkeys(tokens))


def try_complete_last_word(name: str, raw_len: int, email: str) -> tuple[str, bool, float]:
    """
    If the merchant name is truncated (hit the 24-character field limit),
    attempts to complete the last word using the owner's email address or known business suffixes.
    Returns: (updated_name, was_completed, completion_confidence)
    """
    if raw_len < 23:
        return name, False, 1.0
        
    words = re.findall(r'[a-zA-Z0-9\']+', name)
    if not words:
        return name, False, 1.0
        
    last = words[-1]
    last_upper = last.upper()
    last_lower = last.lower()
    
    # 1. Check known business suffix completions
    if last_upper in BUSINESS_COMPLETIONS:
        completion = BUSINESS_COMPLETIONS[last_upper]
        pattern = re.compile(re.escape(last) + r'$')
        new_name = pattern.sub(completion, name)
        return new_name, True, 0.85
        
    # Single characters are too ambiguous to complete from an email username
    if len(last) < 2:
        return name, False, 1.0

    # If the last word is already a recognized complete English word (e.g. Art, Well, Printing, Bar),
    # do not extend it with characters from the email address.
    if len(last) >= 3 and last_lower in DICTIONARY_WORDS:
        return name, False, 1.0
        
    # 2. Check email tokens
    email_tokens = extract_email_tokens(email)
    name_words_lower = [w.lower() for w in words[:-1]]
    
    for tok in email_tokens:
        if tok.startswith(last_lower) and len(tok) > len(last):
            cand = tok
            # If token ends with state code (e.g. guntersvilleal -> guntersville), strip state code
            for st in STATE_ACRONYMS:
                if cand.endswith(st.lower()) and len(cand) - len(st) >= len(last):
                    sub = cand[:-len(st)]
                    if sub in DICTIONARY_WORDS or len(sub) > len(last):
                        cand = sub
                        break
                        
            # The candidate must be a valid dictionary word
            if DICTIONARY_WORDS and cand not in DICTIONARY_WORDS:
                continue
                    
            # Skip if candidate contains another word that already appears earlier in the name
            if any(len(ow) >= 4 and ow in cand for ow in name_words_lower):
                continue
                
            cand_fmt = cand.capitalize()
            pattern = re.compile(re.escape(last) + r'$')
            new_name = pattern.sub(cand_fmt, name)
            return new_name, True, 0.95
            
    return name, False, 1.0


def format_word(word: str, is_all_caps_context: bool, is_first: bool, is_last: bool) -> str:
    """
    Formats an individual word:
    - Acronyms remain UPPERCASE.
    - Standard words are Capitalized (First letter uppercase, rest lowercase).
    - Preserves ordinals (5th, 34th), apostrophes (Man's), and prefixes (Mc/O'/D').
    """
    if not word:
        return ''
        
    # Ordinals: 1st, 2nd, 3rd, 4th, 5th, etc.
    m_ord = re.match(r'^(\d+)(st|nd|rd|th)$', word, flags=re.IGNORECASE)
    if m_ord:
        return m_ord.group(1) + m_ord.group(2).lower()
        
    # Alphanumeric codes: VA03, H20, 4K, 3D
    if re.match(r'^[A-Za-z0-9]+$', word) and any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
        return word.upper()
        
    # Pure numbers
    if word.isdigit():
        return word
        
    w_upper = word.upper()
    
    # Spanish articles and common titles -> Capitalized, not all caps
    if w_upper in TITLE_WORDS or w_upper in SPANISH_ARTICLES:
        return word.capitalize()
        
    # Explicit known acronyms
    if w_upper in KNOWN_ACRONYMS:
        return w_upper
        
    # State codes
    if w_upper in STATE_ACRONYMS:
        if w_upper in AMBIGUOUS_STATE_WORDS:
            # Only uppercase if positioned at the end (e.g., 'Care Center NH' or 'Boutique LV')
            if is_last and not is_first:
                return w_upper
            else:
                return word.capitalize()
        else:
            return w_upper

    # Roman numerals (II, III, IV, VI, VII, VIII, IX, etc.)
    if w_upper in {'II', 'III', 'IV', 'VI', 'VII', 'VIII', 'IX', 'XI', 'XII'}:
        return w_upper
        
    # Consonants-only words of 2-6 letters -> Acronym (e.g., BSPGC, CHS, CTR, FTS)
    if len(word) >= 2 and len(word) <= 6 and not any(c in 'AEIOUaeiouYy' for c in word) and word.isalpha():
        return w_upper

    # If the original context was mixed case, and this specific word was ALL CAPS (>=2 letters),
    # preserve it as an intentional acronym (e.g., 'Love Laced Beautique LV' or 'Sugar Troll MH')
    if not is_all_caps_context and word.isupper() and len(word) >= 2:
        return w_upper

    # Surnames / Prefixes: Mc..., O'..., D'...
    if word.lower().startswith('mc') and len(word) > 2:
        return 'Mc' + word[2:].capitalize()
    if word.lower().startswith("o'") and len(word) > 2:
        return "O'" + word[2:].capitalize()
    if word.lower().startswith("d'") and len(word) > 2:
        return "D'" + word[2:].capitalize()

    # Apostrophe s: e.g., MAN'S -> Man's
    if re.match(r'^[a-zA-Z]+\'[sS]$', word):
        return word[:-2].capitalize() + "'s"
    if word.endswith("'"):
        return word[:-1].capitalize() + "'"
        
    # Hyphenated words: e.g., DROP-N-GO -> Drop-N-Go
    if '-' in word:
        subparts = word.split('-')
        return '-'.join(format_word(sp, is_all_caps_context, False, False) for sp in subparts)

    return word.capitalize()


def format_merchant_name(name: str, was_originally_all_caps: bool = False) -> str:
    """
    Standardizes and formats the entire merchant name string according to sentence/title casing
    and acronym rules, while preserving delimiter structure.
    """
    name = name.strip()
    if not name:
        return ''
        
    is_all_caps = was_originally_all_caps or (name == name.upper())
    
    # Split into words and punctuation/delimiters
    tokens = re.split(r'(\s+|[,\&/\(\)])', name)
    word_indices = [i for i, tok in enumerate(tokens) if any(c.isalnum() for c in tok)]
    
    out = []
    for i, tok in enumerate(tokens):
        if not tok:
            continue
        if any(c.isalnum() for c in tok):
            is_first = (i == word_indices[0]) if word_indices else False
            is_last = (i == word_indices[-1]) if word_indices else False
            out.append(format_word(tok, is_all_caps, is_first, is_last))
        else:
            out.append(tok)
            
    res = ''.join(out)
    return re.sub(r'\s+', ' ', res).strip()


def process_merchant_record(raw_name: str, email: str) -> tuple[str, str, float]:
    """
    Performs the full transformation on a merchant name:
    1. Removes Inc. and LLC.
    2. Completes truncated last words using owner_email or business vocabulary.
    3. Formats casing (Title case words, uppercase acronyms).
    4. Evaluates confidence and flags 'Attention' if confidence < 70% or anomaly detected.
    
    Returns: (cleaned_merchant_name, attention_flag, confidence_score)
    """
    raw_name = raw_name.strip()
    raw_len = len(raw_name)
    is_originally_all_caps = (raw_name == raw_name.upper()) and any(c.isalpha() for c in raw_name)
    confidence = 1.0
    
    if not raw_name:
        return '', 'Attention', 0.0
        
    # Check for placeholder / dummy / test accounts or names containing 'old'
    if re.search(r'(?i)\b(do not use|test|temp|unknown|dummy|n/a)\b', raw_name):
        confidence = min(confidence, 0.3)
    elif re.search(r'(?i)\bold\b', raw_name):
        confidence = min(confidence, 0.4)
    elif re.match(r'(?i)^(none|na|\.|\?+)$', raw_name):
        confidence = min(confidence, 0.2)
        
    # Check very short or non-alphabetic names
    if len(raw_name) <= 2:
        confidence = min(confidence, 0.4)
    if not any(c.isalpha() for c in raw_name):
        confidence = min(confidence, 0.2)
        
    # 1. Remove Inc. and LLC
    cleaned = remove_inc_llc(raw_name, raw_len)
    
    # Check if last word appears truncated and required email resolution
    words = cleaned.split()
    last_word = words[-1] if words else ''
    last_lower = last_word.lower()
    last_upper = last_word.upper()
    
    raw_ended_with_entity = bool(re.search(r'(?i)(?:[,\s\-_]+|\b)(?:l+\.?l+\.?c+\.?|inc\.?|llc\.?|l\.l\.c\.?|i\.n\.c\.?|ll|in|i)$', raw_name))
    hit_cutoff = (raw_len == 24 or (raw_len == 23 and raw_name.endswith(' '))) and not raw_ended_with_entity
    
    is_truncated_word = False
    if hit_cutoff and last_word:
        if len(last_word) == 1 and last_word.isalpha():
            is_truncated_word = True
        elif last_lower in {'and', 'or', 'of', 'the', 'for', 'in', 'at', 'with', 'by', 'an', 'a', '&'}:
            is_truncated_word = True
        elif last_upper in BUSINESS_COMPLETIONS:
            is_truncated_word = True
        elif (last_lower not in DICTIONARY_WORDS or len(last_word) <= 2) and last_upper not in KNOWN_ACRONYMS:
            is_truncated_word = True

    # 2. Try completion if truncated
    completed_name, was_completed, comp_conf = try_complete_last_word(cleaned, raw_len, email)
    if was_completed:
        confidence = min(confidence, comp_conf)
    elif is_truncated_word:
        # The name required using email to deduce the complete word, but email does not exist, was empty, or did not contain the completion
        if last_lower in {'and', 'or', 'of', 'the', 'for', 'in', 'at', 'with', 'by', 'an', 'a', '&'}:
            cleaned_without_dangling = re.sub(r'(?i)\s+(?:and|or|of|the|for|in|at|with|by|an|a|&)$', '', completed_name).strip()
            if cleaned_without_dangling:
                completed_name = cleaned_without_dangling
        confidence = min(confidence, 0.5)
                
    # Check suspicious characters or emoji
    if re.search(r'[♥®™\?]{2,}', raw_name):
        confidence = min(confidence, 0.5)
        
    # 3. Format casing
    formatted = format_merchant_name(completed_name, was_originally_all_caps=is_originally_all_caps)
    
    # 4. Attention flag if confidence < 70%
    attention = 'Attention' if confidence < 0.70 else ''
    
    return formatted, attention, confidence


def find_column_indices(header: list[str], specified_merchant_idx: int | None = None, specified_email_idx: int | None = None) -> tuple[int, int | None]:
    """
    Locates:
    1. The merchant_name column: finds exact 'merchant_name' or any header resembling 'merchant name'
       (e.g., 'Merchant Name', 'merchant', 'business_name', 'dba_name', 'company_name', etc.).
    2. The owner_email column: finds 'owner_email' or any header containing 'email'.
       Returns None if no email column exists in the CSV (email is optional).
    """
    # 1. Locate merchant_name column
    merchant_idx = None
    if specified_merchant_idx is not None:
        merchant_idx = specified_merchant_idx
    else:
        # Check Column D (index 3) first if it contains 'merchant' or 'name'
        if len(header) > 3 and 'merchant' in header[3].strip().lower():
            merchant_idx = 3
        else:
            best_score = -1
            best_idx = None
            for i, raw_col in enumerate(header):
                col_clean = re.sub(r'[^a-z0-9]+', ' ', raw_col.strip().lower()).strip()
                score = 0
                
                # Priority 1: Exact normalized match for 'merchant name' or 'merchantname'
                if col_clean in ('merchant name', 'merchantname', 'merchant'):
                    score = 100
                # Priority 2: Contains both 'merchant' and 'name'
                elif 'merchant' in col_clean and 'name' in col_clean:
                    score = 90
                # Priority 3: Contains 'merchant'
                elif 'merchant' in col_clean:
                    score = 70
                # Priority 4: Resembles business / company / store / dba name
                elif any(term in col_clean for term in ('business name', 'company name', 'store name', 'dba name', 'dba')):
                    score = 50
                elif any(term in col_clean for term in ('business', 'company')):
                    score = 30
                    
                if score > best_score:
                    best_score = score
                    best_idx = i
                    
            if best_score > 0:
                merchant_idx = best_idx

    if merchant_idx is None:
        available = ', '.join(repr(c) for c in header[:10])
        raise ValueError(f"Could not find a column header resembling 'merchant name'. Available columns: [{available}]")

    # 2. Locate owner_email column (optional: can be None)
    email_idx = None
    if specified_email_idx is not None:
        email_idx = specified_email_idx
    else:
        best_email_score = -1
        best_email_idx = None
        for i, raw_col in enumerate(header):
            col_clean = re.sub(r'[^a-z0-9]+', ' ', raw_col.strip().lower()).strip()
            score = 0
            if col_clean in ('owner email', 'owneremail'):
                score = 100
            elif 'owner' in col_clean and 'email' in col_clean:
                score = 90
            elif 'email' in col_clean:
                score = 70
                
            if score > best_email_score:
                best_email_score = score
                best_email_idx = i
                
        if best_email_score > 0:
            email_idx = best_email_idx

    return merchant_idx, email_idx


def process_csv(input_path: str, output_path: str, merchant_col_idx: int | None = None, email_col_idx: int | None = None, drop_duplicate_col: bool = True) -> dict:
    """
    Processes the input CSV file and writes the enriched data to the output CSV file.
    Drops any duplicate merchant_name column (e.g. Column E / index 4) so state ends at Column P,
    and appends 'cleaned_merchant_name' (Column Q) and 'attention' (Column R) at the end.
    """
    start_time = time.time()
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    stats = {
        'total_rows': 0,
        'completed_truncations': 0,
        'flagged_attention': 0,
        'elapsed_seconds': 0.0,
        'dropped_duplicate_column': False,
    }
    
    with open(input_path, mode='r', encoding='utf-8', errors='replace') as infile:
        reader = csv.reader(infile)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"File {input_path} is empty.")
            
        merchant_idx, email_idx = find_column_indices(header, merchant_col_idx, email_col_idx)
        
        # Check if there is a redundant duplicate merchant_name column at index 4
        drop_idx = None
        if drop_duplicate_col and len(header) > 4:
            if header[3].strip().lower() == 'merchant_name' and header[4].strip().lower() == 'merchant_name':
                drop_idx = 4
                stats['dropped_duplicate_column'] = True
                
        # Build new output header
        if drop_idx is not None:
            base_header = [col for i, col in enumerate(header) if i != drop_idx]
        else:
            base_header = list(header)
            
        new_header = base_header + ['cleaned_merchant_name', 'attention']
        
        with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(new_header)
            
            for row in reader:
                if not row:
                    continue
                stats['total_rows'] += 1
                
                raw_merchant = row[merchant_idx] if len(row) > merchant_idx else ''
                email = row[email_idx] if (email_idx is not None and len(row) > email_idx) else ''
                
                cleaned_name, attention_val, confidence = process_merchant_record(raw_merchant, email)
                
                if attention_val:
                    stats['flagged_attention'] += 1
                if confidence == 0.95:  # high-confidence email completion
                    stats['completed_truncations'] += 1
                    
                if drop_idx is not None:
                    base_row = [val for i, val in enumerate(row) if i != drop_idx]
                else:
                    base_row = list(row)
                    
                new_row = base_row + [cleaned_name, attention_val]
                writer.writerow(new_row)
                
    stats['elapsed_seconds'] = time.time() - start_time
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clean and standardize merchant names in CSV files, appending cleaned name and attention flag."
    )
    parser.add_argument(
        'input_file', 
        nargs='?', 
        default='mailing list.csv',
        help="Path to input CSV file (default: 'mailing list.csv')"
    )
    parser.add_argument(
        'output_file', 
        nargs='?', 
        default=None,
        help="Path to output CSV file (default: '<input_name>_cleaned.csv')"
    )
    parser.add_argument(
        '--merchant-col', 
        type=int, 
        default=None,
        help="Zero-based index of merchant_name column (default: Column D / index 3)"
    )
    parser.add_argument(
        '--email-col', 
        type=int, 
        default=None,
        help="Zero-based index of owner_email column (default: Column F / index 5)"
    )
    
    args = parser.parse_args()
    
    input_path = args.input_file
    
    # If the default file was used but doesn't exist, or if run interactively without args:
    if len(sys.argv) == 1:
        if os.path.exists('mailing list.csv'):
            print("\nDefault file 'mailing list.csv' detected in this folder.")
            try:
                user_choice = input("Press ENTER to process it, or drag and drop your CSV file here: ").strip()
                if user_choice:
                    # Strip quotes if dragged and dropped from Mac Finder or Windows Explorer
                    input_path = user_choice.strip('\'"')
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                sys.exit(0)
        else:
            print("\nWelcome! No file was passed to the script.")
            try:
                user_choice = input("Please drag and drop your CSV file into this window and press ENTER: ").strip()
                if user_choice:
                    input_path = user_choice.strip('\'"')
                else:
                    print("No file provided. Exiting.")
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                sys.exit(0)
                
    if not os.path.exists(input_path):
        print(f"\nError: Could not find file '{input_path}'. Please check the filename or path and try again.", file=sys.stderr)
        sys.exit(1)
        
    if args.output_file:
        output_path = args.output_file
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_cleaned{ext}"
        
    print(f"\n=== Merchant Name Processing Pipeline ===")
    print(f"Input file : {input_path}")
    print(f"Output file: {output_path}")
    
    try:
        stats = process_csv(
            input_path=input_path, 
            output_path=output_path, 
            merchant_col_idx=args.merchant_col, 
            email_col_idx=args.email_col
        )
        print("\n=== Processing Complete ===")
        print(f"Total records processed : {stats['total_rows']:,}")
        print(f"Truncations completed   : {stats['completed_truncations']:,}")
        print(f"Flagged for Attention   : {stats['flagged_attention']:,} ({stats['flagged_attention']/max(1, stats['total_rows'])*100:.2f}%)")
        print(f"Execution time          : {stats['elapsed_seconds']:.2f}s ({stats['total_rows']/max(0.001, stats['elapsed_seconds']):.0f} rows/s)")
        print(f"Output saved to         : {output_path}\n")
        
        if len(sys.argv) == 1:
            try:
                input("Press ENTER to close this window...")
            except (EOFError, KeyboardInterrupt):
                pass
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if len(sys.argv) == 1:
            try:
                input("\nPress ENTER to close this window...")
            except (EOFError, KeyboardInterrupt):
                pass
        sys.exit(1)


if __name__ == '__main__':
    main()
