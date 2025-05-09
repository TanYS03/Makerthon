import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pymongo import MongoClient
import random
import datetime
# from streamlit_autorefresh import st_autorefresh

# Set page configuration
st.set_page_config(
    page_title="Waste Management Admin Dashboard",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)
# st_autorefresh(interval=5000, key="auto_refresh")

# Database setup and connection
client = MongoClient("mongodb+srv://easontan7285:nb2XBcriGVzT2QhF@cluster0.u7gxoah.mongodb.net/?tls=true")
db = client["smartbin"]

# Collections
dustbin_col = db["dustbins"]
notification_col = db["notification"]
collect_rubbish_col = db["collectRubbish"]
useraccount_col = db["userAccount"]
rubbish_col = db["rubbish"]

dustbin_df = pd.DataFrame(list(dustbin_col.find()))
notification_df = pd.DataFrame(list(notification_col.find()))
collect_rubbish_df = pd.DataFrame(list(collect_rubbish_col.find()))
useraccount_df = pd.DataFrame(list(useraccount_col.find()))
rubbish_df = pd.DataFrame(list(rubbish_col.find()))

# Sidebar
st.sidebar.title("Admin Controls")

# Sidebar - Filter options
st.sidebar.header("Filters")

status_filter = st.sidebar.multiselect(
    "Select Bin Status",
    options=["Empty", "Half-Full", "Full", "Low"],
)

# Sidebar - Add new dustbin address
st.sidebar.header("Add New Dustbin Location")
with st.sidebar.form("new_address_form"):
    new_location = st.text_input("Location")
    new_dustbin_id = st.text_input("Dustbin ID")
    new_status = "Empty" 

    submit_button = st.form_submit_button("Add Dustbin")

    if submit_button:
        if new_location and new_dustbin_id:
            # Optional: Prevent duplicates
            if (dustbin_col.find_one({"dustbin_id": new_dustbin_id}) or dustbin_col.find_one({"location": new_location})):
                st.warning("Dustbin ID already exists!")
            else:
                dustbin_col.insert_one({
                    "dustbin_id": new_dustbin_id,
                    "status": new_status,
                    "location": new_location
                })
                st.success("New dustbin location added successfully!")
                st.rerun()
        else:
            st.error("Please fill in both Dustbin ID and Location.")

# Main dashboard
st.title("🗑️ Waste Management Admin Dashboard")

st.markdown("---")

# Tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dustbin Location", "Notifications", "Reward Calculator", "History", "Smartbin Installation Order"])

# Tab 1: Address List
with tab1:

    if not dustbin_df.empty:
        # Optional formatting
        dustbin_df.rename(columns={
            'dustbin_id': 'Dustbin ID',
            'status': 'Status',
            'location': 'Location',
            'type': 'Type'
        }, inplace=True)

        # Separate full bins
        full_bins = dustbin_df[dustbin_df['Status'].str.lower() == 'full']
        waste_bins = dustbin_df[dustbin_df['Type'].str.lower() == 'waste']
        recycle_bins = dustbin_df[dustbin_df['Type'].str.lower() == 'recycle']

        # Display full bins
        st.subheader("⚠️ Full Dustbins")
        # Apply status filter (Empty, Half, Full)
        if status_filter:
            full_bins = full_bins[full_bins['Status'].isin(status_filter)]
        st.dataframe(full_bins[['Dustbin ID', 'Location', 'Status']], use_container_width=True)

        # Display
        st.subheader("♻ Recycle Waste")
        if status_filter:
            recycle_bins = recycle_bins[recycle_bins['Status'].isin(status_filter)]
        st.dataframe(recycle_bins[['Dustbin ID', 'Location', 'Status']], use_container_width=True)

        # Display 
        st.subheader("✅ Normal Waste")
        if status_filter:
            waste_bins = waste_bins[waste_bins['Status'].isin(status_filter)]
        st.dataframe(waste_bins[['Dustbin ID', 'Location', 'Status']], use_container_width=True)
        
    else:
        st.info("No dustbin records found in database.")

# Tab 2: Notifications
with tab2:
    st.header("Notifications")
    
    if not notification_df.empty:
        # Display notifications
        uncollected_df = notification_df[notification_df['isCollected'] == False]

        if not uncollected_df.empty:
            st.subheader("Notification Records")
            display_df = uncollected_df.copy()
            display_df = display_df.drop(['_id', 'isCollected'], axis=1, errors='ignore')
            display_df.columns = ['Dustbin ID', 'Location', 'Time', 'Notification Type']
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("All recycle items have been collected.")
    else:
        st.info("No notifications available.")

