import os
import re
import base64
import json
from faker import Faker
from datetime import datetime, timedelta
import random
import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import pdfkit

# Initialize Faker
fake = Faker()

# Bank configuration with flat filenames
BANK_CONFIG = {
    "chase": {
        "logo": "chase_bank_logo.png",
        "components": {
            "bank_front_page": "chase_front_page.html",
            "account_summary": "chase_summary.html",
            "bank_balance": "chase_balance.html",
            "disclosures": "chase_disclosures.html"
        }
    },
    "citibank": {
        "logo": "citibank_logo.png",
        "components": {
            "bank_front_page": "citibank_front_page.html",
            "account_summary": "citibank_summary.html",
            "bank_balance": "citibank_balance.html",
            "disclosures": "citibank_disclosures.html"
        }
    },
    "wellsfargo": {
        "logo": "wellsfargo_logo.png",
        "components": {
            "bank_front_page": "wells_front_page.html",
            "account_summary": "wells_summary.html",
            "bank_balance": "wells_balance.html",
            "disclosures": "wells_disclosures.html"
        }
    },
    "pnc": {
        "logo": "pnc_logo.png",
        "components": {
            "bank_front_page": "pnc_front_page.html",
            "account_summary": "pnc_summary.html",
            "bank_balance": "pnc_balance.html",
            "disclosures": "pnc_disclosures.html"
        }
    }
}

# Pydantic models
class FieldDefinition(BaseModel):
    name: str = Field(..., description="Field name")
    is_mutable: bool = Field(..., description="Whether the field is mutable")
    description: str = Field(..., description="Description of the field")

class StatementFields(BaseModel):
    fields: List[FieldDefinition] = Field(..., description="List of mutable and immutable fields")

class Transaction(BaseModel):
    description: str = Field(..., max_length=35, description="Transaction description")
    category: str
    amount: float
    account_type: str = Field(..., description="Type of account (personal or business)")
    type: str = Field(..., description="Transaction type (e.g., deposit, electronic, check, other)")

# Predefined transaction categories and descriptions
BUSINESS_CATEGORIES = {
    "loss": [
        ("Vendor Payment", ["Vendor Invoice Payment", "Supplier Payment", "Service Fee", "Contractor Payment"]),
        ("Payroll Expense", ["Employee Salary", "Payroll Distribution", "Staff Wages", "Bonus Payment"]),
        ("Office Supplies", ["Office Supply Purchase", "Stationery Order", "Equipment Rental", "Supply Restock"]),
        ("Equipment Purchase", ["Machinery Purchase", "Hardware Acquisition", "Tool Purchase", "Equipment Upgrade"]),
        ("Marketing Cost", ["Advertising Expense", "Marketing Campaign", "Promo Materials", "Digital Ad Spend"])
    ],
    "gain": [
        ("Client Invoice", ["Client Payment Received", "Invoice Settlement", "Customer Payment", "Service Revenue"]),
        ("Refund Received", ["Vendor Refund", "Overpayment Refund", "Return Credit", "Reimbursement"]),
        ("Investment Income", ["Dividend Payment", "Interest Income", "Investment Return", "Profit Share"]),
        ("Grant Received", ["Business Grant", "Funding Received", "Grant Disbursement", "Award Payment"]),
        ("Sales Revenue", ["Product Sales", "Service Sales", "Retail Revenue", "Online Sales"])
    ]
}

PERSONAL_CATEGORIES = {
    "loss": [
        ("Utility Payment", ["Electric Bill Payment", "Water Bill Payment", "Internet Bill", "Phone Bill"]),
        ("Subscription Fee", ["Streaming Service", "Gym Membership", "Magazine Subscription", "Software License"]),
        ("Online Purchase", ["Ecommerce Purchase", "Online Retail", "Shopping Delivery", "Web Order"]),
        ("Rent Payment", ["Monthly Rent", "Apartment Lease", "Housing Payment", "Landlord Payment"]),
        ("Grocery Shopping", ["Grocery Store Purchase", "Supermarket Bill", "Food Shopping", "Market Purchase"])
    ],
    "gain": [
        ("Salary Deposit", ["Paycheck Deposit", "Wage Deposit", "Salary Credit", "Job Payment"]),
        ("Tax Refund", ["Tax Return Credit", "Refund Deposit", "IRS Refund", "State Tax Refund"]),
        ("Gift Received", ["Gift Money", "Cash Gift", "Family Support", "Personal Gift"]),
        ("Client Payment", ["Freelance Payment", "Consulting Fee", "Service Payment", "Project Payment"]),
        ("Cash Deposit", ["Cash Deposit", "ATM Deposit", "Bank Deposit", "Personal Savings"])
    ]
}

