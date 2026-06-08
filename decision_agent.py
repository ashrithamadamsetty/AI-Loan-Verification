import json
import os
import re
from tabulate import tabulate

# ===========================================
# Tool 1: Verify PAN Details
# ===========================================
def verify_pan_details(inputs: str) -> str:
    """
    Checks if PAN number in AA data follows correct format (AAAAA9999A pattern).
    Input format: 'aa_data.json|final_results.json' (pipe-separated file paths)
    """
    try:
        aa_path, doc_path = inputs.split("|")
        with open(aa_path.strip()) as f1, open(doc_path.strip()) as f2:
            aa, doc = json.load(f1), json.load(f2)

        pan = aa.get("personal_info", {}).get("pan", "").strip().upper()
        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
        valid = bool(re.match(pattern, pan))

        return json.dumps({
            "PAN": pan,
            "ValidFormat": valid,
            "Status": "Valid PAN" if valid else "Invalid PAN format"
        }, indent=2)

    except Exception as e:
        return f"Error verifying PAN: {e}"

# ===========================================
# Tool 2: Check Tax Paid Consistency
# ===========================================
def check_tax_paid_consistency(inputs: str) -> str:
    """
    Verifies if tax paid in AA data matches tax deducted in payslip documents.
    Allows ±1000 variance. Input format: 'aa_data.json|final_results.json'
    """
    try:
        aa_path, doc_path = inputs.split("|")
        with open(aa_path.strip()) as f1, open(doc_path.strip()) as f2:
            aa, doc = json.load(f1), json.load(f2)

        aa_tax = float(aa["income_details"]["tax_paid"])
        doc_tax = float(doc["payslip"]["Tax Deducted"])

        diff = abs(aa_tax - doc_tax)
        match = diff < 1000

        return json.dumps({
            "AA Tax Paid": aa_tax,
            "Document Tax Deducted": doc_tax,
            "Difference": round(diff, 2),
            "Status": "Match" if match else "Mismatch"
        }, indent=2)

    except Exception as e:
        return f"Error verifying tax consistency: {e}"

# ===========================================
# Tool 3: Verify Bank Account
# ===========================================
def verify_bank_account_decision(inputs: str) -> str:
    """
    Validates bank account number and currency in AA data match with documents.
    Input format: 'aa_data.json|final_results.json'
    """
    try:
        aa_path, doc_path = inputs.split("|")
        with open(aa_path.strip()) as f1, open(doc_path.strip()) as f2:
            aa, doc = json.load(f1), json.load(f2)

        aa_acc = aa["bank_account"]["account_number"].strip()
        aa_currency = aa["bank_account"]["currency"]
        doc_acc = doc["bank"]["Account Number"].strip()
        doc_currency = "INR"

        acc_match = (aa_acc == doc_acc)
        curr_match = (aa_currency == doc_currency)

        return json.dumps({
            "AA Account": aa_acc,
            "Document Account": doc_acc,
            "Currency Match": curr_match,
            "Account Match": acc_match,
            "Status": "Verified" if acc_match and curr_match else "Mismatch Found"
        }, indent=2)

    except Exception as e:
        return f"Error verifying bank account: {e}"

