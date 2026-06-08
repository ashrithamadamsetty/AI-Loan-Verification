
from typing import Dict, Any, List
from cross_validation import CrossValidationCore
from document_analyzer import DocumentAnalyzerCore
from account_aggregator import verify_aa_data
from decision_agent import calculate_loan_plans, decision_agent, extract_financial_data
import json
import os
import re
import concurrent.futures


# Helper function to extract text from AgentResult objects
def extract_agent_response(response):
    """Convert AgentResult to string for JSON serialization"""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if hasattr(response, 'output'):
        return str(response.output)
    if hasattr(response, 'text'):
        return str(response.text)
    if hasattr(response, 'content'):
        return str(response.content)
    return str(response)


# -----------------------------
# Workflow State Management
# -----------------------------
class VerificationState:
    """State management for verification workflow"""
    def __init__(self, documents_folder: str):
        self.documents_folder = documents_folder
        self.manipulation_results = {}
        self.payslip = {}
        self.offer = {}
        self.bank = {}
        self.form16 = {}
        self.payslip_vs_offer = {}
        self.bank_vs_payslip = {}
        self.payslip_vs_form16 = {}
        self.aa_verification = {}
        self.decision_result = {}
        self.workflow_status = "started"
        self.doc_errors = []
        self.cross_errors = []
        self.aa_errors = []
        self.decision_errors = []
        self.errors = []


