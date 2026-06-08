# Supporting libraries
import json
import re
import warnings
warnings.filterwarnings('ignore')

# ===========================================
# 🔹 Tool 1: Greeting Tool
# ===========================================
def greet_user(query: str) -> str:
    return "Hello! The agent is working correctly."

# ===========================================
# 🔹 Tool 2: Verify AA Data
# ===========================================
def verify_aa_data(inputs: str) -> str:
    """
    Verifies extracted offer/payslip/bank document data with AA (Account Aggregator) data.
    Input format: 'aa_json_path|final_results_json_path'
    """
    try:
        aa_path, doc_path = inputs.split("|")
        with open(aa_path.strip()) as f1, open(doc_path.strip()) as f2:
            aa, doc = json.load(f1), json.load(f2)

        results = {}
        # Extract AA data
        aa_name = aa["personal_info"]["name"].strip().lower()
        aa_account = aa["bank_account"]["account_number"].strip()
        aa_salary = float(aa["income_details"]["monthly_salary"])
        aa_bonus = float(aa["income_details"]["bonus"])
        aa_tax = float(aa["income_details"]["tax_paid"])
        aa_currency = aa["bank_account"]["currency"]

        # Extract Document data
        doc_offer = doc.get("offer", {})
        doc_payslip = doc.get("payslip", {})
        doc_bank = doc.get("bank", {})

        doc_name = doc_offer.get("Employee Name", "").strip().lower()
        doc_account = doc_bank.get("Account Number", "").strip()
        
        # Safe float conversion with fallback to 0
        def safe_float(value, default=0):
            try:
                if value == "" or value is None:
                    return default
                return float(str(value).replace(",", ""))
            except (ValueError, TypeError):
                return default
        
        doc_salary = safe_float(doc_payslip.get("Base Salary", 0))
        doc_bonus = safe_float(doc_offer.get("Bonus", 0))
        doc_tax = safe_float(doc_payslip.get("Income Tax", 0))
        doc_currency = "INR"  # Assuming Indian context

        # Comparison rules
        results["Name Match"] = (aa_name == doc_name)
        results["Account Number Match"] = (aa_account == doc_account)
        results["Salary Match"] = abs(aa_salary - doc_salary) < 1000
        results["Bonus Match"] = abs(aa_bonus - doc_bonus) < 2000
        results["Tax Match"] = abs(aa_tax - doc_tax) < 1000
        results["Currency Match"] = (aa_currency == doc_currency)

        results["AA Verification Status"] = (
            "✅ All fields verified successfully"
            if all(results.values())
            else "❌ One or more mismatches found"
        )

        return json.dumps(results, indent=2)

    except Exception as e:
        return f"Error verifying AA data: {e}"

# ===========================================
# 🔹 Tool 3: Verify PAN
# ===========================================
def verify_pan_details(inputs: str) -> str:
    try:
        aa_path, _ = inputs.split("|")
        with open(aa_path.strip()) as f:
            aa = json.load(f)

        pan = aa.get("personal_info", {}).get("pan", "").strip().upper()
        valid = bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan))

        return json.dumps({
            "PAN": pan,
            "ValidFormat": valid,
            "Status": "✅ Valid PAN" if valid else "❌ Invalid PAN format"
        }, indent=2)
    except Exception as e:
        return f"Error verifying PAN: {e}"

# ===========================================
# 🔹 Tool 4: Verify Bank Account
# ===========================================
def verify_bank_account(inputs: str) -> str:
    print("AHAH")
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
            "Status": "✅ Verified" if acc_match and curr_match else "❌ Mismatch Found"
        }, indent=2)
    except Exception as e:
        return f"Error verifying bank account: {e}"

# ===========================================
# 🔹 Tool 5: Loan Eligibility
# ===========================================
def calculate_risk_based_loan_eligibility(inputs: str) -> str:
    """
    inputs: 'aa_json_path|final_results_json_path'
    """
    try:
        aa_path, _ = inputs.split("|")  # Only need AA data
        with open(aa_path.strip()) as f:
            aa = json.load(f)

        income_details = aa.get("income_details", {})
        loans = aa.get("loan_obligations", [])
        credit_score = aa.get("credit_score", None)

        monthly_income = float(income_details.get("monthly_salary", 0))
        total_emi = sum(float(l.get("emi", 0)) for l in loans)
        dti_ratio = round((total_emi / (monthly_income + 1e-9)) * 100, 2)

        # Determine Risk Tier
        if credit_score:
            if credit_score > 750:
                tier, rate = "Super Prime", 0.105
            elif credit_score >= 700:
                tier, rate = "Prime", 0.12
            elif credit_score >= 650:
                tier, rate = "Near Prime", 0.14
            elif credit_score >= 600:
                tier, rate = "Subprime", 0.16
            else:
                tier, rate = "Deep Subprime", 0.18
        else:
            if dti_ratio < 30:
                tier, rate = "Prime", 0.12
            elif dti_ratio < 50:
                tier, rate = 0.14, "Near Prime"
            else:
                tier, rate = "Subprime", 0.16

        max_emi_allowed = 0.4 * monthly_income
        available_emi_capacity = max_emi_allowed - total_emi

        if available_emi_capacity <= 0:
            return json.dumps({
                "Monthly Income": monthly_income,
                "Existing EMI": total_emi,
                "Debt-to-Income Ratio": f"{dti_ratio}%",
                "Risk Tier": tier,
                "Interest Rate (Annual)": f"{rate*100:.2f}%",
                "Eligible Loan": 0,
                "Status": "❌ No available EMI capacity"
            }, indent=2)

        tenure_months = 60
        monthly_rate = rate / 12
        numerator = available_emi_capacity * ((1 + monthly_rate) ** tenure_months - 1)
        denominator = monthly_rate * ((1 + monthly_rate) ** tenure_months)
        eligible_amount = numerator / denominator

        return json.dumps({
            "Monthly Income": round(monthly_income, 2),
            "Existing EMI": round(total_emi, 2),
            "Debt-to-Income Ratio": f"{dti_ratio}%",
            "Credit Score": credit_score or "Not Available",
            "Risk Tier": tier,
            "Interest Rate (Annual)": f"{rate*100:.2f}%",
            "Available EMI Capacity": round(available_emi_capacity, 2),
            "Eligible Loan Amount (5Y)": round(eligible_amount, 2),
            "Status": "✅ Eligible for Loan"
        }, indent=2)
    except Exception as e:
        return f"Error calculating risk-based loan eligibility: {e}"
