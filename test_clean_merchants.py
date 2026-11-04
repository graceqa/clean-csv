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

if __name__ == '__main__':
    unittest.main()
