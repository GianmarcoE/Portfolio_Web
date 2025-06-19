import streamlit as st
import pandas as pd
import datetime
from utilities import operations


# UI
st.title("Transactions List")
st.write("")
st.write("")

df, engine = operations.load_data()
df = df.drop(columns=["id"])

df["earning"] = df["price_sell"] - df["price_buy"]

# convert earnings to EUR
df["earning"] = df.apply(lambda row: operations.convert_to_eur(row, "earning", "date_sell"), axis=1)

daily = df.groupby(["owner", "date_sell"])["earning"].sum().reset_index()

# Cumulative sum
daily = daily.sort_values(["owner", "date_sell"])
daily["cumulative"] = daily.groupby("owner")["earning"].cumsum()

# Let user select owners
owners = df["owner"].unique().tolist()
cols = st.columns(len(owners))

selected_owners = [
    owner for col, owner in zip(cols, owners)
    if col.checkbox(owner, value=True, key=f"chk_{owner}")
]
st.write("")

# Filter both the chart and the table
filtered_df = df[df["owner"].isin(selected_owners)] if selected_owners else pd.DataFrame()

# Chart: recompute from filtered_df
if not filtered_df.empty:
    daily = (
        filtered_df.groupby(["owner", "date_sell"])["earning"]
        .sum()
        .reset_index()
        .sort_values(["owner", "date_sell"])
    )
    daily["cumulative"] = daily.groupby("owner")["earning"].cumsum()
    chart_df = daily.pivot(index="date_sell", columns="owner", values="cumulative").ffill()

    st.markdown("Total Earnings (closed positions)")
    st.line_chart(chart_df)
    with st.expander("Show transactions", expanded=False):
        st.dataframe(filtered_df, hide_index=True, column_config=
        {
            "owner": st.column_config.TextColumn("Owner"),
            "stock": st.column_config.TextColumn("Stock"),
            "price_buy": st.column_config.NumberColumn("Buy", format="%.2f"),
            "date_buy": st.column_config.DateColumn("Buy Date"),
            "price_sell": st.column_config.NumberColumn("Sell", format="%.2f"),
            "date_sell": st.column_config.DateColumn("Sell Date"),
            "currency": st.column_config.TextColumn("Currency"),
            "earning": st.column_config.NumberColumn("Earnings", format="%.2f €"),
        }
                     )
else:
    st.info("Select at least one owner to view data.")

# Show filtered data


# Session state to track button click
if "show_form" not in st.session_state:
    st.session_state.show_form = False

if "show_form2" not in st.session_state:
    st.session_state.show_form2 = False

# Button to show the form
if st.button("➕ Add transaction"):
    st.session_state.show_form = not st.session_state.show_form

if st.button("✔️ Close open transaction"):
    st.session_state.show_form2 = not st.session_state.show_form2

# Display form if button1 clicked
if st.session_state.show_form:
    st.subheader("New Transaction")
    owner = st.selectbox("Select Owner", df["owner"].unique())
    stock = st.text_input("Stock")
    price_buy = st.number_input("Price buy", step=0.01)
    date_buy = st.date_input("Date buy", value=datetime.date.today())
    currency = st.selectbox("Currency", ["EUR", "USD", "PLN"])
    sold = st.checkbox("Has this stock been sold?")
    price_sell = None
    date_sell = None
    if sold:
        price_sell = st.number_input("Price sell", step=0.01)
        date_sell = st.date_input("Date sold", value=datetime.date.today())

    if st.button("Submit"):
        operations.new_stock_to_db(engine, owner, stock, price_buy, date_buy, price_sell, date_sell, currency)

if st.session_state.show_form2:
    st.subheader("Close open position")
    owner = st.selectbox("Select Owner", df["owner"].unique())
    # Filter open positions for that owner
    open_stocks = df[(df["owner"] == owner) & (df["date_sell"].isna())]

    # Create selectbox of stock names (or IDs, if you have those)
    selected_stock = st.selectbox("Select open stock", open_stocks["stock"].unique())

    price_sell = st.number_input("Sell Price", step=0.01)
    date_sell = st.date_input("Date sold", value=datetime.date.today())

    if st.button("Submit"):
        operations.close_stock(engine, owner, selected_stock, price_sell, date_sell)
