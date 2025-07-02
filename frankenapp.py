import streamlit as st
import pandas as pd
import os
import base64
from frankengen import (
    generate_bank_statement,
    identify_template_fields,
    generate_populated_html_and_pdf,
    BANK_CONFIG
)
from faker import Faker
from streamlit_pdf_viewer import pdf_viewer  # Add this import for streamlit-pdf-viewer

fake = Faker()
# Directory setup
SAMPLE_LOGOS_DIR = "franken_logos"
SYNTHETIC_STAT_DIR = "output_statements"
TEMPLATES_DIR = "f_templates"

# Create directories if they don’t exist
for directory in [SAMPLE_LOGOS_DIR, SYNTHETIC_STAT_DIR, TEMPLATES_DIR]:
    os.makedirs(directory, exist_ok=True)

# Streamlit page configuration
st.set_page_config(page_title="Synthetic Bank Statement Generator", page_icon="🏦", layout="wide")

# Custom CSS for buttons
st.markdown("""
<style>
.stButton > button {
    width: 100%;
    height: 40px;
    font-size: 16px;
}
</style>
""", unsafe_allow_html=True)

# Bank and template display names
BANK_DISPLAY_NAMES = {
    "chase": "Chase",
    "citibank": "Citibank",
    "wellsfargo": "Wells Fargo",
    "pnc": "PNC"
}

# Sidebar for user inputs
with st.sidebar:
    st.header("Statement Options")
    st.markdown("Configure your synthetic bank statement.")
    
    # Bank selection for each section
    st.subheader("Select Bank Sections")
    banks = list(BANK_CONFIG.keys())
    if "component_map" not in st.session_state:
        st.session_state["component_map"] = {k: banks[0] for k in ["bank_front_page", "account_summary", "bank_balance", "disclosures"]}
    
    cols = st.columns(2)
    with cols[0]:
        st.session_state["component_map"]["bank_front_page"] = st.selectbox("Bank Front Page (Header + Important Info)", banks, index=0, key="front_page")
    with cols[1]:
        st.session_state["component_map"]["account_summary"] = st.selectbox("Account Summary", banks, index=0, key="summary")
    with cols[0]:
        st.session_state["component_map"]["bank_balance"] = st.selectbox("Bank Balance (Deposits, Withdrawals, Daily Balances)", banks, index=0, key="balance")
    with cols[1]:
        st.session_state["component_map"]["disclosures"] = st.selectbox("Disclosures", banks, index=0, key="disclosures")
    
    # Account type selection
    st.subheader("Select Account Type")
    if "account_type" not in st.session_state:
        st.session_state["account_type"] = "personal"
    
    cols = st.columns(2)
    with cols[0]:
        if st.button("Personal", key="account_type_personal"):
            st.session_state["account_type"] = "personal"
    with cols[1]:
        if st.button("Business", key="account_type_business"):
            st.session_state["account_type"] = "business"
    
    account_type = st.session_state["account_type"]

    # Number of transactions
    st.subheader("Number of Transactions")
    num_transactions = st.slider("Number of Transactions", min_value=3, max_value=25, value=5, step=1)

    # Add spacing before Generate button
    st.markdown("<br><br>", unsafe_allow_html=True)  # Adds two line breaks
    
    # Generate button
    if st.button("Generate Statement", key="sidebar_generate_button"):
        if not all(st.session_state["component_map"].values()):
            st.error("Please ensure all bank sections are selected.")
        else:
            st.session_state["trigger_generate"] = True

# Main interface
st.title("Frankenstein of Synthetic Bank Statements")
st.markdown("""  
- Create your synthetic bank statement by mixing and matching sections from different banks using the sidebar options.  
- Select **Personal** or **Business** account type to customize transaction categories.  
- Download the generated PDF!
""")

# Initialize session state
if "generated" not in st.session_state:
    st.session_state["generated"] = False
if "trigger_generate" not in st.session_state:
    st.session_state["trigger_generate"] = False
if "pdf_content" not in st.session_state:
    st.session_state["pdf_content"] = None