# Generate category lists
def generate_category_lists(account_type: str) -> tuple[List[str], List[str]]:
    categories = BUSINESS_CATEGORIES if account_type == "business" else PERSONAL_CATEGORIES
    loss_categories = [cat[0] for cat in categories["loss"]]
    gain_categories = [cat[0] for cat in categories["gain"]]
    return loss_categories, gain_categories

# Generate transaction description
def generate_transaction_description(amount: float, category: str, account_type: str) -> dict:
    categories = BUSINESS_CATEGORIES if account_type == "business" else PERSONAL_CATEGORIES
    description_list = next((cat[1] for cat in (categories["loss"] + categories["gain"]) if cat[0] == category), [f"{category} Transaction"])
    description = random.choice(description_list)[:35]
    description = ' '.join(word.capitalize() for word in description.split())
    if amount > 0:
        transaction_type = "deposit"
    else:
        transaction_type = random.choice(["electronic", "check", "other"])
    transaction = Transaction(description=description, category=category, amount=amount, account_type=account_type, type=transaction_type)
    return transaction.model_dump()

# Generate synthetic bank statement
def generate_bank_statement(num_transactions: int, account_holder: str, account_type: str) -> pd.DataFrame:
    if account_type not in ["business", "personal"]:
        raise ValueError("Account type must be 'business' or 'personal'")
    if not (3 <= num_transactions <= 25):
        raise ValueError("Number of transactions must be between 3 and 25")
    
    loss_categories, gain_categories = generate_category_lists(account_type)
    start_date = datetime.now() - timedelta(days=30)
    dates = [start_date + timedelta(days=random.randint(0, 30)) for _ in range(num_transactions)]
    
    transactions = []
    min_deposits = max(1, num_transactions // 3)
    min_withdrawals = max(1, num_transactions // 3)
    deposit_count = 0
    withdrawal_count = 0
    
    for _ in range(num_transactions):
        if deposit_count < min_deposits:
            is_gain = True
        elif withdrawal_count < min_withdrawals:
            is_gain = False
        else:
            is_gain = random.choice([True, False])
        
        category = random.choice(gain_categories if is_gain else loss_categories)
        amount = round(random.uniform(50, 1000), 2) if is_gain else round(random.uniform(-500, -10), 2)
        transaction = generate_transaction_description(amount, category, account_type)
        transactions.append(transaction)
        
        if is_gain:
            deposit_count += 1
        else:
            withdrawal_count += 1
    
    data = {
        "Date": [d.strftime("%m/%d") for d in dates],
        "Description": [t["description"] for t in transactions],
        "Category": [t["category"] for t in transactions],
        "Amount": [t["amount"] for t in transactions],
        "Type": [t["type"] for t in transactions],
        "Balance": [0.0] * num_transactions,
        "Account Holder": [account_holder] * num_transactions,
        "Account Type": [account_type.capitalize()] * num_transactions,
        "Transaction ID": [(fake.bban()[:10] + str(i).zfill(4)) for i in range(num_transactions)]
    }
    df = pd.DataFrame(data)
    df = df.sort_values("Date")
    initial_balance = round(random.uniform(1000, 20000), 2)
    df["Balance"] = initial_balance + df["Amount"].cumsum()
    return df

# Identify mutable and immutable fields
def identify_template_fields(component_map: Dict[str, str], templates_dir: str = "f_templates") -> StatementFields:
    env = Environment(loader=FileSystemLoader(templates_dir))
    supported_components = ["bank_front_page", "account_summary", "bank_balance", "disclosures"]
    for component in component_map.keys():
        if component not in supported_components:
            raise ValueError(f"Unsupported component: {component}")
    placeholders = set()
    for component in supported_components:
        bank = component_map[component]
        template_name = BANK_CONFIG[bank]["components"][component]
        try:
            template = env.get_template(template_name)
            placeholders.update(re.findall(r'\{\{([^{}]+)\}\}', template.render()))
        except TemplateNotFound:
            raise FileNotFoundError(f"Template {template_name} not found in {templates_dir}")
    placeholders = [p.strip() for p in placeholders]
    
    default_fields = [
        FieldDefinition(name="account_holder", is_mutable=True, description="Name of the account holder"),
        FieldDefinition(name="account_holder_address", is_mutable=True, description="Address of the account holder"),
        FieldDefinition(name="account_number", is_mutable=True, description="Account number"),
        FieldDefinition(name="statement_period", is_mutable=True, description="Statement date range"),
        FieldDefinition(name="statement_date", is_mutable=True, description="Date the statement was created"),
        FieldDefinition(name="transactions", is_mutable=True, description="List of transaction details"),
        FieldDefinition(name="opening_balance", is_mutable=True, description="Opening balance"),
        FieldDefinition(name="total_debit", is_mutable=True, description="Total debit amount"),
        FieldDefinition(name="total_credit", is_mutable=True, description="Total credit amount"),
        FieldDefinition(name="total", is_mutable=True, description="Total balance"),
        FieldDefinition(name="logo_path", is_mutable=True, description="Path to the bank logo"),
        FieldDefinition(name="important_info", is_mutable=True, description="Important account information"),
        FieldDefinition(name="summary", is_mutable=True, description="Summary of account details"),
        FieldDefinition(name="daily_balances", is_mutable=True, description="Daily balance details"),
        FieldDefinition(name="deposits", is_mutable=True, description="Deposit transactions"),
        FieldDefinition(name="withdrawals", is_mutable=True, description="Withdrawal transactions"),
        FieldDefinition(name="balance_map", is_mutable=True, description="Mapping of dates to balances"),
        FieldDefinition(name="statement_start", is_mutable=True, description="Start date of the statement period"),
        FieldDefinition(name="statement_end", is_mutable=True, description="End date of the statement period"),
        FieldDefinition(name="day_delta", is_mutable=True, description="Delta between days for balance calculation"),
        FieldDefinition(name="client_number", is_mutable=True, description="Client number"),
        FieldDefinition(name="date_of_birth", is_mutable=True, description="Date of birth"),
        FieldDefinition(name="customer_account_number", is_mutable=True, description="Customer account number"),
        FieldDefinition(name="customer_iban", is_mutable=True, description="Customer IBAN"),
        FieldDefinition(name="customer_bank_name", is_mutable=True, description="Customer bank name"),
        FieldDefinition(name="show_fee_waiver", is_mutable=True, description="Whether the service fee was waived"),
        FieldDefinition(name="account_type", is_mutable=True, description="Type of account"),
        FieldDefinition(name="bank_name", is_mutable=False, description="Name of the bank"),
        FieldDefinition(name="bank_address", is_mutable=False, description="Bank address"),
        FieldDefinition(name="customer_service", is_mutable=False, description="Customer service contact information"),
        FieldDefinition(name="footnotes", is_mutable=False, description="Footnotes and disclosures")
    ]
    statement_fields = StatementFields(fields=[f for f in default_fields if f.name in placeholders or f.name in ["bank_name", "bank_address", "customer_service", "footnotes"]])
    
    log_path = os.path.join("output_statements", "template_fields.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(statement_fields.model_dump(), f, indent=2)
    
    return statement_fields

# Generate populated HTML and PDF
def generate_populated_html_and_pdf(df: pd.DataFrame, account_holder: str, component_map: Dict[str, str], template_dir: str = "f_templates", output_dir: str = "output_statements", account_type: str = Field(..., description="Type of account (personal or business)")) -> list:
    env = Environment(loader=FileSystemLoader(template_dir))
    try:
        template = env.get_template("base_template.html")
    except TemplateNotFound:
        raise FileNotFoundError(f"Base template 'base_template.html' not found in {template_dir}")
    
    initial_balance = round(random.uniform(1000, 20000), 2)
    deposits_total = sum(x for x in df['Amount'] if x > 0)
    withdrawals_total = abs(sum(x for x in df['Amount'] if x < 0))
    ending_balance = initial_balance + deposits_total - withdrawals_total
    service_fee = 25 if ending_balance < 5000 else 0
    if service_fee:
        withdrawals_total += service_fee
        ending_balance -= service_fee
    
    min_date = datetime.strptime(min(df['Date']), "%m/%d").replace(year=2025)
    max_date = datetime.strptime(max(df['Date']), "%m/%d").replace(year=2025)
    statement_date = datetime.now().strftime("%B %d, %Y at %I:%M %p %Z")
    
    address = fake.address().replace('\n', '<br>')[:100]
    account_holder = account_holder[:50]
    account_number = fake.bban()[:15]
    
    info_bank = component_map["bank_front_page"]
    important_info = generate_important_info(info_bank, account_type)
    
    transactions = []
    deposits = []
    withdrawals = []
    running_balance = initial_balance
    if component_map["bank_balance"] == "citibank":
        total_debit = abs(sum(x for x in df['Amount'] if x < 0))
        total_credit = sum(x for x in df['Amount'] if x > 0)
        for _, row in df.iterrows():
            amount = row['Amount']
            debit = f"£{abs(amount):,.2f}" if amount < 0 else ""
            credit = f"£{amount:,.2f}" if amount > 0 else ""
            running_balance += amount
            transactions.append({
                "date": row["Date"], "description": row["Description"], "debit": debit, "credit": credit,
                "balance": f"£{running_balance:,.2f}", "type": row["Type"]
            })
    else:
        for _, row in df.sort_values("Date").iterrows():
            amount = row['Amount']
            transaction_type = row['Type']
            deposits_credits = f"${amount:,.2f}" if amount > 0 else ""
            withdrawals_debits = f"${abs(amount):,.2f}" if amount < 0 else ""
            running_balance += amount
            transactions.append({
                "date": row["Date"], "description": row["Description"], "deposits_credits": deposits_credits,
                "withdrawals_debits": withdrawals_debits, "ending_balance": f"${running_balance:,.2f}", "type": transaction_type
            })
            if amount > 0:
                deposits.append({"date": row["Date"], "description": row["Description"], "amount": f"${amount:,.2f}", "type": transaction_type})
            else:
                withdrawals.append({"date": row["Date"], "description": row["Description"], "amount": f"${abs(amount):,.2f}", "type": transaction_type})
        if service_fee:
            withdrawals.append({"date": max_date.strftime("%m/%d"), "description": "Monthly Service Fee", "amount": f"${service_fee:,.2f}", "type": "other"})
            running_balance -= service_fee
    
    daily_balances = [{"date": row["Date"], "amount": f"${row['Balance']:,.2f}"} for _, row in df.drop_duplicates(subset="Date").iterrows()]
    balance_map = {}
    if component_map["bank_balance"] in ["chase", "wellsfargo"]:
        running_balance = initial_balance
        statement_start = min_date
        statement_end = max_date
        day_delta = timedelta(days=1)
        current_date = statement_start
        while current_date <= statement_end:
            iso_date = current_date.isoformat()
            daily_transactions = df[df["Date"] == current_date.strftime("%m/%d")]
            if not daily_transactions.empty:
                daily_amount = daily_transactions["Amount"].sum()
                running_balance += daily_amount
            balance_map[iso_date] = f"${running_balance:,.2f}"
            current_date += day_delta
    
    summary = {
        "beginning_balance": f"${initial_balance:,.2f}",
        "deposits_total": f"${deposits_total:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{deposits_total:,.2f}",
        "withdrawals_total": f"${withdrawals_total + (service_fee if service_fee else 0):,.2f}" if component_map["bank_balance"] != "citibank" else f"£{withdrawals_total + (service_fee if service_fee else 0):,.2f}",
        "ending_balance": f"${ending_balance:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{ending_balance:,.2f}",
        "deposits_count": len(deposits), "withdrawals_count": len(withdrawals), "transactions_count": len(df) + (1 if service_fee else 0),
        "average_balance": f"${round((initial_balance + ending_balance) / 2, 2):,.2f}" if component_map["bank_balance"] != "citibank" else f"£{round((initial_balance + ending_balance) / 2, 2):,.2f}",
        "fees": f"${service_fee:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{service_fee:,.2f}",
        "checks_written": sum(1 for w in withdrawals if w["type"] == "check"), "pos_transactions": random.randint(0, 10),
        "pos_pin_transactions": random.randint(0, 5), "total_atm_transactions": random.randint(0, 8),
        "pnc_atm_transactions": random.randint(0, 5) if component_map["bank_balance"] == "pnc" else 0,
        "other_atm_transactions": random.randint(0, 3), "apy_earned": f"{random.uniform(0.01, 0.5):.2f}%" if component_map["bank_balance"] in ["pnc", "wellsfargo"] else "0.00%",
        "days_in_period": (max_date - min_date).days + 1,
        "average_collected_balance": f"${round(random.uniform(initial_balance, ending_balance), 2):,.2f}" if component_map["bank_balance"] != "citibank" else f"£{round(random.uniform(initial_balance, ending_balance), 2):,.2f}",
        "interest_paid_period": f"${random.uniform(0.1, 10):,.2f}" if component_map["bank_balance"] in ["pnc", "wellsfargo"] else "$0.00",
        "interest_paid_ytd": f"${random.uniform(1, 50):,.2f}" if component_map["bank_balance"] in ["pnc", "wellsfargo"] else "$0.00",
        "overdraft_protection1": f"{component_map['account_summary'].capitalize()} Savings Account XXXX1234" if random.choice([True, False]) else "",
        "overdraft_protection2": f"{component_map['account_summary'].capitalize()} Credit Line XXXX5678" if random.choice([True, False]) else "",
        "overdraft_status": "Opted-In" if random.choice([True, False]) else "Opted-Out"
    }
        

    template_data = {
        "account_holder": account_holder, "account_holder_address": address, "account_number": account_number,
        "statement_period": f"{min_date.strftime('%B %d')} through {max_date.strftime('%B %d')}", "statement_date": statement_date,
        "logo_path": os.path.join("franken_logos", BANK_CONFIG[component_map["bank_front_page"]]["logo"]) if os.path.exists(os.path.join("franken_logos", BANK_CONFIG[component_map["bank_front_page"]]["logo"])) else "",
        "important_info": important_info, "summary": summary, "deposits": deposits, "withdrawals": withdrawals,
        "daily_balances": daily_balances, "transactions": transactions,
        "opening_balance": f"${initial_balance:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{initial_balance:,.2f}",
        "total_debit": f"£{total_debit:,.2f}" if component_map["bank_balance"] == "citibank" else "",
        "total_credit": f"£{total_credit:,.2f}" if component_map["bank_balance"] == "citibank" else "",
        "total": f"£{ending_balance:,.2f}" if component_map["bank_balance"] == "citibank" else "",
        "account_type": "Total Checking" if account_type == "personal" and component_map["bank_front_page"] == "chase" else
                       "Business Complete Checking" if account_type == "business" and component_map["bank_front_page"] == "chase" else
                       "Access Checking" if account_type == "personal" and component_map["bank_front_page"] == "citibank" else
                       "Business Checking" if account_type == "business" and component_map["bank_front_page"] == "citibank" else
                       "Standard Checking" if account_type == "personal" and component_map["bank_front_page"] == "pnc" else
                       "Business Checking" if account_type == "business" and component_map["bank_front_page"] == "pnc" else
                       "Everyday Checking" if account_type == "personal" and component_map["bank_front_page"] == "wellsfargo" else
                       "Business Checking",
        "show_fee_waiver": service_fee == 0, "statement_start": statement_start, "statement_end": statement_end,
        "day_delta": day_delta, "balance_map": balance_map,
        "client_number": fake.uuid4()[:8] if component_map["bank_front_page"] == "citibank" else "",
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%m/%d/%Y") if component_map["bank_front_page"] == "citibank" else "",
        "customer_account_number": account_number if component_map["bank_front_page"] == "citibank" else "",
        "customer_iban": f"GB{fake.random_number(digits=2)}CITI{fake.random_number(digits=14)}" if component_map["bank_front_page"] == "citibank" else "",
        "customer_bank_name": "Citibank" if component_map["bank_front_page"] == "citibank" else "",
        "bank_front_page_template": BANK_CONFIG[component_map["bank_front_page"]]["components"]["bank_front_page"],
        "account_summary_template": BANK_CONFIG[component_map["account_summary"]]["components"]["account_summary"],
        "bank_balance_template": BANK_CONFIG[component_map["bank_balance"]]["components"]["bank_balance"],
        "disclosures_template": BANK_CONFIG[component_map["disclosures"]]["components"]["disclosures"],
        "component_map": component_map
    }


    
    template_name_base = "_".join([f"{k}_{v}" for k, v in component_map.items()])
    html_filename = os.path.join(output_dir, f"bank_statement_{account_type.upper()}_{account_holder.replace(' ', '_')}_{template_name_base}.html")
    pdf_filename = os.path.join(output_dir, f"bank_statement_{account_type.upper()}_{account_holder.replace(' ', '_')}_{template_name_base}.pdf")
    
    rendered_html = template.render(**template_data)
    
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
    
    wkhtmltopdf_path = os.environ.get("WKHTMLTOPDF_PATH", "/usr/bin/wkhtmltopdf")
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    options = {
        "enable-local-file-access": "",
        "page-size": "Letter",
        "margin-top": "0.8in",
        "margin-right": "0.9in",
        "margin-bottom": "0.8in",
        "margin-left": "0.9in",
        "encoding": "UTF-8",
        "disable-javascript": "",
        "image-dpi": "300",
        "enable-forms": "",
        "no-outline": "",
        "print-media-type": "",
        "minimum-font-size": "10"
    }
    try:
        pdfkit.from_string(rendered_html, pdf_filename, configuration=config, options=options)
        return [(html_filename, pdf_filename)]
    except OSError as e:
        raise Exception(f"PDF generation failed for {component_map} template: {e}")

# Generate important info
def generate_important_info(bank: str, account_type: str) -> str:
    if account_type == "business":
        if bank == "chase":
            return f"<p>Effective July 1, 2025, the monthly service fee for Business Chase Complete Checking accounts will increase to $20 unless you maintain a minimum daily balance of $2,000...</p>"
        elif bank == "pnc":
            return f"<p>Effective July 1, 2025, the monthly service fee for Business Checking accounts will increase to $15 unless you maintain a minimum daily balance of $5,000...</p>"
        elif bank == "citibank":
            return f"<p>Effective July 1, 2025, the monthly account fee for CitiBusiness Checking accounts will increase to £15 unless you maintain a minimum daily balance of £5,000...</p>"
        elif bank == "wellsfargo":
            return f"<p>Effective July 1, 2025, the monthly service fee for Business Checking accounts will increase to $20 unless you maintain a minimum daily balance of $5,000...</p>"
    else:  # Personal
        if bank == "chase":
            return f"<p>Effective July 1, 2025, the monthly service fee for Personal Chase Total Checking accounts will increase to $15 unless you maintain a minimum daily balance of $1,500...</p>"
        elif bank == "pnc":
            return f"<p>Effective July 1, 2025, the monthly service fee for Personal Checking accounts will increase to $10 unless you maintain a minimum daily balance of $1,500...</p>"
        elif bank == "citibank":
            return f"<p>Effective July 1, 2025, the monthly account fee for Citi Access Checking accounts will increase to £10 unless you maintain a minimum daily balance of £1,500...</p>"
        elif bank == "wellsfargo":
            return f"<p>Effective July 1, 2025, the monthly service fee for Personal Checking accounts will increase to $10 unless you maintain a minimum daily balance of $1,500...</p>"
    return "<p>No specific important information available.</p>"

if __name__ == "__main__":
    df = generate_bank_statement(10, "John Doe", "personal")
    component_map = {"bank_front_page": "chase", "account_summary": "pnc", "bank_balance": "wellsfargo", "disclosures": "citibank"}
    output_files = generate_populated_html_and_pdf(df, "John Doe", component_map, "f_templates", "output_statements", "personal")
    print(f"Generated files: {output_files}")