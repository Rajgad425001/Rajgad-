import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# पेज लेआउट आणि टायटल सेट करणे
st.set_page_config(
    page_title="राजगड सोसायटी व्यवस्थापन प्रणाली",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS स्टायलिंग (मराठी फॉन्ट व आकर्षक डिझाईन) ---
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
    .stat-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #8B0000;
    }
</style>
""", unsafe_allow_html=True)

# --- डेटाबेस इनिशियलायझेशन ---
def get_connection():
    return sqlite3.connect("rajgad_society.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # १. फ्लॅट धारक टेबल
    c.execute("""
        CREATE TABLE IF NOT EXISTS flats (
            flat_no TEXT PRIMARY KEY,
            owner_name TEXT NOT NULL,
            contact TEXT,
            monthly_maint REAL NOT NULL DEFAULT 1000.0
        )
    """)
    # २. मेंटेनन्स जमा टेबल
    c.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_received (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flat_no TEXT NOT NULL,
            month_year TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            remark TEXT,
            FOREIGN KEY(flat_no) REFERENCES flats(flat_no)
        )
    """)
    # ३. सोसायटी खर्च टेबल
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL,
            paid_to TEXT,
            payment_mode TEXT NOT NULL,
            remark TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- हेडर ---
st.markdown('<div class="main-title">🏰 राजगड गृहनिर्माण संस्था (Housing Society)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">मेंटेनन्स, खर्च आणि थकबाकी व्यवस्थापन प्रणाली</div>', unsafe_allow_html=True)

# साइडबार मेनू
menu = st.sidebar.radio(
    "📌 नेव्हिगेशन मेनू",
    [
        "📊 डॅशबोर्ड (हिशोब सारांश)",
        "🏢 फ्लॅट व सभासद नोंदणी (Members)",
        "💵 मेंटेनन्स जमा (Receipts)",
        "💸 सोसायटी खर्च नोंद (Expenses)",
        "⚠️ थकबाकीदार यादी (Pending Dues)",
        "📑 अहवाल व डाऊनलोड (Reports / Excel)"
    ]
)

conn = get_connection()

# ================= 1. डॅशबोर्ड =================
if menu == "📊 डॅशबोर्ड (हिशोब सारांश)":
    st.subheader("📊 संस्थेचा आर्थिक सारांश")
    
    df_maint = pd.read_sql_query("SELECT * FROM maintenance_received", conn)
    df_exp = pd.read_sql_query("SELECT * FROM expenses", conn)
    df_flats = pd.read_sql_query("SELECT * FROM flats", conn)

    total_maint = df_maint["amount"].sum() if not df_maint.empty else 0.0
    total_exp = df_exp["amount"].sum() if not df_exp.empty else 0.0
    balance = total_maint - total_exp
    total_flats_count = len(df_flats)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("एकूण फ्लॅट्स", f"{total_flats_count} फ्लॅट्स")
    col2.metric("एकूण जमा मेंटेनन्स", f"₹ {total_maint:,.2f}")
    col3.metric("एकूण झालेला खर्च", f"₹ {total_exp:,.2f}")
    col4.metric("शिल्लक निधी (Balance)", f"₹ {balance:,.2f}")

    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 📥 नुकतीच झालेली मेंटेनन्स जमा")
        if not df_maint.empty:
            recent_m = df_maint.sort_values(by="id", ascending=False).head(5)
            st.dataframe(recent_m[["flat_no", "month_year", "amount", "payment_mode", "payment_date"]], use_container_width=True)
        else:
            st.info("अद्याप कोणतीही मेंटेनन्स नोंद उपलब्ध नाही.")
            
    with c2:
        st.write("### 📤 नुकताच झालेला खर्च")
        if not df_exp.empty:
            recent_e = df_exp.sort_values(by="id", ascending=False).head(5)
            st.dataframe(recent_e[["title", "category", "amount", "payment_mode", "expense_date"]], use_container_width=True)
        else:
            st.info("अद्याप कोणतीही खर्चाची नोंद उपलब्ध नाही.")