# Tab 3: Recycling Calculator
with tab3:
    st.header("Recycling Value Calculator")
    
   # Input section: Admin updates prices and weight input
    st.subheader("Input Rubbish Data")

    total_weight = 0
    total_value = 0
    chart_data = []
    updated_prices = {}

    if not rubbish_df.empty:
        for index, row in rubbish_df.iterrows():
            rubbish_type = row["type"]
            default_price = row["price"]

            st.markdown(f"### {rubbish_type}")
            col1, col2 = st.columns(2)

            with col1:
                weight = st.number_input(
                    f"{rubbish_type} Weight (kg)",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    key=f"{rubbish_type}_weight"
                )

            with col2:
                price = st.number_input(
                    f"{rubbish_type} Price ($/kg)",
                    min_value=0.01,
                    value=default_price,
                    step=0.01,
                    key=f"{rubbish_type}_price"
                )
                updated_prices[rubbish_type] = price

            value = weight * price
            total_weight += weight
            total_value += value

            if weight > 0:
                chart_data.append({
                    "Rubbish Type": rubbish_type,
                    "Weight (kg)": weight,
                    "Value ($)": value
                })

        # Submit Button for MongoDB update
        if st.button("Submit Price Updates"):
            for rubbish_type, new_price in updated_prices.items():
                rubbish_col.update_one(
                    {"type": rubbish_type},
                    {"$set": {"price": new_price}}
                )
            st.success("Prices updated successfully.")
    else:
        st.info("No rubbish types available.")

    st.markdown("---")
    st.subheader("Calculation Results")
    st.info(f"**Total Weight**: {total_weight:.2f} kg\n\n**Total Value**: ${total_value:.2f}")

    if not useraccount_df.empty and not notification_df.empty:
        # Step 1: Get uncollected dustbin IDs from notifications
        uncollected_dustbins = notification_df[notification_df["isCollected"] == False]["dustbin_id"].unique()

        # Step 2: Filter user accounts whose dustbin_id is in the uncollected list
        filtered_users = useraccount_df[useraccount_df["dustbin_id"].isin(uncollected_dustbins)]

        if not filtered_users.empty:
            with st.form("reward_form"):
                # Dropdown with filtered owner names
                owner_names = filtered_users["owner_name"].tolist()
                selected_owner = st.selectbox("Select Owner", ["-- Select Owner --"] + owner_names)

                # Show total value to be added
                st.markdown(f"**Total Reward to Add**: ${total_value:.2f}")

                # Submit button (MUST be inside the form)
                submitted = st.form_submit_button("Submit Reward")

                if submitted and selected_owner != "-- Select Owner --":
                    # Fetch user from MongoDB and update total_reward
                    user_doc = useraccount_col.find_one({"owner_name": selected_owner})
                    if user_doc:
                        current_reward = user_doc.get("total_reward", 0)
                        new_reward = current_reward + total_value

                        useraccount_col.update_one(
                            {"owner_name": selected_owner},
                            {"$set": {"total_reward": new_reward}}
                        )

                        notification_col.update_one(
                            {"dustbin_id": user_doc["dustbin_id"], "isCollected": False},
                            {"$set": {"isCollected": True}}
                        )

                        dustbin_col.update_one(
                            {"dustbin_id": user_doc["dustbin_id"]},
                            {"$set": {"status": 'Empty'}}
                        )

                        for entry in chart_data:
                            collect_rubbish_col.insert_one({
                                "dustbin_id": user_doc["dustbin_id"],
                                "timestamp": datetime.datetime.now(),
                                "rubbish_type": entry["Rubbish Type"],
                                "weight": entry["Weight (kg)"],
                                "price": entry["Value ($)"]
                            })

                        st.success(f"Reward of ${total_value:.2f} added to {selected_owner}. New Total: ${new_reward:.2f}")
                    else:
                        st.error("Selected owner not found in database.")
                elif submitted:
                    st.warning("Please select an owner before submitting.")
        else:
            st.info("No matching users found with uncollected dustbins.")
    else:
        st.info("No user accounts or notifications available.")

    if chart_data:
        chart_df = pd.DataFrame(chart_data)
        fig = px.bar(
            chart_df,
            x="Rubbish Type",
            y="Value ($)",
            color="Rubbish Type",
            title="Recycling Value by Rubbish Type",
            hover_data=["Weight (kg)"]
        )
        st.plotly_chart(fig, use_container_width=True)

# Tab 4: History (formerly Completion Tracker)
with tab4:
    st.header("Recycle History")
    
    col1, col2 = st.columns(2)
    
    if not collect_rubbish_df.empty:
        # Show full collection history
        st.subheader("Collection Records")
        display_df = collect_rubbish_df.copy()
        display_df = display_df.drop(['_id', 'image'], axis=1, errors='ignore')
        display_df.columns = ['Dustbin ID', 'Time', 'Rubbish Type', 'Weight (kg)', 'Price (RM)']
        st.dataframe(display_df, use_container_width=True)

        # Rubbish type weight summary
        st.subheader("Total Weight by Rubbish Type")

        weight_summary = collect_rubbish_df.groupby("rubbish_type")["weight"].sum().reset_index()
        weight_summary.columns = ["Rubbish Type", "Total Weight (kg)"]

        fig = px.bar(
            weight_summary,
            x="Rubbish Type",
            y="Total Weight (kg)",
            title="Total Weight Collected per Rubbish Type",
            color="Rubbish Type",
            text="Total Weight (kg)"
        )
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rubbish collection data available.")

# Tab 5: Product
with tab5:
    st.header("Smartbin Installation Order")

    # Product info
    product_name = "Smart Recycling Dustbin"
    product_description = "This smart dustbin comes with a built-in ultrasonic sensor to detect fullness level and notifies admin when it needs to be collected. Eco-friendly and IoT-integrated."

    # Layout
    col1, col2 = st.columns([1, 2])

    # Product Image
    with col1:
        st.image("images.jpeg", width=300, caption=product_name)

    # Product Details and Quantity Selector
    with col2:
        st.subheader(product_name)
        st.write(product_description)
        st.markdown("**Price:** $120.00")

        # Quantity Control
        if "quantity" not in st.session_state:
            st.session_state.quantity = 1

        col_inc, col_q, col_dec = st.columns([1, 2, 1])

        with col_dec:
            if st.button("➖"):
                if st.session_state.quantity > 1:
                    st.session_state.quantity -= 1

        with col_q:
            st.markdown(f"<h3 style='text-align: center;'>{st.session_state.quantity}</h3>", unsafe_allow_html=True)

        with col_inc:
            if st.button("➕"):
                st.session_state.quantity += 1

        # Add to Cart or Confirm
        if st.button("Add to Order"):
            st.success(f"{st.session_state.quantity} unit(s) of '{product_name}' added to your order.")


   
# Footer
st.markdown("---")
st.caption("Waste Management Admin Dashboard | Last updated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))