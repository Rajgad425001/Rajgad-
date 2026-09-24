import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

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

def get_connection():
    return sqlite3.connect("rajgad_society.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS flats (
            flat_no TEXT PRIMARY KEY,
            owner_name TEXT NOT NULL,
            contact TEXT,
            monthly_maint REAL NOT NULL DEFAULT 1000.0
        )
    """)
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

st.markdown('<div class="main-title">🏰 राजगड गृहनिर्माण संस्था (Housing Society)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">मेंटेनन्स, खर्च आणि थकबाकी व्यवस्थापन प्रणाली</div>', unsafe_allow_html=True)

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
            st.info("मेंटेनन्स नोंद उपलब्ध नाही.")
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
                        c = conn.cursor()
                        c.execute("INSERT INTO flats (flat_no, owner_name, contact, monthly_maint) VALUES (?, ?, ?, ?)",
                                  (f_no, o_name, contact, m_maint))
                        conn.commit()
                        st.success(f"फ्लॅट क्र. {f_no} जोडला गेला!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"फ्लॅट क्र. {f_no} आधीच नोंदणीकृत आहे!")
                else:
                    st.error("सर्व माहिती अचूक भरा.")
                    
    with tab2:
        df_flats = pd.read_sql_query("SELECT * FROM flats", conn)
        if not df_flats.empty:
            st.dataframe(df_flats, use_container_width=True)
            flat_to_edit = st.selectbox("फ्लॅट निवडा:", df_flats["flat_no"].tolist())
            flat_curr = df_flats[df_flats["flat_no"] == flat_to_edit].iloc[0]
            
            with st.form("edit_flat_form"):
                new_owner = st.text_input("सभासदाचे नाव:", value=flat_curr["owner_name"])
                new_contact = st.text_input("मोबाईल नंबर:", value=flat_curr["contact"] or "")
                new_maint = st.number_input("मासिक मेंटेनन्स (₹):", value=float(flat_curr["monthly_maint"]), step=100.0)
                
                col_u1, col_u2 = st.columns(2)
                btn_update = col_u1.form_submit_button("माहिती अपडेट करा")
                btn_del = col_u2.form_submit_button("हा फ्लॅट डिलीट करा")
                
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

# ================= 3. मेंटेनन्स जमा =================
# ================= 3. मेंटेनन्स जमा =================
elif menu == "💵 मेंटेनन्स जमा (Receipts)":
    st.subheader("💵 मेंटेनन्स पावती नोंदवणे")
    df_flats = pd.read_sql_query("SELECT * FROM flats", conn)
    
    if df_flats.empty:
        st.warning("कृपया आधी 'फ्लॅट व सभासद नोंदणी' विभागात जाऊन फ्लॅट्स जोडा.")
    else:
        # १. वेगवान Fetching साठी फ्लॅट्सचा डेटा डिक्शनरीमध्ये साठवणे
        flats_dict = {
            row["flat_no"]: {
                "owner": row["owner_name"],
                "maint": float(row["monthly_maint"])
            }
            for _, row in df_flats.iterrows()
        }
        
        flat_list = list(flats_dict.keys())

        # २. फ्लॅट निवडण्याचा पर्याय फॉर्मच्या बाहेर ठेवल्याने नाव लगेच रिफ्लेक्ट होते
        col_f1, col_f2 = st.columns(2)
        sel_flat = col_f1.selectbox("फ्लॅट नंबर निवडा:", flat_list)
        
        # निवडलेल्या फ्लॅटचा मालक आणि मेंटेनन्स दर लगेच घेणे
        curr_owner = flats_dict[sel_flat]["owner"]
        curr_maint = flats_dict[sel_flat]["maint"]
        
        col_f2.text_input("सभासदाचे नाव:", value=curr_owner, disabled=True)

        # ३. पावतीचा उर्वरित फॉर्म
        with st.form("maint_entry_form", clear_on_submit=True):
            col3, col4 = st.columns(2)
            curr_y = datetime.now().year
            year_choices = [curr_y, curr_y - 1, curr_y + 1]
            sel_year = col3.selectbox("वर्ष:", year_choices, index=0)
            sel_month = col4.selectbox("महिना:", MONTHS_LIST, index=datetime.now().month - 1)
            
            month_year_str = f"{sel_month} {sel_year}"
            
            col5, col6 = st.columns(2)
            rec_amt = col5.number_input("रक्कम (₹):", value=curr_maint, step=100.0)
            pay_mode = col6.selectbox("पैसे कसे मिळाले?:", ["ऑनलाइन (GPay / PhonePe / NEFT)", "रोख (Cash)", "धनादेश (Cheque)"])
            
            rec_date = st.date_input("पावती तारीख:")
            remark = st.text_input("रिमार्क (उदा. UTR Number / Cash Received):")
            
            btn_save_maint = st.form_submit_button("पावती सेव्ह करा")
            if btn_save_maint:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO maintenance_received (flat_no, month_year, amount, payment_mode, payment_date, remark)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sel_flat, month_year_str, rec_amt, pay_mode, str(rec_date), remark))
                conn.commit()
                st.success(f"फ्लॅट क्र. {sel_flat} ({curr_owner}) साठी {month_year_str} चे मेंटेनन्स नोंदवले गेले!")
                st.rerun()

        st.markdown("---")
        df_maint_all = pd.read_sql_query("""
            SELECT m.id, m.flat_no as 'फ्लॅट क्र.', f.owner_name as 'नाव', 
                   m.month_year as 'महिना/वर्ष', m.amount as 'रक्कम (₹)', 
                   m.payment_mode as 'पद्धत', m.payment_date as 'तारीख', m.remark as 'रिमार्क'
            FROM maintenance_received m
            LEFT JOIN flats f ON m.flat_no = f.flat_no
            ORDER BY m.id DESC
        """, conn)
        if not df_maint_all.empty:
            st.dataframe(df_maint_all, use_container_width=True)
            with st.expander("🗑️ चुकीची पावती हटवा"):
                del_rec_id = st.selectbox("पावती ID निवडा:", df_maint_all["id"].tolist())
                if st.button("पावती डिलीट करा", type="primary"):
                    c = conn.cursor()
                    c.execute("DELETE FROM maintenance_received WHERE id=?", (del_rec_id,))
                    conn.commit()
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
        exp_date = col4.date_input("खर्च तारीख:")
        
        col5, col6 = st.columns(2)
        paid_to = col5.text_input("पैसे कोणास दिले?:")
        exp_mode = col6.selectbox("पेमेंट मोड:", ["ऑनलाइन (UPI/NEFT)", "रोख (Cash)", "धनादेश (Cheque)"])
        exp_remark = st.text_input("शेरा / बिल नंबर:")
        
        btn_save_exp = st.form_submit_button("खर्च सेव्ह करा")
        if btn_save_exp:
            if exp_title and exp_amt > 0:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO expenses (title, category, amount, expense_date, paid_to, payment_mode, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (exp_title, exp_cat, exp_amt, str(exp_date), paid_to, exp_mode, exp_remark))
                conn.commit()
                st.success("खर्च नोंद सेव्ह झाली!")
                st.rerun()

    st.markdown("---")
    df_exp_all = pd.read_sql_query("SELECT id, title as 'तपशील', category as 'प्रवर्ग', amount as 'रक्कम (₹)', expense_date as 'तारीख', paid_to as 'कोणास दिले', payment_mode as 'पद्धत' FROM expenses ORDER BY id DESC", conn)
    if not df_exp_all.empty:
        st.dataframe(df_exp_all, use_container_width=True)

# ================= 5. फ्लॅटनिहाय सविस्तर थकबाकी अहवाल =================
elif menu == "⚠️ फ्लॅटनिहाय सविस्तर थकबाकी अहवाल (Pending Dues)":
    st.subheader("⚠️ फ्लॅटनिहाय थकबाकी व बाकी महिन्यांचा अहवाल")
    df_flats = pd.read_sql_query("SELECT * FROM flats", conn)

    if df_flats.empty:
        st.warning("कृपया आधी फ्लॅट्स ॲड करा.")
    else:
        curr_y = datetime.now().year
        
        # हिशोब तपासण्यासाठी वर्ष व महिना फिल्टर
        col_s1, col_s2, col_s3 = st.columns(3)
        selected_year = col_s1.selectbox("कोणत्या वर्षाचा हिशोब पाहायचा आहे?", [curr_y, 2026, 2027], index=0)
        
        # जर २०२६ निवडले तर सुरुवात ऑगस्टपासून, २०२७ ला जानेवारीपासून
        default_start_idx = 7 if selected_year == 2026 else 0
        from_month = col_s2.selectbox("सुरुवातीचा महिना:", MONTHS_LIST, index=default_start_idx)
        
        # चालू महिना डीफॉल्ट ठेवणे
        curr_m_idx = datetime.now().month - 1
        upto_month = col_s3.selectbox("शेवटचा महिना:", MONTHS_LIST, index=curr_m_idx)

        from_idx = MONTHS_LIST.index(from_month)
        upto_idx = MONTHS_LIST.index(upto_month) + 1
        
        # तपासण्याचे महिने
        months_to_check = [f"{m} {selected_year}" for m in MONTHS_LIST[from_idx:upto_idx]]

        df_paid = pd.read_sql_query("SELECT flat_no, month_year, amount FROM maintenance_received", conn)
        dues_report = []
        total_society_dues = 0.0

        for _, flat in df_flats.iterrows():
            f_no = flat["flat_no"]
            owner = flat["owner_name"]
            contact = flat["contact"] or "-"
            rate = float(flat["monthly_maint"])

            flat_receipts = df_paid[df_paid["flat_no"] == f_no]
            paid_months = flat_receipts["month_year"].unique().tolist()

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
        df = pd.read_sql_query("""
            SELECT m.id, m.flat_no as 'फ्लॅट क्र.', f.owner_name as 'सभासदाचे नाव', 
                   m.month_year as 'महिना/वर्ष', m.amount as 'जमा रक्कम (₹)', 
                   m.payment_mode as 'पद्धत', m.payment_date as 'पावती तारीख', m.remark as 'रिमार्क'
            FROM maintenance_received m
            LEFT JOIN flats f ON m.flat_no = f.flat_no
            ORDER BY m.payment_date DESC
        """, conn)
        st.dataframe(df, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Maintenance')
        st.download_button("📥 मेंटेनन्स अहवाल Excel डाउनलोड करा", out.getvalue(), "Maintenance_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif rep_choice == "२. संपूर्ण खर्च अहवाल (Expenses Report)":
        df = pd.read_sql_query("""
            SELECT id, title as 'खर्चाचे नाव', category as 'प्रवर्ग', amount as 'रक्कम (₹)', 
                   expense_date as 'तारीख', paid_to as 'कोणास दिले', payment_mode as 'पेमेंट पद्धत', remark as 'रिमार्क'
            FROM expenses ORDER BY expense_date DESC
        """, conn)
        st.dataframe(df, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')
        st.download_button("📥 खर्च अहवाल Excel डाउनलोड करा", out.getvalue(), "Expenses_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
    elif rep_choice == "३. एकत्रित ताळेबंद / नफा-तोटा (Profit & Loss Summary)":
        df_m = pd.read_sql_query("SELECT SUM(amount) as total_maint FROM maintenance_received", conn)
        df_e = pd.read_sql_query("SELECT SUM(amount) as total_exp FROM expenses", conn)
        tm = df_m['total_maint'].iloc[0] or 0.0
        te = df_e['total_exp'].iloc[0] or 0.0
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

conn.close()