# ================= 2. फ्लॅट व सभासद नोंदणी =================
elif menu == "🏢 फ्लॅट व सभासद नोंदणी (Members)":
    st.subheader("🏢 फ्लॅट व सभासद व्यवस्थापन")
    
    tab1, tab2 = st.tabs(["नवीन फ्लॅट / सभासद जोडा", "अस्तित्वात असलेले फ्लॅट्स (Edit/Delete)"])
    
    with tab1:
        with st.form("add_flat_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_no = col1.text_input("फ्लॅट नंबर (उदा. A-101):").strip().upper()
            o_name = col2.text_input("सभासदाचे पूर्ण नाव:").strip()
            contact = col1.text_input("मोबाईल नंबर:")
            m_maint = col2.number_input("मासिक मेंटेनन्स आकारणी (₹):", min_value=0.0, value=1000.0, step=100.0)
            
            btn_add = st.form_submit_button("फ्लॅट सेव्ह करा")
            if btn_add:
                if f_no and o_name:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO flats (flat_no, owner_name, contact, monthly_maint) VALUES (?, ?, ?, ?)",
                                  (f_no, o_name, contact, m_maint))
                        conn.commit()
                        st.success(f"फ्लॅट क्र. {f_no} यशस्वीरीत्या जोडला गेला!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"फ्लॅट क्र. {f_no} आधीच नोंदणीकृत आहे!")
                else:
                    st.error("कृपया फ्लॅट नंबर आणि सभासदाचे नाव भरा.")
    
    with tab2:
        df_flats = pd.read_sql_query("SELECT * FROM flats", conn)
        if not df_flats.empty:
            st.dataframe(df_flats, use_container_width=True)
            
            st.markdown("#### ✏️ फ्लॅट माहिती अपडेट किंवा डिलीट करा")
            flat_to_edit = st.selectbox("फ्लॅट नंबर निवडा:", df_flats["flat_no"].tolist())
            flat_curr = df_flats[df_flats["flat_no"] == flat_to_edit].iloc[0]
            
            with st.form("edit_flat_form"):
                new_owner = st.text_input("सभासदाचे नाव:", value=flat_curr["owner_name"])
                new_contact = st.text_input("मोबाईल नंबर:", value=flat_curr["contact"] or "")
                new_maint = st.number_input("मासिक मेंटेनन्स आकारणी (₹):", value=float(flat_curr["monthly_maint"]), step=100.0)
                
                col_u1, col_u2 = st.columns(2)
                btn_update = col_u1.form_submit_button("माहिती अपडेट करा")
                btn_del = col_u2.form_submit_button("हा फ्लॅट काढून टाका (Delete)")
                
                if btn_update:
                    c = conn.cursor()
                    c.execute("UPDATE flats SET owner_name=?, contact=?, monthly_maint=? WHERE flat_no=?",
                              (new_owner, new_contact, new_maint, flat_to_edit))
                    conn.commit()
                    st.success("माहिती अपडेट झाली!")
                    st.rerun()
                
                if btn_del:
                    c = conn.cursor()
                    c.execute("DELETE FROM flats WHERE flat_no=?", (flat_to_edit,))
                    conn.commit()
                    st.warning("फ्लॅट डिलीट केला गेला!")
                    st.rerun()
        else:
            st.info("अद्याप कोणतेही फ्लॅट जोडलेले नाहीत.")

# ================= 3. मेंटेनन्स जमा =================
elif menu == "💵 मेंटेनन्स जमा (Receipts)":
    st.subheader("💵 मेंटेनन्स पावती नोंदवणे")
    
    df_flats = pd.read_sql_query("SELECT * FROM flats", conn)
    if df_flats.empty:
        st.warning("कृपया आधी 'फ्लॅट व सभासद नोंदणी' विभागात जाऊन फ्लॅट्स जोडा.")
    else:
        flat_list = df_flats["flat_no"].tolist()
        
        with st.form("maint_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            sel_flat = col1.selectbox("फ्लॅट नंबर निवडा:", flat_list)
            
            # निवडलेल्या फ्लॅट धारकाचे नाव आणि रक्कम दाखवणे
            flat_info = df_flats[df_flats["flat_no"] == sel_flat].iloc[0]
            col2.text_input("सभासदाचे नाव:", value=flat_info["owner_name"], disabled=True)
            
            col3, col4 = st.columns(2)
            months = ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]
            curr_year = datetime.now().year
            sel_month = col3.selectbox("कोणत्या महिन्याचे मेंटेनन्स?", [f"{m} {curr_year}" for m in months])
            rec_amt = col4.number_input("मिळालेली रक्कम (₹):", value=float(flat_info["monthly_maint"]), step=100.0)
            
            col5, col6 = st.columns(2)
            pay_mode = col5.selectbox("पैसे कसे मिळाले? (Payment Mode):", ["ऑनलाइन (GPay / PhonePe / NEFT)", "रोख (Cash)", "धनादेश (Cheque)"])
            rec_date = col6.date_input("जमा तारीख:")
            
            remark = st.text_input("रिमार्क / तपशील (उदा. UTR Number, Txn ID, इ.):")
            
            btn_save_maint = st.form_submit_button("पावती सेव्ह करा")
            if btn_save_maint:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO maintenance_received (flat_no, month_year, amount, payment_mode, payment_date, remark)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sel_flat, sel_month, rec_amt, pay_mode, str(rec_date), remark))
                conn.commit()
                st.success(f"फ्लॅट {sel_flat} साठी ₹{rec_amt} ची पावती यशस्वीपणे नोंदवली गेली!")
                st.rerun()

        st.markdown("---")
        st.write("### 📜 सर्व मेंटेनन्स पावत्यांची यादी")
        df_maint_all = pd.read_sql_query("""
            SELECT m.id, m.flat_no as 'फ्लॅट क्र.', f.owner_name as 'सभासदाचे नाव', 
                   m.month_year as 'महिना', m.amount as 'रक्कम (₹)', 
                   m.payment_mode as 'पद्धत', m.payment_date as 'तारीख', m.remark as 'रिमार्क'
            FROM maintenance_received m
            LEFT JOIN flats f ON m.flat_no = f.flat_no
            ORDER BY m.id DESC
        """, conn)
        
        if not df_maint_all.empty:
            st.dataframe(df_maint_all, use_container_width=True)
            with st.expander("🗑️ चुकीची पावती हटवा (Delete Receipt)"):
                del_rec_id = st.selectbox("पावती ID निवडा:", df_maint_all["id"].tolist())
                if st.button("पावती डिलीट करा", type="primary"):
                    c = conn.cursor()
                    c.execute("DELETE FROM maintenance_received WHERE id=?", (del_rec_id,))
                    conn.commit()
                    st.success("पावती काढून टाकली!")
                    st.rerun()
        else:
            st.info("अद्याप कोणत्याही पावत्या नोंदवलेल्या नाहीत.")