# -----------------------------
# Orchestrator Agent
# -----------------------------
class VerificationOrchestrator:
    def __init__(self, documents_folder="Documents", loan_id=None, artifact_storage=None):
        self.documents_folder = documents_folder
        
        # Extract loan_id from documents_folder path if not provided
        if loan_id is None:
            # Extract customer_id/loan_id from path (e.g., "Documents/LID12345678" -> "LID12345678")
            loan_id = os.path.basename(documents_folder)
            print(f"📋 Extracted loan_id from path: {loan_id}")
        
        self.loan_id = loan_id
        self.doc_analyzer = DocumentAnalyzerCore(loan_id=loan_id, storage=artifact_storage)
        self.cross_validator = CrossValidationCore()
        self.state = VerificationState(documents_folder)

        # Track node progress
        self.progress = {
            "doc_analyzer": False,
            "cross_validator": False,
            "aa_agent": False,
            "decision_agent": False,
            "finalizer": False
        }
        
        # Initialize decision agent
        self.decision_agent_instance = decision_agent()

    # -----------------------------
    # Helper Methods
    # -----------------------------
    def _update_progress(self, node_name: str):
        self.progress[node_name] = True

    def get_all_files(self):
        return [
            os.path.join(self.documents_folder, f)
            for f in os.listdir(self.documents_folder)
            if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
        ]

    def find_file(self, keyword: str):
        for file in self.get_all_files():
            if keyword.lower() in os.path.basename(file).lower():
                return file
        return None

    # -----------------------------
    # Node 1: Document Analyzer
    # -----------------------------
    def _run_doc_analysis(self) -> Dict[str, Any]:
        try:
            print("\n🔍 NODE 1: DOCUMENT ANALYZER (Running in Parallel Thread)")
            print("   - Scanning all PDFs/images")
            print("   - Detecting manipulation using CNN + ELA + OCR")
            print("   - Calculating risk levels per page")
            print(f"   - Loan ID: {self.loan_id}")
            print(f"   - GradCAM images will be saved under local storage for {self.loan_id}/gradcam/\n")
            manipulation_results = {}
            all_docs = [
                os.path.join(self.documents_folder, f)
                for f in os.listdir(self.documents_folder)
                if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
            ]

            if not all_docs:
                raise FileNotFoundError("No valid documents found.")

            for doc_path in all_docs:
                doc_name = os.path.basename(doc_path)
                print(f"\n📄 Analyzing: {doc_name}")
                analysis = self.doc_analyzer.analyze_document(doc_path, tamper_threshold=0.6, verbose=False)
                manipulation_results[doc_name] = analysis

            self._update_progress("doc_analyzer")
            return {
                "manipulation_results": manipulation_results,
                "doc_errors": []
            }
        except Exception as e:
            self._update_progress("doc_analyzer")
            return {
                "manipulation_results": {},
                "doc_errors": [f"Doc analysis failed: {str(e)}"]
            }

    # -----------------------------
    # Node 2: Cross Validator
    # -----------------------------
    def _run_cross_validation(self) -> Dict[str, Any]:
        try:
            print("\n⚙️ NODE 2: CROSS VALIDATOR (Running in Parallel Thread)")
            print("   - Extracting data from documents")
            print("   - Payslip, Offer Letter, Bank Statement, Form 16")
            print("   - Cross-checking: Payslip vs Offer, Bank vs Payslip, Payslip vs Form16\n")
            payslip_path = self.find_file("payslip")
            offer_path = self.find_file("Offer")
            bank_path = (
                self.find_file("bank")
                or self.find_file("Account")
                or self.find_file("Statement")
            )
            form16_path = self.find_file("form16")

            if not all([payslip_path, offer_path, bank_path]):
                raise FileNotFoundError("Missing payslip/offer/bank documents.")

            # Extract payslip (supports both PDF and image formats)
            if payslip_path.lower().endswith(".pdf"):
                payslip_text = self.cross_validator.extract_text_from_pdf(payslip_path)
            else:
                payslip_text = self.cross_validator.extract_text_from_image(payslip_path)
            payslip_json = self.cross_validator.extract_payslip_info(payslip_text)

            # Extract offer letter (supports both PDF and image formats)
            if offer_path.lower().endswith(".pdf"):
                offer_text = self.cross_validator.extract_text_from_pdf(offer_path)
            else:
                offer_text = self.cross_validator.extract_text_from_image(offer_path)
            offer_json = self.cross_validator.extract_offer_letter_info(offer_text)
            if bank_path.lower().endswith(".pdf"):
                bank_text = self.cross_validator.extract_text_from_pdf(bank_path)
            else:
                bank_text = self.cross_validator.extract_text_from_image(bank_path)
            bank_json = self.cross_validator.extract_bank_info(bank_text)

            # Extract Form 16 if available
            form16_json = {}
            if form16_path:
                print("📄 Extracting Form 16...")
                if form16_path.lower().endswith(".pdf"):
                    form16_text = self.cross_validator.extract_text_from_pdf(form16_path)
                else:
                    form16_text = self.cross_validator.extract_text_from_image(form16_path)
                form16_json = self.cross_validator.extract_form16_info(form16_text)
            else:
                print("⚠️ Form 16 not found, skipping...")

            # Cross-validate using available methods
            payslip_vs_offer = self.cross_validator.compare_with_llm(payslip_json, offer_json)
            bank_vs_payslip = self.cross_validator.cross_check_salary(payslip_json, bank_json)
            payslip_vs_form16 = self.cross_validator.cross_check_payslip_form16(payslip_json, form16_json) if form16_json else {}

            self._update_progress("cross_validator")
            return {
                "payslip": payslip_json,
                "offer": offer_json,
                "bank": bank_json,
                "form16": form16_json,
                "payslip_vs_offer": payslip_vs_offer,
                "bank_vs_payslip": bank_vs_payslip,
                "payslip_vs_form16": payslip_vs_form16,
                "cross_errors": []
            }
        except Exception as e:
            import traceback
            print(f"❌ Cross validation error: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            self._update_progress("cross_validator")
            return {
                "payslip": {},
                "offer": {},
                "bank": {},
                "form16": {},
                "payslip_vs_offer": {},
                "bank_vs_payslip": {},
                "payslip_vs_form16": {},
                "cross_errors": [f"Cross validation failed: {str(e)}"]
            }

    # -----------------------------
    # Node 3: AA Verification Agent
    # -----------------------------
    def _run_aa_verification(self) -> Dict[str, Any]:
        try:
            print("🔐 NODE 3: AA VERIFICATION AGENT (Sequential)")
            print("   - Reading AA_data.json")
            print("   - Comparing with extracted documents")
            print("   - Validating: Name, Account Number, Salary, Bonus, Tax\n")
            
            # Check if AA data file exists in Documents folder
            aa_data_path = os.path.join(self.documents_folder, "AA_data.json")
            
            if not os.path.exists(aa_data_path):
                print("⚠️ AA_data.json not found in Documents folder, skipping AA verification...")
                self._update_progress("aa_agent")
                return {
                    "aa_verification": {"status": "skipped", "reason": "AA data file not found in Documents folder"},
                    "aa_errors": []
                }
            
            # Save extracted documents to a temporary file for AA verification
            extracted_docs_path = os.path.join(self.documents_folder, "extracted_documents.json")
            extracted_docs = {
                "payslip": self.state.payslip,
                "offer": self.state.offer,
                "bank": self.state.bank,
                "form16": self.state.form16
            }
            
            with open(extracted_docs_path, "w") as f:
                json.dump(extracted_docs, f, indent=2)
            
            # First, run direct verification to get structured checks
            print("🔍 Running AA data verification checks...")
            inputs = f"{aa_data_path}|{extracted_docs_path}"
            verification_checks_json = verify_aa_data(inputs)
            
            # Parse the verification checks
            try:
                aa_checks = json.loads(verification_checks_json)
            except json.JSONDecodeError:
                aa_checks = {"raw_result": verification_checks_json}
            
            print(f"✅ Verification checks completed: {aa_checks.get('AA Verification Status', 'Unknown')}\n")
            
            # Create AA agent with LLM for comprehensive analysis
            '''print("🤖 Initializing AA Agent with LLM...")
            aa_agent = create_aa_agent()
            
            # Run the agent with a comprehensive query
            query = f"""Based on the AA data in {aa_data_path} and extracted documents in {extracted_docs_path}, perform the following:

1. Verify the consistency between AA data and extracted documents (name, account number, salary, bonus, tax, currency)
2. Perform risk-based pricing analysis considering all financial factors
3. Calculate loan eligibility with appropriate interest rates based on the user's financial profile
4. Provide recommendations for what loans and at what interest rates should be offered

Give detailed output with currency mentioned. Use the available tools to perform verification and calculations."""
            
            print("🔍 Running AA Agent analysis...")
            try:
                response = aa_agent.run(query)
            except Exception as e:
                print(f"⚠️ Agent execution failed, falling back to direct tool call: {e}")
                response = verification_checks_json'''
            
            # Parse the result with both structured checks and agent response
            aa_verification = {
                "aa_checks": aa_checks,
                "status": "completed"
            }
            
            print(f"\n✅ AA Verification completed\n")
            
            self._update_progress("aa_agent")
            return {
                "aa_verification": aa_verification,
                "aa_errors": []
            }
            
        except Exception as e:
            import traceback
            print(f"❌ AA verification error: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            self._update_progress("aa_agent")
            return {
                "aa_verification": {},
                "aa_errors": [f"AA verification failed: {str(e)}"]
            }

    def _run_decision_agent(self) -> Dict[str, Any]:
        try:
            print("🎯 NODE 4: DECISION AGENT (Sequential)")
            print("   - Analyzing all verification results")
            print("   - Calculating overall risk level")
            print("   - Making final loan decision: APPROVED/REJECTED/NEEDS_REVIEW")
            print("   - Generating detailed reasoning\n")
            
            # Check if AA data file exists in Documents folder
            aa_data_path = os.path.join(self.documents_folder, "AA_data.json")
            
            if not os.path.exists(aa_data_path):
                print("⚠️ AA_data.json not found in Documents folder, skipping Decision Agent...")
                self._update_progress("decision_agent")
                return {
                    "decision_agent": {"status": "skipped", "reason": "AA data file not found in Documents folder"},
                    "decision_errors": []
                }
     
            # Load AA_data.json to get loan_amount_requested
            try:
                with open(aa_data_path, 'r') as f:
                    aa_data_json = json.load(f)
                loan_amount_requested = aa_data_json.get("loan_amount_requested", 100000)
                print(f"💰 Loan Amount Requested: INR {loan_amount_requested:,.2f}")
            except Exception as e:
                print(f"⚠️ Error reading AA_data.json: {e}. Using default loan amount 100000")
                loan_amount_requested = 100000
     
            # Initialize Decision Agent with LLM
            print("🤖 Initializing Decision Agent with LLM...")
            decision_agent = self.decision_agent_instance
            
            # Run deterministic financial tools locally before asking Gemini to synthesize the decision.
            payslip_data = self.state.payslip or {}
            financial_data = extract_financial_data(aa_data_path)
            loan_plan = calculate_loan_plans(
                f"Calculate loan for {loan_amount_requested} using {aa_data_path}"
            )
            salary = financial_data.get("salary", 0)
            emi = financial_data.get("emi", 0)
            
            # Create comprehensive query for final decision
            query = f"""You are a financial decision agent for loan approval. Analyze the verification data and provide a comprehensive loan decision.

VERIFICATION RESULTS:
1. Manipulation Results: {json.dumps(self.state.manipulation_results, indent=2)}
2. Cross-Validation Results:
   - Payslip vs Offer: {json.dumps(self.state.payslip_vs_offer, indent=2)}
   - Bank vs Payslip: {json.dumps(self.state.bank_vs_payslip, indent=2)}
   - Payslip vs Form16: {json.dumps(self.state.payslip_vs_form16, indent=2)}
3. AA Verification: {json.dumps(self.state.aa_verification, indent=2)}

FINANCIAL DATA:
- Payslip Data: {json.dumps(payslip_data, indent=2)}
- Account Aggregator Financial Data: {json.dumps(financial_data, indent=2)}
- Monthly Salary: INR {salary}
- Existing EMI: INR {emi}
- Precalculated Loan Plan: {json.dumps(loan_plan, indent=2)}

TASK:
1. Calculate DTI ratio: (Monthly EMI / Monthly Income) * 100. Risk levels: <20% Low, 20-35% Medium, >35% High
2. Use the exact loan_plan_table from the precalculated loan plan in section 6 of your response
3. Assess overall risk based on document tampering, DTI ratio, cross-validation mismatches, and AA verification failures

CRITICAL: Return ONLY a raw JSON object. Do NOT wrap it in markdown code blocks. Do NOT use ```json or ```. Just return the plain JSON object starting with {{ and ending with }}.

RETURN JSON FORMAT:
{{
  "suggested_status": "APPROVED or REJECTED or NEEDS_REVIEW",
  "risk": "Low or Medium or High",
  "response": "Provide clean text summary with these sections (use simple text, no **, no *, no checkmarks, no emojis):
1. Document Verification: List each document with ensemble scores. Example: Account Statement shows low risk with scores 0.40-0.49. Form16 shows low risk with scores 0.51-0.54.
2. Cross-Validation Results: State matches and mismatches clearly. Example: Payslip matches Offer Letter for name and salary. Bank Statement matches Payslip. Form16 shows tax mismatch with payslip.
3. AA Verification: List verification results. Example: Name verified, Account verified, Salary verified, Bonus mismatch, Tax mismatch.
4. Financial Analysis: State income, DTI ratio, EMI, risk level. Example: Monthly income INR 85000. Existing EMI INR 12000. DTI ratio 14.12 percent (Low Risk).
5. Loan Eligibility: State maximum eligible amount. Example: Maximum eligible loan amount INR 850000 based on income.
6. Loan Plans for INR {loan_amount_requested}: Copy the exact table from calculate_loan_plans tool output. Keep the table formatting with lines and columns intact.
7. Risk Assessment: Summarize overall risk. Example: Medium risk due to document tampering score 0.57 in Offer Breakup and tax inconsistencies. DTI ratio is healthy at 14 percent.
8. Final Decision: State decision with reasoning. Example: NEEDS_REVIEW recommended. Verify Offer Breakup document and clarify tax discrepancies before approving loan of INR {loan_amount_requested} at 9.5 percent interest for 24 months.
Use plain text only. No bold, no italics, no markdown. Write in simple sentences. Always mention INR for amounts."
}}

Use the supplied deterministic financial calculations; do not invent replacement figures."""

            print("🔍 Running Decision Agent analysis...\n")
            try:
                response = decision_agent(query)
                response_text = extract_agent_response(response)
                
                # Try to parse JSON response
                try:
                    # Clean response text - remove markdown code blocks if present
                    cleaned_response = response_text.strip()
                    
                    # Remove markdown code blocks (```json ... ``` or ``` ... ```)
                    if cleaned_response.startswith('```'):
                        # Split by ``` and get the middle part
                        parts = cleaned_response.split('```')
                        if len(parts) >= 3:
                            cleaned_response = parts[1]
                        elif len(parts) == 2:
                            cleaned_response = parts[1]
                        
                        # Remove 'json' prefix if present
                        if cleaned_response.strip().startswith('json'):
                            cleaned_response = cleaned_response.strip()[4:]
                        
                        cleaned_response = cleaned_response.strip()
                    
                    # Try to find JSON object in the response
                    if not cleaned_response.startswith('{'):
                        # Look for { ... } pattern
                        json_match = re.search(r'\{[^}]*"suggested_status"[^}]*\}', cleaned_response, re.DOTALL)
                        if json_match:
                            cleaned_response = json_match.group(0)
                    
                    decision_json = json.loads(cleaned_response)
                    
                    decision_result = {
                        "suggested_status": decision_json.get("suggested_status", "NEEDS_REVIEW"),
                        "risk": decision_json.get("risk", "Medium"),
                        "response": decision_json.get("response", response_text),
                        "raw_response": response_text,
                        "processing_status": "completed"
                    }
                    
                    print(f"\n✅ Decision Agent completed")
                    print(f"📊 Suggested Status: {decision_result['suggested_status']}")
                    print(f"⚠️ Risk Level: {decision_result['risk']}")
                    print(f"📝 Response:\n{decision_result['response']}\n")
                    
                except json.JSONDecodeError as je:
                    print(f"⚠️ Failed to parse JSON response, using raw text")
                    print(f"Parse error: {str(je)}")
                    print(f"Attempted to parse: {cleaned_response[:200]}...")
                    
                    decision_result = {
                        "suggested_status": "NEEDS_REVIEW",
                        "risk": "Medium",
                        "response": response_text,
                        "raw_response": response_text,
                        "processing_status": "completed",
                        "parse_error": str(je)
                    }
                    print(f"\n✅ Decision Agent completed (raw format)\n")
                    print(f"📊 Response:\n{response_text[:500]}...\n")
                
            except Exception as e:
                print(f"⚠️ Decision Agent execution failed: {e}")
                decision_result = {
                    "suggested_status": "NEEDS_REVIEW",
                    "risk": "Medium",
                    "response": f"Error: {str(e)}",
                    "status": "failed"
                }
            
            self._update_progress("decision_agent")
            return {
                "decision_agent": decision_result,
                "decision_errors": []
            }
            
        except Exception as e:
            import traceback
            print(f"❌ Decision Agent error: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            self._update_progress("decision_agent")
            return {
                "decision_agent": {"status": "error", "error": str(e)},
                "decision_errors": [f"Decision Agent failed: {str(e)}"]
            }


    # -----------------------------
    # Node 4: Finalizer
    # -----------------------------
    def _finalize_workflow(self) -> Dict[str, Any]:
        print("🧩 NODE 5: FINALIZER (Sequential)")
        print("   - Combining all results")
        print("   - Setting workflow_status")
        print("   - Saving to final_results.json\n")

        all_errors = (
            self.state.doc_errors +
            self.state.cross_errors +
            self.state.aa_errors +
            self.state.decision_errors
        )

        if all_errors:
            status = "failed"
        elif (
            not self.state.manipulation_results
            or not self.state.payslip
        ):
            status = "partial_success"
        else:
            status = "success"

        self._update_progress("finalizer")
        return {
            "workflow_status": status,
            "errors": all_errors
        }

    # -----------------------------
    # Sequential Workflow Execution
    # -----------------------------
    def _execute_workflow(self):
        """
        Execute workflow steps sequentially and update self.state
        """
        print("┌─────────────────────────────────────────────────────────────────┐")
        print("│                         START                                    │")
        print("│                  (Initial State Created)                         │")
        print(f"│  documents_folder: {self.documents_folder}                      │")
        print("└─────────────────────────────────────────────────────────────────┘\n")

        # Step 1 & 2: Run doc analysis and cross validation IN PARALLEL
        print("🚀 Running Document Analyzer and Cross Validator in PARALLEL...\n")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks to run in parallel
            doc_future = executor.submit(self._run_doc_analysis)
            cross_future = executor.submit(self._run_cross_validation)
            
            # Wait for both to complete and get results
            doc_results = doc_future.result()
            cross_results = cross_future.result()
        
        print("\n✅ Parallel execution completed!\n")
        
        # Update state
        self.state.manipulation_results = doc_results.get("manipulation_results", {})
        self.state.doc_errors = doc_results.get("doc_errors", [])
        
        self.state.payslip = cross_results.get("payslip", {})
        self.state.offer = cross_results.get("offer", {})
        self.state.bank = cross_results.get("bank", {})
        self.state.form16 = cross_results.get("form16", {})
        self.state.payslip_vs_offer = cross_results.get("payslip_vs_offer", {})
        self.state.bank_vs_payslip = cross_results.get("bank_vs_payslip", {})
        self.state.payslip_vs_form16 = cross_results.get("payslip_vs_form16", {})
        self.state.cross_errors = cross_results.get("cross_errors", [])
        
        # Step 3: Run AA verification
        aa_results = self._run_aa_verification()
        self.state.aa_verification = aa_results.get("aa_verification", {})
        self.state.aa_errors = aa_results.get("aa_errors", [])
        
        # Step 4: Run decision agent
        decision_results = self._run_decision_agent()
        self.state.decision_result = decision_results.get("decision_agent", {})
        self.state.decision_errors = decision_results.get("decision_errors", [])
        
        # Step 5: Finalize
        final_results = self._finalize_workflow()
        self.state.workflow_status = final_results.get("workflow_status", "completed")
        self.state.errors = final_results.get("errors", [])
        
        return self.state

    # -----------------------------
    # Public Runner
    # -----------------------------
    def run_workflow(self) -> Dict[str, Any]:
        """
        Execute the verification workflow with parallel processing.
        Returns final results with all verification data.
        """
        try:
            # Execute workflow steps sequentially
            final_state = self._execute_workflow()

            os.makedirs(self.documents_folder, exist_ok=True)
            ui_results = {
                "status": final_state.workflow_status,
                "errors": final_state.errors,
                "results": {
                    "Profile": {
                        "payslip": final_state.payslip,
                        "offer": final_state.offer,
                        "bank": final_state.bank,
                        "form16": final_state.form16,
                    },
                    "document_analyzer_agent_results": final_state.manipulation_results,
                    "cross_validation_agent_results": {
                        "payslip_vs_offer": final_state.payslip_vs_offer,
                        "bank_vs_payslip": final_state.bank_vs_payslip,
                        "payslip_vs_form16": final_state.payslip_vs_form16
                    },
                    "account_aggrigator_agent_results": final_state.aa_verification,
                    "descision_making_agent": final_state.decision_result
                }
            }
            
            # Save complete final state
            with open(os.path.join(self.documents_folder, "final_results.json"), "w") as f:
                json.dump(ui_results, f, indent=2)

            # Save extracted documents data separately
            extracted_docs = {
                "payslip": final_state.payslip,
                "offer": final_state.offer,
                "bank": final_state.bank,
                "form16": final_state.form16
            }
           
            return {
                "status": final_state.workflow_status,
                "results": {
                    "Profile": {
                        "payslip": final_state.payslip,
                        "offer": final_state.offer,
                        "bank": final_state.bank,
                        "form16": final_state.form16,
                    },
                    "document_analyzer_agent_results": final_state.manipulation_results,
                    "cross_validation_agent_results": {
                        "payslip_vs_offer": final_state.payslip_vs_offer,
                        "bank_vs_payslip": final_state.bank_vs_payslip,
                        "payslip_vs_form16": final_state.payslip_vs_form16
                    },
                    "account_aggrigator_agent_results": final_state.aa_verification,
                    "descision_making_agent": final_state.decision_result
                },
                "extracted_documents": extracted_docs,
                "errors": final_state.errors
            }
        except Exception as e:
            import traceback
            print(f"❌ Workflow error: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"Workflow failed: {str(e)}",
                "errors": [str(e)]
            }


# -----------------------------
# Example Run
# -----------------------------
if __name__ == "__main__":
    # Option 1: Loan ID extracted from documents_folder path
    # If documents_folder = "Documents/LID12345678", loan_id will be "LID12345678"
    orchestrator = VerificationOrchestrator("Documents/LID12345678")
    
    # Option 2: Explicitly pass loan_id
    # orchestrator = VerificationOrchestrator("Documents", loan_id="LID12345678")
    
    results = orchestrator.run_workflow()