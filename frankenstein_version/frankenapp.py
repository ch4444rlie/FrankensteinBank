import streamlit as st
import os
import pandas as pd
from datetime import datetime, timedelta
import random  # Added to fix the undefined error

# Import from frankengen
from frankengen import generate_bank_statement, identify_template_fields, generate_populated_html_and_pdf, BANK_CONFIG

# Set page configuration
st.set_page_config(page_title="FrankenBank Statement Generator", layout="wide")

# Title and description
st.title("FrankenBank Statement Generator")
st.write("Generate a synthetic bank statement by combining sections from different banks.")

# Sidebar for user inputs
st.sidebar.header("Statement Settings")
account_holder = st.sidebar.text_input("Account Holder Name", value="John Doe")
account_type = st.sidebar.selectbox("Account Type", ["personal", "business"])
num_transactions = st.sidebar.slider("Number of Transactions", min_value=3, max_value=25, value=10)

# Section selection
st.sidebar.header("Select Bank Sections")
banks = list(BANK_CONFIG.keys())
component_map = {
    "bank_front_page": st.sidebar.selectbox("Bank Front Page (Header + Important Info)", banks, index=0),
    "account_summary": st.sidebar.selectbox("Account Summary", banks, index=0),
    "bank_balance": st.sidebar.selectbox("Bank Balance (Deposits, Withdrawals, Daily Balances)", banks, index=0),
    "disclosures": st.sidebar.selectbox("Disclosures", banks, index=0)
}