# ================= 4. सोसायटी खर्च नोंद =================
elif menu == "💸 सोसायटी खर्च नोंद (Expenses)":
    st.subheader("💸 संस्थेचा खर्च नोंदवणे")
    
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        exp_title = col1.text_input("खर्चाचे नाव / तपशील (उदा. वॉटर टँकर बिल):").strip()
        exp_cat = col2.selectbox("खर्चाचा प्रवर्ग (Category):", [
            "लाईट बिल (Electricity)",
            "पाणी पुरवठा (Water)",
            "सफाई व स्वच्छता (Cleaning)",
            "सुरक्षा रक्षक पगार (Security)",
            "लिफ्ट देखभाल (Lift Maintenance)",
            "दुरुस्ती व कामे (Repairs/Civil)",
            "इतर किरकोळ खर्च (Miscellaneous)"
        ])
        
        col3, col4 = st.columns(2)
        exp_amt = col3.number_input("खर्च रक्कम (₹):", min_value=0.0, step=100.0)
        exp_date = col4.date_input("खर्च केल्याची तारीख:")
        
        col5, col6 = st.columns(2)
        paid_to = col5.text_input("पैसे कोणाला दिले? (Paid To):")
        exp_mode = col6.selectbox("खर्च पेमेंट प्रकार:", ["ऑनलाइन (Online/UPI)", "रोख (Cash)", "धनादेश (Cheque)"])
        
        exp_remark = st.text_input("अतिरिक्त शेरा / बिल नंबर:")
        
        btn_save_exp = st.form_submit_button("खर्च सेव्ह करा")
        if btn_save_exp:
            if exp_title and exp_amt > 0:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO expenses (title, category, amount, expense_date, paid_to, payment_mode, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (exp_title, exp_cat, exp_amt, str(exp_date), paid_to, exp_mode, exp_remark))
                conn.commit()
                st.success("खर्चाची नोंद सेव्ह झाली!")
                st.rerun()
            else:
                st.error("कृपया खर्चाचा तपशील आणि योग्य रक्कम भरा.")
                
    st.markdown("---")
    st.write("### 📋 झालेल्या सर्व खर्चांची यादी")
    df_exp_all = pd.read_sql_query("SELECT id, title as 'तपशील', category as 'प्रवर्ग', amount as 'रक्कम (₹)', expense_date as 'तारीख', paid_to as 'कोणास दिले', payment_mode as 'पद्धत', remark as 'रिमार्क' FROM expenses ORDER BY id DESC", conn)
    
    if not df_exp_all.empty:
        st.dataframe(df_exp_all, use_container_width=True)
        with st.expander("🗑️ चुकीची खर्च नोंद हटवा"):
            del_exp_id = st.selectbox("खर्च आयडी निवडा:", df_exp_all["id"].tolist())
            if st.button("खर्च नोंद डिलीट करा", type="primary"):
                c = conn.cursor()
                c.execute("DELETE FROM expenses WHERE id=?", (del_exp_id,))
                conn.commit()
                st.success("खर्च नोंद हटवली!")
                st.rerun()
    else:
        st.info("अद्याप कोणत्याही खर्चाची नोंद नाही.")

