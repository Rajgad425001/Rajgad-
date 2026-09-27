import streamlit as st
import pandas as pd
from datetime import datetime
import io
import urllib.request
import json

st.set_page_config(
    page_title="राजगड सोसायटी व्यवस्थापन प्रणाली",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #8B0000;
        text-align: center;
        padding-bottom: 5px;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #555;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

MONTHS_LIST = [
    "जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून",
    "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"
]

# --- Zero-Dependency Cloud Database Engine (Neon HTTP SQL) ---
def get_db_url():
    if "DATABASE_URL" in st.secrets:
        return st.secrets["DATABASE_URL"]
    return ""

def run_query(sql, params=None):
    db_url = get_db_url()
    if not db_url:
        st.error("कृपया Streamlit Secrets मध्ये DATABASE_URL सेट करा.")
        st.stop()
        
    endpoint = db_url.replace("postgresql://", "https://").replace("postgres://", "https://")
    endpoint = endpoint.split("?")[0] + "/sql"
    
    payload = {"query": sql}
    if params:
        payload["params"] = params
        
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = resp.read().decode("utf-8")
            return json.loads(resp_data)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        st.error(f"डेटाबेस त्रुटी: {err_msg}")
        raise e

def execute_sql(sql, params=None):
    run_query(sql, params)

def query_df(sql, params=None):
    res = run_query(sql, params)
    rows = res.get("rows", [])
    fields = [f["name"] for f in res.get("fields", [])]
    return pd.DataFrame(rows, columns=fields)

def init_db():
    run_query("""
        CREATE TABLE IF NOT EXISTS flats (
            flat_no VARCHAR(50) PRIMARY KEY,
            owner_name VARCHAR(255) NOT NULL,
            contact VARCHAR(50),
            monthly_maint DOUBLE PRECISION NOT NULL DEFAULT 1000.0
        );
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS maintenance_received (
            id SERIAL PRIMARY KEY,
            flat_no VARCHAR(50) NOT NULL,
            month_year VARCHAR(50) NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            payment_mode VARCHAR(100) NOT NULL,
            payment_date VARCHAR(50) NOT NULL,
            remark TEXT
        );
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            expense_date VARCHAR(50) NOT NULL,
            paid_to VARCHAR(255),
            payment_mode VARCHAR(100) NOT NULL,
            remark TEXT
        );
    """)

init_db()

st.markdown('<div class="main-title">🏰 राजगड गृहनिर्माण संस्था (Housing Society)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">क्लाऊड डेटाबेस सुरक्षित मेंटेनन्स, खर्च आणि थकबाकी व्यवस्थापन प्रणाली</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "📌 नेव्हिगेशन मेनू",
    [
        "📊 डॅशबोर्ड (हिशोब सारांश)",
        "🏢 फ्लॅट व सभासद नोंदणी (Members)",
        "💵 मेंटेनन्स जमा (Receipts)",
        "💸 सोसायटी खर्च नोंद (Expenses)",
        "⚠️ फ्लॅटनिहाय सविस्तर थकबाकी अहवाल (Pending Dues)",
        "📑 अहवाल व डाऊनलोड (Reports / Excel)"
    ]
)

# ================= 1. डॅशबोर्ड =================
if menu == "📊 डॅशबोर्ड (हिशोब सारांश)":
    st.subheader("📊 संस्थेचा आर्थिक सारांश")
    
    df_maint = query_df("SELECT * FROM maintenance_received;")
    df_exp = query_df("SELECT * FROM expenses;")
    df_flats = query_df("SELECT * FROM flats;")

    total_maint = float(df_maint["amount"].sum()) if not df_maint.empty else 0.0
    total_exp = float(df_exp["amount"].sum()) if not df_exp.empty else 0.0
    balance = total_maint - total_exp

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("एकूण फ्लॅट्स", f"{len(df_flats)} फ्लॅट्स")
    col2.metric("एकूण जमा मेंटेनन्स", f"₹ {total_maint:,.2f}")
    col3.metric("एकूण झालेला खर्च", f"₹ {total_exp:,.2f}")
    col4.metric("शिल्लक निधी (Balance)", f"₹ {balance:,.2f}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 📥 नुकतीच झालेली मेंटेनन्स जमा")
        if not df_maint.empty:
            st.dataframe(df_maint.sort_values(by="id", ascending=False).head(5)[["flat_no", "month_year", "amount", "payment_mode", "payment_date"]], use_container_width=True)
        else:
            st.info("कोणतीही नोंद उपलब्ध नाही.")
    with c2:
        st.write("### 📤 नुकताच झालेला खर्च")
        if not df_exp.empty:
            st.dataframe(df_exp.sort_values(by="id", ascending=False).head(5)[["title", "category", "amount", "payment_mode", "expense_date"]], use_container_width=True)
        else:
            st.info("खर्चाची नोंद उपलब्ध नाही.")

# ================= 2. फ्लॅट व सभासद नोंदणी =================
elif menu == "🏢 फ्लॅट व सभासद नोंदणी (Members)":
    st.subheader("🏢 फ्लॅट व सभासद व्यवस्थापन")
    tab1, tab2 = st.tabs(["नवीन फ्लॅट / सभासद जोडा", "नोंदणीकृत फ्लॅट्स (Edit/Delete)"])
    
    with tab1:
        with st.form("add_flat_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_no = col1.text_input("फ्लॅट नंबर (उदा. 101, A-202):").strip().upper()
            o_name = col2.text_input("सभासदाचे पूर्ण नाव:").strip()
            contact = col1.text_input("मोबाईल नंबर:")
            m_maint = col2.number_input("मासिक मेंटेनन्स आकारणी (₹):", min_value=0.0, value=1000.0, step=100.0)
            
            btn_add = st.form_submit_button("फ्लॅट सेव्ह करा")
            if btn_add:
                if f_no and o_name:
                    try:
                        execute_sql(
                            "INSERT INTO flats (flat_no, owner_name, contact, monthly_maint) VALUES ($1, $2, $3, $4)",
                            [f_no, o_name, contact, m_maint]
                        )
                        st.success(f"फ्लॅट क्र. {f_no} यशस्वीरीत्या जोडला गेला!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"त्रुटी: फ्लॅट आधीच नोंदणीकृत असू शकतो किंवा {e}")
                else:
                    st.error("कृपया फ्लॅट नंबर आणि नाव भरा.")
                    
    with tab2:
        df_flats = query_df("SELECT * FROM flats;")
        if not df_flats.empty:
            st.dataframe(df_flats, use_container_width=True)
            flat_to_edit = st.selectbox("बदल करण्यासाठी फ्लॅट निवडा:", df_flats["flat_no"].tolist())
            flat_curr = df_flats[df_flats["flat_no"] == flat_to_edit].iloc[0]
            
            with st.form("edit_flat_form"):
                new_owner = st.text_input("सभासदाचे नाव:", value=flat_curr["owner_name"])
                new_contact = st.text_input("मोबाईल नंबर:", value=flat_curr["contact"] or "")
                new_maint = st.number_input("मासिक मेंटेनन्स (₹):", value=float(flat_curr["monthly_maint"]), step=100.0)
                
                col_u1, col_u2 = st.columns(2)
                btn_update = col_u1.form_submit_button("माहिती अपडेट करा")
                btn_del = col_u2.form_submit_button("हा फ्लॅट डिलीट करा")
                
                if btn_update:
                    execute_sql(
                        "UPDATE flats SET owner_name=$1, contact=$2, monthly_maint=$3 WHERE flat_no=$4",
                        [new_owner, new_contact, new_maint, flat_to_edit]
                    )
                    st.success("माहिती अपडेट झाली!")
                    st.rerun()
                if btn_del:
                    execute_sql("DELETE FROM flats WHERE flat_no=$1", [flat_to_edit])
                    st.warning("फ्लॅट डिलीट केला गेला!")
                    st.rerun()

# ================= 3. मेंटेनन्स जमा =================
elif menu == "💵 मेंटेनन्स जमा (Receipts)":
    st.subheader("💵 मेंटेनन्स पावती नोंदवणे")
    df_flats = query_df("SELECT * FROM flats;")
    
    if df_flats.empty:
        st.warning("कृपया आधी फ्लॅट्स जोडा.")
    else:
        flats_dict = {
            row["flat_no"]: {
                "owner": row["owner_name"],
                "maint": float(row["monthly_maint"])
            }
            for _, row in df_flats.iterrows()
        }
        
        flat_list = list(flats_dict.keys())

        col_f1, col_f2 = st.columns(2)
        sel_flat = col_f1.selectbox("फ्लॅट नंबर निवडा:", flat_list)
        curr_owner = flats_dict[sel_flat]["owner"]
        curr_maint = flats_dict[sel_flat]["maint"]
        
        col_f2.text_input("सभासदाचे नाव:", value=curr_owner, disabled=True)

        with st.form("maint_entry_form", clear_on_submit=True):
            col3, col4 = st.columns(2)
            curr_y = datetime.now().year
            sel_year = col3.selectbox("वर्ष:", [curr_y, curr_y - 1, curr_y + 1], index=0)
            sel_month = col4.selectbox("महिना:", MONTHS_LIST, index=datetime.now().month - 1)
            
            month_year_str = f"{sel_month} {sel_year}"
            
            col5, col6 = st.columns(2)
            rec_amt = col5.number_input("रक्कम (₹):", value=curr_maint, step=100.0)
            pay_mode = col6.selectbox("पैसे कसे मिळाले?:", ["ऑनलाइन (GPay / PhonePe / NEFT)", "रोख (Cash)", "धनादेश (Cheque)"])
            
            rec_date = st.date_input("पावती तारीख:", value=datetime.today().date())
            remark = st.text_input("रिमार्क (उदा. UTR Number / Cash):")
            
            btn_save_maint = st.form_submit_button("पावती सेव्ह करा")
            if btn_save_maint:
                execute_sql(
                    """
                    INSERT INTO maintenance_received (flat_no, month_year, amount, payment_mode, payment_date, remark)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    [sel_flat, month_year_str, rec_amt, pay_mode, str(rec_date), remark]
                )
                st.success(f"फ्लॅट क्र. {sel_flat} साठी {month_year_str} चे मेंटेनन्स नोंदवले गेले!")
                st.rerun()

        st.markdown("---")
        df_maint_all = query_df("""
            SELECT m.id, m.flat_no as "फ्लॅट क्र.", f.owner_name as "नाव", 
                   m.month_year as "महिना/वर्ष", m.amount as "रक्कम (₹)", 
                   m.payment_mode as "पद्धत", m.payment_date as "तारीख", m.remark as "रिमार्क"
            FROM maintenance_received m
            LEFT JOIN flats f ON m.flat_no = f.flat_no
            ORDER BY m.id DESC;
        """)
            
        if not df_maint_all.empty:
            st.dataframe(df_maint_all, use_container_width=True)
            with st.expander("🗑️ चुकीची पावती हटवा"):
                del_rec_id = st.selectbox("पावती ID निवडा:", df_maint_all["id"].tolist())
                if st.button("पावती डिलीट करा", type="primary"):
                    execute_sql("DELETE FROM maintenance_received WHERE id=$1", [int(del_rec_id)])
                    st.success("पावती काढली!")
                    st.rerun()

# ================= 4. सोसायटी खर्च नोंद =================
elif menu == "💸 सोसायटी खर्च नोंद (Expenses)":
    st.subheader("💸 संस्थेचा खर्च नोंदवणे")
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        exp_title = col1.text_input("खर्चाचे नाव:").strip()
        exp_cat = col2.selectbox("प्रवर्ग:", [
            "लाईट बिल (Electricity)", "पाणी पुरवठा (Water)", "सफाई व स्वच्छता (Cleaning)",
            "सुरक्षा रक्षक पगार (Security)", "लिफ्ट देखभाल (Lift Maintenance)",
            "दुरुस्ती व कामे (Repairs/Civil)", "इतर किरकोळ खर्च (Miscellaneous)"
        ])
        
        col3, col4 = st.columns(2)
        exp_amt = col3.number_input("रक्कम (₹):", min_value=0.0, step=100.0)
        exp_date = col4.date_input("खर्च तारीख:", value=datetime.today().date())
        
        col5, col6 = st.columns(2)
        paid_to = col5.text_input("पैसे कोणास दिले?:")
        exp_mode = col6.selectbox("पेमेंट मोड:", ["ऑनलाइन (UPI/NEFT)", "रोख (Cash)", "धनादेश (Cheque)"])
        exp_remark = st.text_input("शेरा / बिल नंबर:")
        
        btn_save_exp = st.form_submit_button("खर्च सेव्ह करा")
        if btn_save_exp:
            if exp_title and exp_amt > 0:
                execute_sql(
                    """
                    INSERT INTO expenses (title, category, amount, expense_date, paid_to, payment_mode, remark)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    [exp_title, exp_cat, exp_amt, str(exp_date), paid_to, exp_mode, exp_remark]
                )
                st.success("खर्च नोंद सेव्ह झाली!")
                st.rerun()

    st.markdown("---")
    df_exp_all = query_df("""
        SELECT id, title as "तपशील", category as "प्रवर्ग", amount as "रक्कम (₹)", 
               expense_date as "तारीख", paid_to as "कोणास दिले", payment_mode as "पद्धत" 
        FROM expenses ORDER BY id DESC;
    """)
    if not df_exp_all.empty:
        st.dataframe(df_exp_all, use_container_width=True)

# ================= 5. फ्लॅटनिहाय सविस्तर थकबाकी अहवाल =================
elif menu == "⚠️ फ्लॅटनिहाय सविस्तर थकबाकी अहवाल (Pending Dues)":
    st.subheader("⚠️ फ्लॅटनिहाय थकबाकी व बाकी महिन्यांचा अहवाल")
    df_flats = query_df("SELECT * FROM flats;")

    if df_flats.empty:
        st.warning("कृपया आधी फ्लॅट्स जोडा.")
    else:
        curr_y = datetime.now().year
        col_s1, col_s2, col_s3 = st.columns(3)
        selected_year = col_s1.selectbox("वर्ष निवडा:", [curr_y, 2026, 2027], index=0)
        
        default_start_idx = 7 if selected_year == 2026 else 0
        from_month = col_s2.selectbox("सुरुवातीचा महिना:", MONTHS_LIST, index=default_start_idx)
        
        curr_m_idx = datetime.now().month - 1
        upto_month = col_s3.selectbox("शेवटचा महिना:", MONTHS_LIST, index=curr_m_idx)

        from_idx = MONTHS_LIST.index(from_month)
        upto_idx = MONTHS_LIST.index(upto_month) + 1
        
        months_to_check = [f"{m} {selected_year}" for m in MONTHS_LIST[from_idx:upto_idx]]

        df_paid = query_df("SELECT flat_no, month_year, amount FROM maintenance_received;")
            
        dues_report = []
        total_society_dues = 0.0

        for _, flat in df_flats.iterrows():
            f_no = flat["flat_no"]
            owner = flat["owner_name"]
            contact = flat["contact"] or "-"
            rate = float(flat["monthly_maint"])

            flat_receipts = df_paid[df_paid["flat_no"] == f_no] if not df_paid.empty else pd.DataFrame()
            paid_months = flat_receipts["month_year"].unique().tolist() if not flat_receipts.empty else []

            unpaid_months = [m for m in months_to_check if m not in paid_months]

            pending_months_count = len(unpaid_months)
            total_pending_amount = pending_months_count * rate
            total_society_dues += total_pending_amount

            status = "🔴 थकबाकी आहे" if pending_months_count > 0 else "🟢 सर्व भरले (Nil)"
            months_str = ", ".join(unpaid_months) if unpaid_months else "कोणताही महिना बाकी नाही"

            dues_report.append({
                "फ्लॅट क्र.": f_no,
                "सभासदाचे नाव": owner,
                "मोबाईल": contact,
                "मासिक दर (₹)": rate,
                "एकूण बाकी महिने": pending_months_count,
                "एकूण थकबाकी रक्कम (₹)": total_pending_amount,
                "बाकी असलेले महिने": months_str,
                "स्थिती": status
            })

        df_dues_result = pd.DataFrame(dues_report)

        c_m1, c_m2, c_m3 = st.columns(3)
        unpaid_count = len(df_dues_result[df_dues_result["एकूण बाकी महिने"] > 0])
        c_m1.metric("एकूण फ्लॅट्स", f"{len(df_flats)}")
        c_m2.metric("थकबाकीदार फ्लॅट्स", f"{unpaid_count} फ्लॅट्स")
        c_m3.metric("एकूण थकबाकी रक्कम (Dues)", f"₹ {total_society_dues:,.2f}")

        st.markdown("---")
        filter_choice = st.radio("यादी कशी पाहायची आहे?:", ["फक्त थकबाकीदार फ्लॅट्स", "सर्व फ्लॅट्सची यादी"], horizontal=True)
        display_df = df_dues_result[df_dues_result["एकूण बाकी महिने"] > 0] if filter_choice == "फक्त थकबाकीदार फ्लॅट्स" else df_dues_result

        st.dataframe(display_df, use_container_width=True)

        output_dues = io.BytesIO()
        with pd.ExcelWriter(output_dues, engine='openpyxl') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Pending_Dues')
        st.download_button(
            label="📥 थकबाकीदार अहवाल Excel डाउनलोड करा (.xlsx)",
            data=output_dues.getvalue(),
            file_name=f"Rajgad_Dues_{selected_year}_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ================= 6. अहवाल व डाऊनलोड =================
elif menu == "📑 अहवाल व डाऊनलोड (Reports / Excel)":
    st.subheader("📑 अहवाल (Reports) व Excel डाऊनलोड")
    rep_choice = st.radio("कोणता अहवाल डाउनलोड करायचा आहे?", [
        "१. संपूर्ण मेंटेनन्स जमा अहवाल (Maintenance Received)",
        "२. संपूर्ण खर्च अहवाल (Expenses Report)",
        "३. एकत्रित ताळेबंद / नफा-तोटा (Profit & Loss Summary)"
    ])
    
    if rep_choice == "१. संपूर्ण मेंटेनन्स जमा अहवाल (Maintenance Received)":
        df = query_df("""
            SELECT m.id, m.flat_no as "फ्लॅट क्र.", f.owner_name as "सभासदाचे नाव", 
                   m.month_year as "महिना/वर्ष", m.amount as "जमा रक्कम (₹)", 
                   m.payment_mode as "पद्धत", m.payment_date as "पावती तारीख", m.remark as "रिमार्क"
            FROM maintenance_received m
            LEFT JOIN flats f ON m.flat_no = f.flat_no
            ORDER BY m.payment_date DESC;
        """)
        st.dataframe(df, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Maintenance')
        st.download_button("📥 मेंटेनन्स अहवाल Excel डाउनलोड करा", out.getvalue(), "Maintenance_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif rep_choice == "२. संपूर्ण खर्च अहवाल (Expenses Report)":
        df = query_df("""
            SELECT id, title as "खर्चाचे नाव", category as "प्रवर्ग", amount as "रक्कम (₹)", 
                   expense_date as "तारीख", paid_to as "कोणास दिले", payment_mode as "पेमेंट पद्धत", remark as "रिमार्क"
            FROM expenses ORDER BY expense_date DESC;
        """)
        st.dataframe(df, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')
        st.download_button("📥 खर्च अहवाल Excel डाउनलोड करा", out.getvalue(), "Expenses_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
    elif rep_choice == "३. एकत्रित ताळेबंद / नफा-तोटा (Profit & Loss Summary)":
        df_m = query_df("SELECT SUM(amount) as total_maint FROM maintenance_received;")
        df_e = query_df("SELECT SUM(amount) as total_exp FROM expenses;")
        tm = float(df_m['total_maint'].iloc[0]) if not df_m.empty and pd.notnull(df_m['total_maint'].iloc[0]) else 0.0
        te = float(df_e['total_exp'].iloc[0]) if not df_e.empty and pd.notnull(df_e['total_exp'].iloc[0]) else 0.0
        bal = tm - te
        df_summary = pd.DataFrame({
            "तपशील": ["एकूण जमा मेंटेनन्स", "एकूण झालेला खर्च", "शिल्लक निधी (Net Balance)"],
            "रक्कम (₹)": [tm, te, bal]
        })
        st.dataframe(df_summary, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df_summary.to_excel(writer, index=False, sheet_name='Summary')
        st.download_button("📥 ताळेबंद समरी Excel डाउनलोड करा", out.getvalue(), "Balance_Summary.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