# Generate statement button
if st.sidebar.button("Generate Statement"):
    try:
        # Generate synthetic data
        df = generate_bank_statement(num_transactions, account_holder, account_type)

        # Prepare template data with number generation
        initial_balance = round(random.uniform(1000, 20000), 2)  # Random initial balance
        deposits_total = sum(x for x in df['Amount'] if x > 0)
        withdrawals_total = abs(sum(x for x in df['Amount'] if x < 0))
        ending_balance = initial_balance + deposits_total - withdrawals_total
        service_fee = 25 if ending_balance < 5000 else 0
        if service_fee:
            withdrawals_total += service_fee
            ending_balance -= service_fee

        min_date = datetime.strptime(min(df['Date']), "%m/%d").replace(year=2025)
        max_date = datetime.strptime(max(df['Date']), "%m/%d").replace(year=2025)
        statement_date = datetime.now().strftime("%B %d, %Y at %I:%M %p %Z")  # e.g., "July 02, 2025 at 02:04 PM CDT"
        address = fake.address().replace('\n', '<br>')[:100]
        account_holder = account_holder[:50]
        account_number = fake.bban()[:15]

        # Generate important info based on selected bank_front_page
        info_bank = component_map["bank_front_page"]
        important_info = generate_important_info(info_bank, account_type)

        # Prepare transactions for Citibank style if selected
        transactions = []
        if component_map["bank_balance"] == "citibank":
            total_debit = abs(sum(x for x in df['Amount'] if x < 0))
            total_credit = sum(x for x in df['Amount'] if x > 0)
            running_balance = initial_balance
            for _, row in df.iterrows():
                amount = row['Amount']
                debit = f"£{abs(amount):,.2f}" if amount < 0 else ""
                credit = f"£{amount:,.2f}" if amount > 0 else ""
                running_balance += amount
                transactions.append({
                    "date": row["Date"],
                    "description": row["Description"],
                    "debit": debit,
                    "credit": credit,
                    "balance": f"£{running_balance:,.2f}",
                    "type": row["Type"]
                })
        else:
            transactions = []
            deposits = []
            withdrawals = []
            running_balance = initial_balance
            for _, row in df.sort_values("Date").iterrows():
                amount = row['Amount']
                transaction_type = row['Type']
                deposits_credits = f"${amount:,.2f}" if amount > 0 else ""
                withdrawals_debits = f"${abs(amount):,.2f}" if amount < 0 else ""
                running_balance += amount
                transactions.append({
                    "date": row["Date"],
                    "description": row["Description"],
                    "deposits_credits": deposits_credits,
                    "withdrawals_debits": withdrawals_debits,
                    "ending_balance": f"${running_balance:,.2f}",
                    "type": transaction_type
                })
                if amount > 0:
                    deposits.append({
                        "date": row["Date"],
                        "description": row["Description"],
                        "amount": f"${amount:,.2f}",
                        "type": transaction_type
                    })
                else:
                    withdrawals.append({
                        "date": row["Date"],
                        "description": row["Description"],
                        "amount": f"${abs(amount):,.2f}",
                        "type": transaction_type
                    })
            if service_fee:
                withdrawals.append({
                    "date": max_date.strftime("%m/%d"),
                    "description": "Monthly Service Fee",
                    "amount": f"${service_fee:,.2f}",
                    "type": "other"
                })
                running_balance -= service_fee

        # Prepare daily balances for Chase/Wells Fargo if selected
        daily_balances = [
            {"date": row["Date"], "amount": f"${row['Balance']:,.2f}"}
            for _, row in df.drop_duplicates(subset="Date").iterrows()
        ]
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

        # Prepare summary with random number generation
        summary = {
            "beginning_balance": f"${initial_balance:,.2f}",
            "deposits_total": f"${deposits_total:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{deposits_total:,.2f}",
            "withdrawals_total": f"${withdrawals_total + (service_fee if service_fee else 0):,.2f}" if component_map["bank_balance"] != "citibank" else f"£{withdrawals_total + (service_fee if service_fee else 0):,.2f}",
            "ending_balance": f"${ending_balance:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{ending_balance:,.2f}",
            "deposits_count": len(deposits),
            "withdrawals_count": len(withdrawals),
            "transactions_count": len(df) + (1 if service_fee else 0),
            "average_balance": f"${round((initial_balance + ending_balance) / 2, 2):,.2f}" if component_map["bank_balance"] != "citibank" else f"£{round((initial_balance + ending_balance) / 2, 2):,.2f}",
            "fees": f"${service_fee:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{service_fee:,.2f}",
            "checks_written": sum(1 for w in withdrawals if w["type"] == "check"),
            "pos_transactions": random.randint(0, 10),
            "pos_pin_transactions": random.randint(0, 5),
            "total_atm_transactions": random.randint(0, 8),
            "pnc_atm_transactions": random.randint(0, 5) if component_map["bank_balance"] == "pnc" else 0,
            "other_atm_transactions": random.randint(0, 3),
            "apy_earned": f"{random.uniform(0.01, 0.5):.2f}%" if component_map["bank_balance"] in ["pnc", "wellsfargo"] else "0.00%",
            "days_in_period": (max_date - min_date).days + 1,
            "average_collected_balance": f"${round(random.uniform(initial_balance, ending_balance), 2):,.2f}" if component_map["bank_balance"] != "citibank" else f"£{round(random.uniform(initial_balance, ending_balance), 2):,.2f}",
            "interest_paid_period": f"${random.uniform(0.1, 10):,.2f}" if component_map["bank_balance"] in ["pnc", "wellsfargo"] else "$0.00",
            "interest_paid_ytd": f"${random.uniform(1, 50):,.2f}" if component_map["bank_balance"] in ["pnc", "wellsfargo"] else "$0.00",
            "overdraft_protection1": f"{component_map['account_summary'].capitalize()} Savings Account XXXX1234" if random.choice([True, False]) else "",
            "overdraft_protection2": f"{component_map['account_summary'].capitalize()} Credit Line XXXX5678" if random.choice([True, False]) else "",
            "overdraft_status": "Opted-In" if random.choice([True, False]) else "Opted-Out"
        }

        # Prepare template data
        template_data = {
            "account_holder": account_holder,
            "account_holder_address": address,
            "account_number": account_number,
            "statement_period": f"{min_date.strftime('%B %d')} through {max_date.strftime('%B %d')}",
            "statement_date": statement_date,
            "logo_path": os.path.join("sample_logos", BANK_CONFIG[component_map["bank_front_page"]]["logo"]) if os.path.exists(os.path.join("sample_logos", BANK_CONFIG[component_map["bank_front_page"]]["logo"])) else "",
            "important_info": important_info,
            "summary": summary,
            "deposits": deposits,
            "withdrawals": withdrawals,
            "daily_balances": daily_balances,
            "transactions": transactions,
            "opening_balance": f"${initial_balance:,.2f}" if component_map["bank_balance"] != "citibank" else f"£{initial_balance:,.2f}",
            "total_debit": f"£{abs(sum(x for x in df['Amount'] if x < 0)):.2f}" if component_map["bank_balance"] == "citibank" else "",
            "total_credit": f"£{sum(x for x in df['Amount'] if x > 0):,.2f}" if component_map["bank_balance"] == "citibank" else "",
            "total": f"£{ending_balance:,.2f}" if component_map["bank_balance"] == "citibank" else "",
            "account_type": "Total Checking" if account_type == "personal" and component_map["bank_front_page"] == "chase" else
                           "Business Complete Checking" if account_type == "business" and component_map["bank_front_page"] == "chase" else
                           "Access Checking" if account_type == "personal" and component_map["bank_front_page"] == "citibank" else
                           "Business Checking" if account_type == "business" and component_map["bank_front_page"] == "citibank" else
                           "Standard Checking" if account_type == "personal" and component_map["bank_front_page"] == "pnc" else
                           "Business Checking" if account_type == "business" and component_map["bank_front_page"] == "pnc" else
                           "Everyday Checking" if account_type == "personal" and component_map["bank_front_page"] == "wellsfargo" else
                           "Business Checking",
            "show_fee_waiver": service_fee == 0,
            "statement_start": statement_start,
            "statement_end": statement_end,
            "day_delta": day_delta,
            "balance_map": balance_map,
            "client_number": fake.uuid4()[:8] if component_map["bank_front_page"] == "citibank" else "",
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%m/%d/%Y") if component_map["bank_front_page"] == "citibank" else "",
            "customer_account_number": account_number if component_map["bank_front_page"] == "citibank" else "",
            "customer_iban": f"GB{fake.random_number(digits=2)}CITI{fake.random_number(digits=14)}" if component_map["bank_front_page"] == "citibank" else "",
            "customer_bank_name": "Citibank" if component_map["bank_front_page"] == "citibank" else ""
        }

        # Set template paths
        template_data.update({
            "bank_front_page_template": os.path.join("templates", BANK_CONFIG[component_map["bank_front_page"]]["components"]["bank_front_page"]),
            "account_summary_template": os.path.join("templates", BANK_CONFIG[component_map["account_summary"]]["components"]["account_summary"]),
            "bank_balance_template": os.path.join("templates", BANK_CONFIG[component_map["bank_balance"]]["components"]["bank_balance"]),
            "disclosures_template": os.path.join("templates", BANK_CONFIG[component_map["disclosures"]]["components"]["disclosures"]),
            "component_map": component_map
        })

        # Generate HTML and PDF
        output_files = generate_populated_html_and_pdf(
            df=df,
            account_holder=account_holder,
            component_map=component_map,
            template_dir="templates",
            output_dir="synthetic_statements",
            account_type=account_type
        )

        # Display results
        st.success("Statement generated successfully!")
        html_file, pdf_file = output_files[0]
        with open(html_file, "r", encoding="utf-8") as f:
            st.components.v1.html(f.read(), height=800, scrolling=True)
        with open(pdf_file, "rb") as f:
            st.download_button(
                label="Download PDF",
                data=f,
                file_name=os.path.basename(pdf_file),
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Error generating statement: {str(e)}")

# Add a footer with current date and time
st.sidebar.text(f"Generated on: {datetime.now().strftime('%I:%M %p CDT, %B %d, %Y')}")  # e.g., "02:04 PM CDT, July 02, 2025"