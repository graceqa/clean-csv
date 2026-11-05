import unittest
from clean_merchants import (
    remove_inc_llc,
    try_complete_last_word,
    format_word,
    format_merchant_name,
    process_merchant_record,
    extract_email_tokens
)

class TestCleanMerchants(unittest.TestCase):

    def test_remove_inc_llc(self):
        self.assertEqual(remove_inc_llc("LA CASA DULCE INC", 17), "LA CASA DULCE")
        self.assertEqual(remove_inc_llc("JB ASPHALT SERVICE LLC", 22), "JB ASPHALT SERVICE")
        self.assertEqual(remove_inc_llc("Glacial HVAC Pro Inc.", 21), "Glacial HVAC Pro")
        self.assertEqual(remove_inc_llc("Beaver Bulk, Inc.", 17), "Beaver Bulk")
        self.assertEqual(remove_inc_llc("DURHAM'S SILT FENCING LL", 24), "DURHAM'S SILT FENCING")
        self.assertEqual(remove_inc_llc("YINGNEWS INTERNATIONAL I", 24), "YINGNEWS INTERNATIONAL")
        self.assertEqual(remove_inc_llc("BILL HIGGINS PAINTING IN", 24), "BILL HIGGINS PAINTING")
        self.assertEqual(remove_inc_llc("RUDDS MOBILE SERVICESLLC", 24), "RUDDS MOBILE SERVICES")
        # Ensure Corp and Ltd are preserved
        self.assertEqual(remove_inc_llc("NEWROCK CONVENIENCE CORP", 24), "NEWROCK CONVENIENCE CORP")

    def test_email_token_extraction(self):
        tokens = extract_email_tokens("curt@dakota-pheasant-hunting.com")
        self.assertIn("hunting", tokens)
        self.assertIn("pheasant", tokens)
        self.assertIn("dakota", tokens)

        tokens_gmail = extract_email_tokens("solz.collectibles@gmail.com")
        self.assertIn("collectibles", tokens_gmail)
        self.assertNotIn("gmail", tokens_gmail)

        tokens_num = extract_email_tokens("jordan_crawfish111@yahoo.com")
        self.assertIn("crawfish", tokens_num)
        self.assertNotIn("yahoo", tokens_num)

    def test_try_complete_last_word(self):
        # Truncation completion from email
        name, completed, conf = try_complete_last_word("WAGON WHEEL RANCH HUNTIN", 24, "curt@dakota-pheasant-hunting.com")
        self.assertTrue(completed)
        self.assertEqual(name, "WAGON WHEEL RANCH Hunting")
        self.assertGreaterEqual(conf, 0.90)

        name, completed, conf = try_complete_last_word("CLAWDADDYS BAYOU CRAWFIS", 24, "jordan_crawfish111@yahoo.com")
        self.assertTrue(completed)
        self.assertEqual(name, "CLAWDADDYS BAYOU Crawfish")

        # Business dictionary completion
        name, completed, conf = try_complete_last_word("LOS SABORES LATINOS STOR", 24, "salvador@icloud.com")
        self.assertTrue(completed)
        self.assertEqual(name, "LOS SABORES LATINOS Store")

    def test_casing_and_acronyms(self):
        # Acronyms preserved
        self.assertEqual(format_merchant_name("Glacial HVAC Pro"), "Glacial HVAC Pro")
        self.assertEqual(format_merchant_name("REGEN RX PRODUCT"), "Regen RX Product")
        self.assertEqual(format_merchant_name("MD AUTO REPAIR"), "MD Auto Repair")
        self.assertEqual(format_merchant_name("BCL COSMOS"), "BCL Cosmos")
        self.assertEqual(format_merchant_name("ACE PRECISION SOLUTIONS"), "ACE Precision Solutions")
        self.assertEqual(format_merchant_name("IV HAIR SALON CORP"), "IV Hair Salon Corp")
        self.assertEqual(format_merchant_name("THE CARE CENTER NH"), "The Care Center NH")
        self.assertEqual(format_merchant_name("BSPGC - HIGHLAND"), "BSPGC - Highland")

        # Ordinals
        self.assertEqual(format_merchant_name("5TH AVE BARBER & SHAVE SHOP"), "5th Ave Barber & Shave Shop")
        self.assertEqual(format_merchant_name("34TH JUDICIAL DIVERSION"), "34th Judicial Diversion")

        # Apostrophes and hyphens
        self.assertEqual(format_merchant_name("ANOTHER MAN'S TREASURE"), "Another Man's Treasure")
        self.assertEqual(format_merchant_name("DROP-N-GO ARAPAHOE CROSSING"), "Drop-N-Go Arapahoe Crossing")
        self.assertEqual(format_merchant_name("LA CASA DULCE"), "La Casa Dulce")

        # Mixed-case records with uppercase phrases
        self.assertEqual(format_merchant_name("MEN'S DISTRICT Moreno"), "Men's District Moreno")
        self.assertEqual(format_merchant_name("In THE LIGHT SERVICES -Susan Grau"), "In The Light Services -Susan Grau")
        self.assertEqual(format_merchant_name("GOLDEN GATES Cushman"), "Golden Gates Cushman")
        self.assertEqual(format_merchant_name("DROP-N-GO Arapahoe Crossing"), "Drop-N-Go Arapahoe Crossing")
        self.assertEqual(format_merchant_name("UNIV OF HC--Bursars"), "Univ Of HC--Bursars")

    def test_process_merchant_record_flags(self):
        # Normal record: no attention needed
        cleaned, att, conf = process_merchant_record("LA CASA DULCE INC", "LACASADULCE@OUTLOOK.COM")
        self.assertEqual(cleaned, "La Casa Dulce")
        self.assertEqual(att, "")

        # Placeholder / dummy
        cleaned, att, conf = process_merchant_record("do not use", "admin@domain.com")
        self.assertEqual(att, "Attention")

        # Name containing the word 'old'
        cleaned, att, conf = process_merchant_record("old acct EXTREME GAME", "user@domain.com")
        self.assertEqual(att, "Attention")

        cleaned, att, conf = process_merchant_record("OLD TOWN GARDENS", "user@domain.com")
        self.assertEqual(att, "Attention")

        cleaned, att, conf = process_merchant_record("The Bean Bandit (OLD)", "user@domain.com")
        self.assertEqual(att, "Attention")

        # Incomplete / cut off at length 24
        cleaned, att, conf = process_merchant_record("FIVE ACES ADVERTISING AN", "FIVEACESADVERTISING@YAHOO.COM")
        self.assertEqual(cleaned, "Five Aces Advertising")
        self.assertEqual(att, "Attention")

        # Single letter trailing cutoff
        cleaned, att, conf = process_merchant_record("Memorial Monuments Oak G", "Monumentsofla@yahoo.com")
        self.assertEqual(att, "Attention")

        # Truncated name requiring email, but email is missing or empty -> must flag Attention
        cleaned, att, conf = process_merchant_record("WAGON WHEEL RANCH HUNTIN", "")
        self.assertEqual(att, "Attention")

        cleaned, att, conf = process_merchant_record("CLAWDADDYS BAYOU CRAWFIS", None)
        self.assertEqual(att, "Attention")

        # Non-truncated name with missing/empty email -> does not need attention
        cleaned, att, conf = process_merchant_record("LA CASA DULCE INC", "")
        self.assertEqual(att, "")

        # Expanding trailing Serv / Serv. to Service
        cleaned, att, conf = process_merchant_record("Pro Master Cleaning Serv", "")
        self.assertEqual(cleaned, "Pro Master Cleaning Service")

        cleaned, att, conf = process_merchant_record("AVONDALE INSPECTION SERV", "")
        self.assertEqual(cleaned, "Avondale Inspection Service")

        # Glued compound words with digits (e.g. INKYENVY937 -> Inky Envy 937)
        cleaned, att, conf = process_merchant_record("Inkyenvy937 LLC", "")
        self.assertEqual(cleaned, "Inky Envy 937")

        cleaned, att, conf = process_merchant_record("INKYENVY937", "")
        self.assertEqual(cleaned, "Inky Envy 937")

        # Flagging names with dotted abbreviations like F.H. / F.h.
        cleaned, att, conf = process_merchant_record("MCCAFFERTY-SWEENEY  F.H.", "")
        self.assertEqual(att, "Attention")

        # Flagging names with MMIS prefix
        cleaned, att, conf = process_merchant_record("MMIS CFI PROD 112719-4", "")
        self.assertEqual(att, "Attention")

        # Flagging names with DBA in the name
        cleaned, att, conf = process_merchant_record("Faithful Roofing & Construction INC (DBA: Storm Guard of Plymouth)", "")
        self.assertEqual(att, "Attention")

        # Flagging names that remain all-capitalized (e.g. YAHWEH4U C&A)
        cleaned, att, conf = process_merchant_record("YAHWEH4U C&A", "")
        self.assertEqual(att, "Attention")

    def test_find_column_indices_flexible(self):
        from clean_merchants import find_column_indices
        # Typical header
        m_idx, e_idx = find_column_indices(['id', 'uuid', 'mid', 'merchant_name', 'merchant_name', 'owner_email'])
        self.assertEqual(m_idx, 3)
        self.assertEqual(e_idx, 5)

        # Variations of merchant name
        m_idx, e_idx = find_column_indices(['id', 'Merchant Name', 'email'])
        self.assertEqual(m_idx, 1)
        self.assertEqual(e_idx, 2)

        m_idx, e_idx = find_column_indices(['client_id', 'BUSINESS_NAME', 'owner_email'])
        self.assertEqual(m_idx, 1)
        self.assertEqual(e_idx, 2)

        # Missing email column -> email_idx should be None without error
        m_idx, e_idx = find_column_indices(['store_id', 'dba_name', 'phone', 'address'])
        self.assertEqual(m_idx, 1)
        self.assertIsNone(e_idx)

if __name__ == '__main__':
    unittest.main()