# ================= 5. थकबाकीदार यादी =================
elif menu == "⚠️ थकबाकीदार यादी (Pending Dues)":
    st.subheader("⚠️ मेंटेनन्स थकबाकीदार अहवाल (Pending Dues)")
    
    df_flats = pd.read_sql_query("SELECT * FROM flats", conn)
    if df_flats.empty:
        st.info("फ्लॅट्स उपलब्ध नाहीत.")
    else:
        months = ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]
        curr_year = datetime.now().year
        check_month = st.selectbox("कोणत्या महिन्याची थकबाकी तपासायची आहे?", [f"{m} {curr_year}" for m in months])
        
        # सदर महिन्यामध्ये ज्यांच्याकडून पैसे आले त्यांची यादी
        df_paid = pd.read_sql_query("SELECT flat_no, SUM(amount) as paid_amt FROM maintenance_received WHERE month_year=? GROUP BY flat_no", conn, params=(check_month,))
        
        merged = pd.merge(df_flats, df_paid, on="flat_no", how="left")
        merged["paid_amt"] = merged["paid_amt"].fillna(0.0)
        merged["थकबाकी (₹)"] = merged["monthly_maint"] - merged["paid_amt"]
        merged["स्थिती"] = merged["थकबाकी (₹)"].apply(lambda x: "✅ भरले (Paid)" if x <= 0 else "❌ थकबाकी (Unpaid)")
        
        # रिनेमिंग
        view_df = merged[["flat_no", "owner_name", "contact", "monthly_maint", "paid_amt", "थकबाकी (₹)", "स्थिती"]]
        view_df.columns = ["फ्लॅट क्र.", "सभासदाचे नाव", "संपर्क", "नियमित मेंटेनन्स (₹)", "जमा रक्कम (₹)", "थकबाकी (₹)", "स्थिती"]
        
        st.dataframe(view_df, use_container_width=True)
        
        # फक्त थकबाकीदार
        unpaid_df = view_df[view_df["स्थिती"] == "❌ थकबाकी (Unpaid)"]
        st.error(f"🔴 एकूण थकबाकीदार फ्लॅट्स संख्या: {len(unpaid_df)} | एकूण येणे बाकी: ₹{unpaid_df['थकबाकी (₹)'].sum():,.2f}")

