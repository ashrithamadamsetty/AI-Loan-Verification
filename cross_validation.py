import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import json
import os
import re
from gemini_service import GeminiService, get_gemini_service

# Optional executable overrides; system PATH is used by default.
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
POPPLER_PATH = os.getenv("POPPLER_PATH", "").strip()
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
POPPLER_INSTALLED = bool(POPPLER_PATH and os.path.isdir(POPPLER_PATH))

class CrossValidationCore:
    def __init__(self, gemini: GeminiService | None = None):
        self.gemini = gemini or get_gemini_service()
        self.system_instruction = (
            "You are a document extraction AI. Extract and compare information from "
            "documents and return only valid JSON without explanations."
        )
        print(f"Initialized CrossValidationCore with Gemini model: {self.gemini.model}")

    # ===== OCR Extraction =====
    def extract_text_from_image(self, image_path):
        print(" Extracting text from image...")
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return ""
        image = Image.open(image_path)
        try:
            return pytesseract.image_to_string(image).strip()
        except Exception as e:
            print(f"❌ Failed to OCR image: {e}")
            return ""

    def extract_text_from_pdf(self, pdf_path):
        print(" Extracting text from PDF...")
        if not os.path.exists(pdf_path):
            print(f"❌ File not found: {pdf_path}")
            return ""
        try:
            # Try with poppler_path if installed, otherwise try system PATH
            if POPPLER_INSTALLED:
                pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
            else:
                # Try without explicit path (will use system PATH)
                pages = convert_from_path(pdf_path)
        except Exception as e:
            print(f"❌ Failed to OCR PDF: {e}")
            if "poppler" in str(e).lower() or "Unable to get page count" in str(e):
                print("   💡 Poppler is not installed or not in PATH")
                print("   Download: https://github.com/oschwartz10612/poppler-windows/releases/")
                print("   Extract to: C:\\Program Files\\poppler\\")
            return ""
        full_text = ""
        for i, page in enumerate(pages):
            try:
                full_text += pytesseract.image_to_string(page) + "\n"
            except Exception as ocr_error:
                print(f"⚠️ Failed to OCR page {i+1}: {str(ocr_error)[:100]}")
                # Continue with other pages
                continue
        return full_text.strip()

    # ===== Clean LLM Response =====
    def clean_llm_response(self, content: str) -> str:
        print("Cleaning LLM response...")
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content

    # ===== Shared Gemini Request Function =====
    def _send_llm_request(self, prompt):
        print("Sending Gemini request...")
        try:
            result = self.gemini.generate_json(
                prompt,
                system_instruction=self.system_instruction,
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            print(f"Gemini request failed: {exc}")
            return {}

    # ===== Offer Letter Extraction =====
    def extract_offer_letter_info(self, ocr_text):
        if not ocr_text:
            return {}
        prompt = f"""
You are an expert HR document parser.
Extract the following details from the OFFER LETTER if present in the document text below and return ONLY JSON in this format:
{{
  "Employee Name": "",
  "Employer": "",
  "Designation": "",
  "Joining Date": "",
  "CTC (Annual)": "",
  "Basic Salary (Monthly)": "",
  "Valiable pay: "",
  "Bonus": "",
  "Tax or Deductions": "",
  "Issue Date": ""
}}

Rules:
- Extract the employee name from the offer letter.
- Extract numeric values without commas or currency symbols.
- Convert all dates into DD-MM-YYYY format if possible.
- If any field is not found, leave it as an empty string.

Offer Letter Text:
\"\"\"{ocr_text}\"\"\"

Return ONLY valid JSON, no other text.
"""
        return self._send_llm_request(prompt)

    # ===== Payslip Extraction =====
    def extract_payslip_info(self, ocr_text):
        if not ocr_text:
            return {}
        prompt = f"""
You are an expert payroll document analyzer. Extract the following fields and return ONLY valid JSON (no explanations, no markdown):
Extract the following details in JSON format:
- Employee Name
- PAN Number
- Month or Pay Period
- Employer
- Base Salary
- Net Salary or Take Home Pay
- Income Tax (monthly deduction)
- Total Tax Deducted (TDS) (cumulative year-to-date)
- PF Deducted for this month
- UAN Number
- Any Bonus or Incentive if mentioned

Rules:
- PF Deducted → Extract the monthly PF deduction amount:
  * Look for amounts near text like "Ee PF contribution", "Employee PF", "EE PF", "EPF" in the Deductions section.
  * The monthly PF is typically 12% of Basic Salary (e.g., if Basic = 37,500, then PF ≈ 4,500).
  * If you see "Provident Fund" with a large amount (like 54,000), that's cumulative - DON'T use it.
  * If you can't find the exact PF deduction amount but see "Ee PF contribution" mentioned, calculate it as: Basic Salary × 0.12
  * If completely missing, leave as empty string.
- Income Tax → Extract the monthly income tax from the Deductions section (e.g., 8,961.00), not the cumulative TDS.
- Total Tax Deducted (TDS) → Extract the cumulative year-to-date TDS (usually from tax computation section).
- Extract numeric values without currency symbols or commas.
- Month should be a clear month name or period (e.g., "March 2024").
- "Net Salary" means take-home pay after deductions.
- If a field is missing, leave it as an empty string.

Respond ONLY in JSON like this:
{{
  "Employee Name": "",
  "PAN": "",
  "Month": "",
  "Employer": "",
  "Base Salary": "",
  "Net Salary": "",
  "Income Tax": "",
  "Total Tax Deducted (TDS)": "",
  "PF Deducted": "",
  "UAN Number": "",
  "Bonus": ""
  }}
Payslip Text:

\"\"\"{ocr_text}\"\"\"

Return ONLY valid JSON, no other text.
"""
        return self._send_llm_request(prompt)

    # ===== Bank Statement Extraction =====
    def extract_bank_info(self, ocr_text):
        if not ocr_text:
            return {}
        prompt = f"""
Extract the following fields from the bank statement text and return ONLY valid JSON (no explanations, no markdown):
Extraction Rules for "Salary Credited Amount":
- Identify the amount labeled as "Salary Credited" or similar variations (e.g., "Salary Deposit," "Credit Amount").
- Ensure the salary is extracted in a numeric format with exactly two decimal places, e.g., 9999.00 (not 9999 or 9999,00).
- Ignore commas or symbols and extract only the numeric value
{{
  "Account Holder Name": "",
  "Account Number": "",
  "IFSC Code": "",
  "Bank Name": "",
  "Salary Credited Amount": "",
  "Salary Credit Date": ""
}}

Bank Statement Text:
\"\"\"{ocr_text}\"\"\"

Return ONLY valid JSON, no other text.
"""
        return self._send_llm_request(prompt)

    # ===== Cross Check Salary =====
    def cross_check_salary(self, payslip_json, bank_json):
        prompt = f"""
Check if the salary in the bank matches the payslip.
1 Names may appear in different orders or cases (e.g., "Mardana yaswanth" vs. "YASWANTH MARDANA").
 Your task is to check if they all refer to the same person, regardless of:
    - Order of first and last name
    - Case sensitivity
    - Extra spaces or punctuation
 Return ONLY valid JSON (no explanations, no markdown):
2 Compare the payslip month with the salary credit date in the bank statement to check if they refer to the same salary period.
    - Consider both month and year.
    - Handle different date formats (e.g., "April 2018" and "30/04/18" should match).
    - Ignore day differences — only month and year must match.
{{
  "Employee Name Match": true/false,
  "Salary Match": true/false,
  "Month of salary": true/false,
  "Overall Match": true/false,
  "Discrepancies": ["list any differences found mentioning the difference"]

}}

Payslip:
{json.dumps(payslip_json, indent=2)}

Bank Statement:
{json.dumps(bank_json, indent=2)}

Return ONLY valid JSON, no other text.
"""
        return self._send_llm_request(prompt)

    # ===== Semantic Comparison =====
    def compare_with_llm(self, payslip_json, offer_json):
        print("🔍 Comparing Payslip vs Offer Letter...")
        if not payslip_json or not offer_json:
            print("⚠️ Warning: Empty payslip or offer letter data")
            return {}
        
        prompt = f"""
Compare these fields between Payslip and Offer Letter semantically: Employee Name, Base Salary.
1 Names may appear in different orders or cases (e.g., "Mardana yaswanth" vs. "YASWANTH MARDANA").
 Your task is to check if they all refer to the same person, regardless of:
    - Order of first and last name
    - Case sensitivity
    - Extra spaces or punctuation
Return ONLY a JSON object with the following structure (no explanations, no markdown):
{{
  "Employee Name Match": true/false,
  "Base Salary Match": true/false,
  "Overall Match": true/false,
  "Discrepancies": ["list any differences found mentioning that diffence"]
}}

Payslip:
{json.dumps(payslip_json, indent=2)}

Offer Letter:
{json.dumps(offer_json, indent=2)}

Return ONLY valid JSON, no other text.
"""
        result = self._send_llm_request(prompt)
        print(f"✅ Comparison result: {result}")
        return result

    # ===== Form 16 Extraction =====
    def extract_employee_pan(self, text: str) -> str:
        pattern_context = r"(?:PAN\s*of\s*(?:the\s*)?(?:Employee|Specified\s*senior\s*citizen)[^A-Z0-9]{0,40})([A-Z]{5}[0-9]{4}[A-Z])"
        match = re.search(pattern_context, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        all_pans = re.findall(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text)
        if len(all_pans) >= 2:
            return all_pans[-1]
        return all_pans[0] if all_pans else ""

    def extract_form16_info(self, text):
        if not text:
            return {}
        prompt = f"""
You are a tax document parser. Analyze the following Form 16 text carefully.

It contains details of TDS deductions and multiple PANs.
⚠️ IMPORTANT:
- The "Employee PAN" is found under "PAN of the Employee" or "Employee/Specified senior citizen".
- Ignore the "PAN of the Deductor".
- Extract all TDS entries, including date and amount (even from previous years).

Return STRICT JSON:
{{
  "Employee Name": "",
  "PAN": "",
  "Employer TAN": "",
  "Total TDS": "",
  "TDS Records": [
    {{"Date": "DD-MM-YYYY", "Month": "", "Tax Deducted": ""}},
    ...
  ]
}}
Form 16 Text:
{text}

Return ONLY valid JSON, no other text.
"""
        response = self._send_llm_request(prompt)
        info = response if isinstance(response, dict) else {}
        employee_pan = self.extract_employee_pan(text)
        if employee_pan:
            info["PAN"] = employee_pan
        return info

    # ===== Cross Check Payslip vs Form16 =====
    def cross_check_payslip_form16(self, payslip_json, form16_json):
        prompt = f"""
You are an AI verifier. Compare the PAYSLIP and FORM 16 information below and check if the key details are consistent.

Compare the PAYSLIP and FORM 16 info. Return ONLY valid JSON (no explanations, no markdown):
Check and verify the following:
    1 Employee Name matches
    - Names may appear in different orders or cases (e.g., "Mardana yaswanth" vs. "YASWANTH MARDANA").
    Your task is to check if they all refer to the same person, regardless of:
    - Order of first and last name
    - Case sensitivity
    - Extra spaces or punctuation

    2 PAN matches
    3 Income Tax in payslip matches the next month's Tax Deducted in Form 16
    **(For example, if the payslip month is January 2025, compare it with February 2025 month's tax deducted record in Form 16)**
    - If the above cannot be verified, return false for that field.
    Return **ONLY JSON**, no extra text. Use this format:
{{
  "PAN Match": true/false,
  "Employee Name Match": true/false,
  "Tax Deduction Match": true/false,
  "Overall Match": true/false,
  "Discrepancies": ["list any differences found mentioning that diffence"]
}}

Payslip:
{json.dumps(payslip_json, indent=2)}

Form 16:
{json.dumps(form16_json, indent=2)}

Return ONLY valid JSON, no other text.
"""
        return self._send_llm_request(prompt)
