import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# Configuration
OWNER_TOKEN = "abcd"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="Loan Portfolio", layout="centered")
st.title("Loan Portfolio Sharing")

# Determine if owner
query_params = st.query_params
owner_token = query_params.get("owner")
if isinstance(owner_token, list):
    owner_token = owner_token[0] if owner_token else ""
elif not isinstance(owner_token, str):
    owner_token = ""
is_owner = owner_token == OWNER_TOKEN

# Owner Upload Panel
if is_owner:
    st.header("Owner Panel: Upload Loan Files")
    loan_file = st.file_uploader("Upload Loan Portfolio File", type=["xlsx", "xls"])
    arc_file = st.file_uploader("Upload ARC Finance File", type=["xlsx", "xls"])
    lms_file = st.file_uploader("Upload LMS053 Voucher MIS File", type=["xlsx", "xls"])

    if loan_file and arc_file and lms_file and st.button("Process Files"):
        try:
            loan_df = pd.read_excel(loan_file)
            loan_df = loan_df[loan_df['accounting_writeoff'].fillna('').str.lower() != 'yes']
            loan_df = loan_df[loan_df['loan_status'].fillna('').str.lower() == 'active']

            keep_cols = [
                "loan_account_number", "customer_name", "cibil", "product_code", "product_name",
                "interest_rate", "original_tenure", "ltv", "login_date", "sourcing_channel",
                "dsa_name", "dealer_code", "dealer_name", "collateral_type", "model",
                "model_year", "registration_number", "chasis_no", "engine_no", "sanction_date",
                "sanctioned_amount", "interest_start_date", "repayment_start_date", "maturity_date",
                "installment_amount", "disbursal_date", "disbursal_amount", "pending_amount",
                "disbursal_status", "principal_outstanding", "total_excess_money", "dpd", "dpd_wise",
                "asset_classification", "credit_manager_id", "credit_manager_name", "sourcing_rm_id",
                "sourcing_rm_name", "branch_id", "branch_code", "branch_name", "state", "repayment_mode",
                "nach_status", "loan_status"
            ]
            loan_df = loan_df[[c for c in keep_cols if c in loan_df.columns]]

            arc_df = pd.read_excel(arc_file)
            arc_df.columns = arc_df.columns.str.strip()
            arc_loan_col = next((c for c in arc_df.columns if 'loan_account_number' in c.lower()), None)
            if not arc_loan_col:
                st.error("ARC Finance file must contain a 'loan_account_number' column.")
                st.stop()
            loan_df['ARC Lookup'] = loan_df['loan_account_number'].apply(
                lambda v: v if v in arc_df[arc_loan_col].values else None
            )
            loan_df = loan_df[loan_df['ARC Lookup'].isna()].drop(columns=['ARC Lookup'])

            lms_df = pd.read_excel(lms_file)
            lms_df.columns = lms_df.columns.str.strip()
            if 'Gl Desc' not in lms_df.columns:
                st.error("LMS053 file must contain a 'Gl Desc' column.")
                st.stop()
            lms_df = lms_df[lms_df['Gl Desc'].str.upper() == 'ACCRUAL INCOME']
            if not all(c in lms_df.columns for c in ['Loan Account Number', 'Debit Amount']):
                st.error("LMS053 must contain 'Loan Account Number' and 'Debit Amount'.")
                st.stop()
            accrual = (
                lms_df.groupby('Loan Account Number')['Debit Amount']
                .sum().reset_index()
                .rename(columns={'Loan Account Number': 'loan_account_number', 'Debit Amount': 'Accrul_Amount'})
            )
            loan_df = loan_df.merge(accrual, on='loan_account_number', how='left')
            loan_df['Accrul_Amount'] = loan_df['Accrul_Amount'].fillna(0)

            cols = loan_df.columns.tolist()
            try:
                AB, AD, AE, AT = cols[27], cols[29], cols[30], cols[45]
            except IndexError:
                st.error("Not enough columns to calculate AUM.")
                st.stop()
            loan_df['AUM'] = loan_df.apply(
                lambda r: max(r[AD] - (r[AB] + r[AE]), 0) + r[AT], axis=1
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_Loan_Portfolio.xlsx"
            save_path = os.path.join(UPLOAD_DIR, filename)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                loan_df.to_excel(writer, index=False, sheet_name="Loan Portfolio")
            with open(save_path, 'wb') as f:
                f.write(output.getvalue())
            st.success(f"File processed and saved as {filename}")
        except Exception as e:
            st.error(f"Error during processing: {e}")

# Download section for all users
st.header("Download Latest File")
files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)]
if files:
    latest_file = max(files, key=os.path.getmtime)
    with open(latest_file, "rb") as f:
        st.download_button(
            label="Download file",
            data=f,
            file_name=os.path.basename(latest_file),
            mime="application/octet-stream"
        )
else:
    st.info("No file has been uploaded yet.")

if not is_owner:
    st.info("All Users access this link")



#http://localhost:8501/?owner=abcd    
