import streamlit as st
import sqlite3
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Member Data Portal", page_icon="🔍", layout="wide")

# Connect to the SQLite Database
@st.cache_resource
def get_connection():
    return sqlite3.connect('members.db', check_same_thread=False)

conn = get_connection()

# Navigation
page = st.sidebar.radio("Navigation", ["🔍 Search Database", "✏️ Update / Add Members"])

if page == "🔍 Search Database":
    st.title("🔍 Member Data Search Portal")
    st.markdown("Search and filter the member database.")

    # Fetch unique values for dropdowns
    def get_unique_values(column_name):
        try:
            query = f"SELECT DISTINCT {column_name} FROM members WHERE {column_name} IS NOT NULL ORDER BY {column_name}"
            return pd.read_sql(query, conn)[column_name].tolist()
        except:
            return []

    # Define sidebar filters
    st.sidebar.header("Filter Options")
    search_term = st.sidebar.text_input("Search (Name, Member No, etc.)", "")
    
    sex_options = ["All"] + get_unique_values('SEX')
    selected_sex = st.sidebar.selectbox("Filter by SEX", sex_options)
    
    status_options = ["All"] + get_unique_values('status')
    selected_status = st.sidebar.selectbox("Filter by Status", status_options)

    # Build the SQL Query dynamically
    query = "SELECT * FROM members WHERE 1=1"
    params = []

    if search_term:
        query += " AND (FullNames LIKE ? OR memberNo LIKE ? OR SN LIKE ?)"
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term, like_term])

    if selected_sex != "All":
        query += " AND SEX = ?"
        params.append(selected_sex)

    if selected_status != "All":
        query += " AND status = ?"
        params.append(selected_status)

    query += " LIMIT 1000"

    # Fetch Data
    with st.spinner('Fetching data...'):
        df_results = pd.read_sql(query, conn, params=params)

    st.subheader(f"Results: {len(df_results)} records found" + (" (Showing top 1000)" if len(df_results) == 1000 else ""))

    if not df_results.empty:
        st.dataframe(df_results, use_container_width=True, hide_index=True)
    else:
        st.info("No records found matching your search criteria.")

elif page == "✏️ Update / Add Members":
    st.title("✏️ Update or Add Members")
    st.markdown("Use this interface to add new members or edit existing records in the database.")
    
    # Let user search a specific member to edit
    st.subheader("Edit Existing Records")
    edit_search = st.text_input("Search member to edit (by Name or Member No):")
    
    if edit_search:
        edit_query = "SELECT * FROM members WHERE FullNames LIKE ? OR memberNo LIKE ? LIMIT 50"
        edit_params = [f"%{edit_search}%", f"%{edit_search}%"]
        df_edit = pd.read_sql(edit_query, conn, params=edit_params)
        
        if not df_edit.empty:
            st.write("Edit the data in the table below and click 'Save Changes' at the bottom.")
            # Use data_editor to allow inline editing
            edited_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
            
            if st.button("💾 Save Changes to Database"):
                try:
                    # To keep it simple, we delete the old rows we just searched for, 
                    # and insert the new edited rows in their place.
                    cursor = conn.cursor()
                    
                    # 1. Delete original records that were in df_edit
                    # Assuming memberNo or SN is somewhat unique, but safer to match exact rows if no primary key.
                    # Since data is messy, we'll just delete based on old SN and MemberNo.
                    for _, row in df_edit.iterrows():
                        cursor.execute("DELETE FROM members WHERE SN=? AND memberNo=? AND FullNames=?", 
                                       (row['SN'], row['memberNo'], row['FullNames']))
                    
                    # 2. Insert the new edited_df
                    edited_df.to_sql('members', conn, if_exists='append', index=False)
                    conn.commit()
                    st.success("✅ Changes successfully saved to the database!")
                except Exception as e:
                    st.error(f"Error saving changes: {e}")
        else:
            st.warning("No members found to edit.")
            
    st.divider()
    
    st.subheader("Add a New Member Manually")
    with st.form("add_member_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_sn = st.text_input("SN (Serial Number)")
            new_memberno = st.text_input("Member No")
            new_name = st.text_input("Full Names")
            new_dob = st.date_input("Date of Birth (DOB)")
            new_sex = st.selectbox("SEX", ["M", "F"])
        with col2:
            new_expiry = st.date_input("Expiry Date")
            new_reg = st.date_input("Registration Date")
            new_status = st.selectbox("Status", ["Single", "Married", "Divorced", "Widow", "Separated"])
            new_emp = st.text_input("Employment Type", "Permanent")
        with col3:
            new_rel = st.text_input("Relationship", "Parent")
            new_photo = st.text_input("Photo ID")
            new_payroll = st.text_input("Payroll Number")
            new_spouse = st.text_input("Spouse Address")
            
        submitted = st.form_submit_button("➕ Add Member")
        if submitted:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO members (
                        SN, memberNo, FullNames, DOB, SEX, Expirydate, 
                        registrationdate, photo, status, "payroll number", 
                        employmenttype, spouseAddress, relationship
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_sn, new_memberno, new_name, str(new_dob), new_sex, 
                    str(new_expiry), str(new_reg), new_photo, new_status, 
                    new_payroll, new_emp, new_spouse, new_rel
                ))
                conn.commit()
                st.success(f"✅ Successfully added {new_name} to the database!")
            except Exception as e:
                st.error(f"Error adding member: {e}")