# ===========================================
# Helper Functions
# ===========================================
def extract_numeric(value):
    """Extract numeric value from various formats"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = re.sub(r"[^\d.]", "", value.replace(",", ""))
        try:
            return float(value)
        except:
            return None
    return None

def recursive_search(obj):
    """Recursively search JSON for financial data"""
    data = {"salary": None, "bonus": None, "allowances": None, "tax": None,
             "balance": None, "emi": None, "existing_loan": None, "name": None}

    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = k.lower()
            num = extract_numeric(v)
            if "salary" in k_lower or "income" in k_lower:
                data["salary"] = num or data["salary"]
            elif "bonus" in k_lower:
                data["bonus"] = num or data["bonus"]
            elif "allowance" in k_lower:
                data["allowances"] = num or data["allowances"]
            elif "tax" in k_lower:
                data["tax"] = num or data["tax"]
            elif "balance" in k_lower:
                data["balance"] = num or data["balance"]
            elif "emi" in k_lower:
                data["emi"] = num or data["emi"]
            elif "loan" in k_lower and num:
                data["existing_loan"] = num or data["existing_loan"]
            elif "name" in k_lower and isinstance(v, str):
                data["name"] = v
            if isinstance(v, (dict, list)):
                inner = recursive_search(v)
                for key, val in inner.items():
                    if val is not None:
                        data[key] = val

    elif isinstance(obj, list):
        for item in obj:
            inner = recursive_search(item)
            for key, val in inner.items():
                if val is not None:
                    data[key] = val
    return data

# ===========================================
# Tool 4: Extract Financial Data
# ===========================================
def extract_financial_data(file_path: str):
    """Extracts salary, balance, tax, and loan info from AA_data.json with proper field mapping."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Initialize result dict
        result = {
            "salary": 0,
            "bonus": 0,
            "allowances": 0,
            "tax": 0,
            "balance": 0,
            "emi": 0,
            "name": ""
        }
        
        # Extract from income_details (monthly data)
        income = data.get("income_details", {})
        result["salary"] = extract_numeric(income.get("monthly_salary", 0))
        result["bonus"] = extract_numeric(income.get("bonus", 0))
        result["allowances"] = extract_numeric(income.get("allowances", 0))
        result["tax"] = extract_numeric(income.get("tax_paid", 0))
        
        # Extract from bank_account (not account_details)
        bank = data.get("bank_account", {})
        result["balance"] = extract_numeric(bank.get("balance", 0))
        
        # Extract total EMI from all loan_obligations
        loans = data.get("loan_obligations", [])
        total_emi = sum(extract_numeric(loan.get("emi", 0)) for loan in loans)
        result["emi"] = total_emi
        
        # Get customer name from personal_info
        personal = data.get("personal_info", {})
        result["name"] = personal.get("name", data.get("customer_name", ""))
        
        print(f"💰 Extracted from {file_path}:")
        print(f"   - Monthly Salary: {result['salary']}")
        print(f"   - Bonus: {result['bonus']}")
        print(f"   - Allowances: {result['allowances']}")
        print(f"   - Tax: {result['tax']}")
        print(f"   - Balance: {result['balance']}")
        print(f"   - Total EMI: {result['emi']}")
        
        return {k: v for k, v in result.items() if v is not None}
    except Exception as e:
        return {"error": str(e)}

# ===========================================
# Tool 5: Calculate Loan Plans
# ===========================================
def calculate_emi(principal, rate, months):
    """Calculate EMI for a loan"""
    r = rate / (12 * 100)
    if r == 0:
        return principal / months
    emi = principal * r * ((1 + r) ** months) / (((1 + r) ** months) - 1)
    return emi