if "pdf_filename" not in st.session_state:
    st.session_state["pdf_filename"] = None

# Handle generation
if st.session_state["trigger_generate"]:
    if not all(st.session_state["component_map"].values()):
        st.error("Please ensure all bank sections are selected.")
        st.session_state["trigger_generate"] = False
    else:
        with st.spinner(f"Generating statement with sections from {', '.join(st.session_state['component_map'].values())}..."):
            try:
                # Generate account holder based on account type
                account_holder = fake.company().upper() if account_type == "business" else fake.name().upper()
                df = generate_bank_statement(num_transactions, account_holder, account_type)
                csv_filename = os.path.join(SYNTHETIC_STAT_DIR, f"bank_statement_{account_type.upper()}_{account_holder.replace(' ', '_')}.csv")
                df.to_csv(csv_filename, index=False, encoding='utf-8')
                
                # Identify fields using the full component_map
                statement_fields = identify_template_fields(st.session_state["component_map"], TEMPLATES_DIR)
                results = generate_populated_html_and_pdf(
                    df=df,
                    account_holder=account_holder,
                    component_map=st.session_state["component_map"],
                    template_dir=TEMPLATES_DIR,
                    output_dir=SYNTHETIC_STAT_DIR,
                    account_type=account_type
                )
                
                # Use the first result (single template combination)
                html_file, pdf_file = results[0]
                st.session_state["generated"] = True
                st.session_state["pdf_filename"] = os.path.basename(pdf_file)
                with open(pdf_file, "rb") as f:
                    st.session_state["pdf_content"] = f.read()
                st.session_state["trigger_generate"] = False
                
                # Display download button
                st.download_button(
                    label=f"Download {account_type.capitalize()} PDF",
                    data=st.session_state["pdf_content"],
                    file_name=st.session_state["pdf_filename"],
                    mime="application/pdf",
                    key=f"pdf_download_{account_type}"
                )
                
                # Preview section
                st.subheader(f"Preview: {account_type.capitalize()} Statement")
                preview_placeholder = st.empty()
                # Use streamlit-pdf-viewer instead of iframe
                pdf_viewer(
                    input=st.session_state["pdf_content"],  # Binary PDF content
                    width=700,  # Specify width for proper rendering
                    height=600,  # Match original iframe height
                    zoom_level=1.0,  # Default zoom (100%)
                    viewer_align="center",  # Center the PDF viewer
                    show_page_separator=True  # Show separators between pages
                )
                preview_placeholder.markdown("""
                **Note**: If the PDF doesn't display, ensure JavaScript is enabled, disable ad blockers, or try Firefox/Edge. The PDF can still be downloaded using the button above.
                """)
                
                # Details expander
                with st.expander("View Details"):
                    st.write(f"CSV saved: {csv_filename}")
                    st.write(f"PDF saved: {pdf_file}")
                    st.write("Template Fields:")
                    for field in statement_fields.fields:
                        st.write(f"- {field.name}: {'Mutable' if field.is_mutable else 'Immutable'}, {field.description}")
            
            except Exception as e:
                st.error(f"Error generating statement: {str(e)}")
                st.markdown("""
                **Troubleshooting**:
                - Ensure transactions are between 3 and 25.
                - Verify the template and logo files exist in the 'f_templates' and 'franken_logos' directories.
                - Check that wkhtmltopdf is installed.
                - If the PDF preview or download fails, try Firefox/Edge or disable Chrome’s ad blockers.
                - Refresh or contact the administrator.
                """)
                preview_placeholder = st.empty()
                preview_placeholder.markdown("No statement generated. Resolve the error and try again.")
                st.session_state["generated"] = False
                st.session_state["trigger_generate"] = False
                st.session_state["pdf_content"] = None
                st.session_state["pdf_filename"] = None

# Default preview message
if not st.session_state["generated"]:
    st.subheader(f"Preview: {account_type.capitalize()} Statement")
    preview_placeholder = st.empty()
    preview_placeholder.markdown("Select bank sections, account type, and options in the sidebar, then click 'Generate Statement' to preview your synthetic bank statement.")