# ================= 6. अहवाल व डाऊनलोड =================
elif menu == "📑 अहवाल व डाऊनलोड (Reports / Excel)":
    st.subheader("📑 अहवाल (Reports) व Excel डाऊनलोड")
    
    rep_choice = st.radio("कोणता अहवाल डाउनलोड करायचा आहे?", [
        "१. संपूर्ण मेंटेनन्स जमा अहवाल (Maintenance Received)",
        "२. संपूर्ण खर्च अहवाल (Expenses Report)",
        "३. एकत्रित ताळेबंद / नफा-तोटा (Profit & Loss Summary)"
    ])
    
    if rep_choice == "१. संपूर्ण मेंटेनन्स जमा अहवाल (Maintenance Received)":
        df = pd.read_sql_query("""
            SELECT m.id, m.flat_no as 'फ्लॅट क्र.', f.owner_name as 'सभासदाचे नाव', 
                   m.month_year as 'महिना', m.amount as 'जमा रक्कम (₹)', 
                   m.payment_mode as 'पद्धत', m.payment_date as 'पावती तारीख', m.remark as 'रिमार्क'
            FROM maintenance_received m
            LEFT JOIN flats f ON m.flat_no = f.flat_no
            ORDER BY m.payment_date DESC
        """, conn)
        st.dataframe(df, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Maintenance')
        st.download_button(
            label="📥 Excel फाईल डाउनलोड करा (.xlsx)",
            data=output.getvalue(),
            file_name=f"Rajgad_Maintenance_Report_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    elif rep_choice == "२. संपूर्ण खर्च अहवाल (Expenses Report)":
        df = pd.read_sql_query("""
            SELECT id, title as 'खर्चाचे नाव', category as 'प्रवर्ग', amount as 'रक्कम (₹)', 
                   expense_date as 'तारीख', paid_to as 'कोणास दिले', payment_mode as 'पेमेंट पद्धत', remark as 'रिमार्क'
            FROM expenses
            ORDER BY expense_date DESC
        """, conn)
        st.dataframe(df, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')
        st.download_button(
            label="📥 Excel फाईल डाउनलोड करा (.xlsx)",
            data=output.getvalue(),
            file_name=f"Rajgad_Expense_Report_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    elif rep_choice == "३. एकत्रित ताळेबंद / नफा-तोटा (Profit & Loss Summary)":
        df_m = pd.read_sql_query("SELECT SUM(amount) as total_maint FROM maintenance_received", conn)
        df_e = pd.read_sql_query("SELECT SUM(amount) as total_exp FROM expenses", conn)
        
        tm = df_m['total_maint'].iloc[0] or 0.0
        te = df_e['total_exp'].iloc[0] or 0.0
        bal = tm - te
        
        summary_data = {
            "तपशील": ["एकूण जमा मेंटेनन्स", "एकूण झालेला खर्च", "शिल्लक शिल्लक निधी (Net Balance)"],
            "रक्कम (₹)": [tm, te, bal]
        }
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_summary.to_excel(writer, index=False, sheet_name='Summary')
        st.download_button(
            label="📥 समरी Excel डाउनलोड करा (.xlsx)",
            data=output.getvalue(),
            file_name=f"Rajgad_Summary_Balance_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

conn.close()