def calculate_loan_plans(prompt: str):
    """
    Calculates loan eligibility and generates loan plans with different tenures.
    Example prompt: "Calculate loan for 100000 using C:/path/to/AA_data.json"
    """
    try:
        # Extract requested amount from prompt
        amount_match = re.search(r"(\d[\d,]*)", prompt)
        requested_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 100000

        # Extract file path - look for full path or just filename
        file_path_match = re.search(r'using\s+["\']?([^"\']+\.json)["\']?', prompt, re.IGNORECASE)
        if not file_path_match:
            # Try to find any .json file path in the prompt
            file_path_match = re.search(r'([A-Za-z]:[/\\][^"\s]+\.json|[/\\][^"\s]+\.json|[\w\-_]+\.json)', prompt)
        
        if not file_path_match:
            return {"error": "Please provide a JSON file path in the prompt. Example: 'Calculate loan for 100000 using /path/to/AA_data.json'"}
        
        file_path = file_path_match.group(1)
        print(f"📊 Extracting financial data from: {file_path}")

        # Extract financial data
        financial_data = extract_financial_data(file_path)
        
        print(f"💰 Financial Data: {financial_data}")

        if "error" in financial_data:
            return {"error": f"Failed to extract data: {financial_data['error']}"}

        salary = financial_data.get("salary") or 0
        bonus = financial_data.get("bonus") or 0
        allowances = financial_data.get("allowances") or 0
        balance = financial_data.get("balance") or 0
        existing_loan = financial_data.get("existing_loan") or 0
        emi = financial_data.get("emi") or 0
        name = financial_data.get("name") or "Customer"

        # If no salary found, return error with details
        if salary == 0:
            return {
                "error": f"No salary data found in file. Financial data: {financial_data}",
                "customer_name": name,
                "risk_level": "Unknown",
                "max_eligible_amount": 0,
                "status": "Cannot calculate - no income data available",
                "loan_plan_table": "No loan plans available - income data missing"
            }

        # Calculate total monthly income
        # Salary is monthly, bonus is typically annual (divide by 12), allowances are monthly
        monthly_bonus = bonus / 12 if bonus > 0 else 0
        monthly_income = salary + allowances + monthly_bonus
        dti = (emi / monthly_income) if monthly_income > 0 else 0

        print(f"💵 Monthly Income: INR {monthly_income:,.2f}")
        print(f"   - Base Salary: INR {salary:,.2f}")
        print(f"   - Monthly Allowances: INR {allowances:,.2f}")
        print(f"   - Monthly Bonus: INR {monthly_bonus:,.2f}")
        print(f"💳 Existing EMI: INR {emi:,.2f}")
        print(f"📊 DTI: {dti*100:.2f}%")

        # Risk tier based on DTI
        if dti < 0.2:
            risk_level = "Low"
            base_rate = 10.0
        elif dti < 0.35:
            risk_level = "Medium"
            base_rate = 12.0
        else:
            risk_level = "High"
            base_rate = 15.0

        max_eligible = max(0, (monthly_income * 10) - (existing_loan * 0.2))

        if requested_amount <= max_eligible:
            status = f"Eligible for INR {requested_amount:,.2f}"
            eligible_amount = requested_amount
        else:
            status = f"Requested INR {requested_amount:,.2f} exceeds limit. Max possible: INR {max_eligible:,.2f}"
            eligible_amount = max_eligible

        print(f"✅ Eligible Amount: INR {eligible_amount:,.2f}")

        # Tenures and dynamic interest rate - 3 plans
        tenures = [12, 24, 36]
        loan_plans = []
        for tenure in tenures:
            interest_rate = max(7.5, base_rate - (tenure / 60))
            emi_value = calculate_emi(eligible_amount, interest_rate, tenure)
            total_payment = emi_value * tenure
            total_interest = total_payment - eligible_amount
            loan_plans.append([
                f"{tenure} months",
                f"{interest_rate:.2f}%",
                f"INR {emi_value:,.2f}",
                f"INR {total_payment:,.2f}",
                f"INR {total_interest:,.2f}"
            ])

        table = tabulate(loan_plans,
                         headers=["Tenure", "Interest Rate", "EMI", "Total Payment", "Total Interest"],
                         tablefmt="fancy_grid")

        return {
            "customer_name": name,
            "risk_level": risk_level,
            "max_eligible_amount": max_eligible,
            "status": status,
            "loan_plan_table": table
        }

    except Exception as e:
        import traceback
        return {"error": f"{str(e)}\n{traceback.format_exc()}"}

DECISION_SYSTEM_PROMPT = """You are a financial decision agent for loan approval with expertise in risk assessment and loan structuring.
Assess risk based on document tampering, DTI ratio (below 20 percent Low, 20-35 percent Medium, above 35 percent High), and verification failures.
Provide loan recommendations with specific INR amounts, interest rates, EMI, and tenure options.
Return exactly the JSON shape requested by the user. Keep the response field plain text without markdown, emojis, or decorative symbols.
"""


class GeminiDecisionAgent:
    """Callable adapter that preserves the previous decision-agent contract."""

    def __init__(self, gemini=None):
        from gemini_service import get_gemini_service

        self.gemini = gemini or get_gemini_service()

    def __call__(self, prompt: str) -> str:
        result = self.gemini.generate_json(
            prompt,
            system_instruction=DECISION_SYSTEM_PROMPT,
        )
        return json.dumps(result, ensure_ascii=False)


def decision_agent():
    return GeminiDecisionAgent()


def descision_agent():
    """Backward-compatible alias for the original misspelled public function."""
    return decision_agent()
