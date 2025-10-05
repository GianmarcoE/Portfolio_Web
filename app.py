import streamlit as st
import datetime
import pandas as pd
from utilities import operations, db_operations


# Cache database operations
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_cached_data():
    """Load data from database with caching"""
    engine = db_operations.get_connection()
    df = db_operations.load_data(engine)
    df = df[~df['date_sell'].astype(str).str.contains('2024')]
    return df


@st.cache_data(ttl=600)  # Cache for 10 minute
def get_current_prices(df_filtered):
    """Get current prices with caching"""
    if df_filtered.empty:
        return df_filtered
    return operations.api_current_price(df_filtered.copy())


@st.cache_data
def calculate_metrics(df, include_dividends=True):
    """Calculate derived columns with caching"""
    df = df.copy()
    # Add calculation columns
    df["total_buy"] = df["price_buy"] * df["quantity_buy"]
    df["total_sell"] = df["price_sell"] * df["quantity_sell"] + df['dividends']
    if not include_dividends:
        df["total_sell"] = df["price_sell"] * df["quantity_sell"]
    df["earning"] = df["total_sell"] - df["total_buy"]

    # Convert earnings to EUR
    usd_rate, pln_rate = operations.today_rate()
    df["earning"] = df.apply(lambda row: operations.convert_open_to_eur(row, "earning", "date_sell", usd_rate, pln_rate)
                             , axis=1)
    return df


@st.cache_data
def calculate_owner_stats(df):
    """Calculate statistics for each owner"""
    stats = {}

    for owner in df["owner"].unique():
        owner_df = df[df["owner"] == owner].copy()

        # Closed positions only for most metrics
        closed_df = owner_df[owner_df["date_sell"].notna()]
        open_df = owner_df[owner_df["date_sell"].isna()]

        # Total earnings (closed positions)
        total_earnings = closed_df["earning"].sum() if not closed_df.empty else 0

        # Average position holding time (closed positions only)
        if not closed_df.empty:
            closed_df["date_buy"] = pd.to_datetime(closed_df["date_buy"])
            closed_df["date_sell"] = pd.to_datetime(closed_df["date_sell"])
            closed_df["holding_days"] = (closed_df["date_sell"] - closed_df["date_buy"]).dt.days
            avg_holding_days = closed_df["holding_days"].mean()
        else:
            avg_holding_days = 0

        # Number of transactions
        total_transactions = len(closed_df)
        open_positions = len(open_df)

        # Win rate
        winning_trades = len(closed_df[closed_df["earning"] > 0])
        win_rate = (winning_trades / total_transactions * 100) if total_transactions > 0 else 0

        # Best and worst trade
        best_trade = closed_df["earning"].max() if not closed_df.empty else 0
        worst_trade = closed_df["earning"].min() if not closed_df.empty else 0

        stats[owner] = {
            "total_earnings": total_earnings,
            "avg_holding_days": avg_holding_days,
            "total_transactions": total_transactions,
            "open_positions": open_positions,
            "win_rate": win_rate,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        }

    return stats


def create_daily_cumulative(df):
    """Create daily cumulative data"""
    daily = df.groupby(["owner", "date_sell"])["earning"].sum().reset_index()
    daily = daily.sort_values(["owner", "date_sell"])
    daily["cumulative"] = daily.groupby("owner")["earning"].cumsum()
    return daily


def clear_cache():
    """Clear all cached data"""
    st.cache_data.clear()


st.set_page_config(layout="wide")
col1, col2 = st.columns(2)
with col1:
    st.title("Trading Portfolio")
with col2:
    # Create custom CSS for right-aligned button
    st.markdown("""
                <style>
                div.stButton > button {
                    float: right;
                }
                </style>
                """, unsafe_allow_html=True)
    if st.button("🔄 Refresh Data"):
        clear_cache()
        st.rerun()
st.write("")
st.write("")

today = datetime.date.today()

# Load data with caching
df = load_cached_data()
owners = df["owner"].unique().tolist()

col1, col2 = st.columns([2, 1])  # col1 is twice as wide
with col1:
    with st.expander("Settings ⚙️", expanded=False):
        st.caption("Owners Selection")
        cols = st.columns(len(owners))
        selected_owners = [
            owner for col, owner in zip(cols, owners)
            if col.checkbox(owner, value=True, key=f"chk_{owner}")
        ]
        st.caption("Others")
        col_1, col_2 = st.columns(2)
        with col_1:
            include_dividends = st.checkbox("Include dividends", value=True, key="include_dividends")
        with col_2:
            include_open = st.checkbox("Include open positions", value=False, key="include_open")

    st.write("")

# Calculate metrics with caching
df_with_metrics = calculate_metrics(df, include_dividends)

# Calculate owner statistics
owner_stats = calculate_owner_stats(df_with_metrics)

badge_1 = operations.badges('#189e25', 'white', '👑 King Fiches')
badge_2 = operations.badges('#7a0b6f', 'white', '🏃‍♂️ Chaser')
badge_3 = operations.badges('#9e1e18', 'white', '💩 Loser')
badges = [badge_1, badge_2, badge_3]

# Get top 3 earners sorted by total_earnings (descending)
top_3_earners = sorted(owner_stats.items(),
                       key=lambda x: x[1]['total_earnings'],
                       reverse=True)[:3]

# Assign badges to top 3 earners
for i, (owner_name, owner_data) in enumerate(top_3_earners):
    owner_stats[owner_name]['badge'] = badges[i]

# Display owner cards
if selected_owners:
    st.subheader("📊 Owner Performance Summary")

    # Create cards for selected owners
    cards_per_row = 3
    rows_needed = (len(selected_owners) + cards_per_row - 1) // cards_per_row

    for row in range(rows_needed):
        cols = st.columns(cards_per_row + 1)
        for i in range(cards_per_row):
            owner_idx = row * cards_per_row + i
            if owner_idx < len(selected_owners):
                owner = selected_owners[owner_idx]
                stats = owner_stats[owner]

                with cols[i]:
                    # Create card styling
                    earnings_color = "green" if stats["total_earnings"] >= 0 else "#d61111"
                    worst_color = "green" if stats["worst_trade"] >= 0 else "#d61111"

                    st.markdown(f"""
                    <div style="
                        border: 1px solid #ddd;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 10px 0;
                        background-color: #222;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <h3 style="margin-top: 0; color: #b8b6b6;">👤 {owner} {stats['badge']}</h3>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <div><strong>💰 Total Earnings:</strong> 
                                <span style="color: {earnings_color}">€{stats['total_earnings']:.2f}</span>
                            </div>
                            <div><strong>📅 Avg. Hold Time:</strong> {stats['avg_holding_days']:.0f} days</div>
                            <div><strong>🎯 Win Rate:</strong> {stats['win_rate']:.1f}%</div>
                            <div><strong>📊 Transactions:</strong> {stats['total_transactions']} closed, {stats['open_positions']} open</div>
                            <div><strong>🏆 Best Trade:</strong> <span style="color: green">€{stats['best_trade']:.2f}</span></div>
                            <div><strong>📉 Worst Trade:</strong> <span style="color: {worst_color}">€{stats['worst_trade']:.2f}</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.write("")

# Filter data
filtered_df = df_with_metrics[df_with_metrics["owner"].isin(selected_owners)] if selected_owners else pd.DataFrame()

# Get current prices only when needed and cache the result
if not filtered_df.empty:
    open_df = get_current_prices(filtered_df)
    closed_transactions = open_df[open_df["date_sell"] != "OPEN"]
    # Show top and worst transactions (only calculate when we have data)
    # if not closed_transactions.empty:
    top_3 = closed_transactions.nlargest(3, 'earning')[['owner', 'stock', 'earning']]
    top_3['label'] = top_3['owner'] + ' - ' + top_3['stock']
    worst_3 = closed_transactions.nsmallest(3, 'earning')[['owner', 'stock', 'earning']]
    worst_3['label'] = worst_3['owner'] + ' - ' + worst_3['stock']

    fig_best = operations.top_worst_graph(True, top_3, 'green', 'Best transactions')
    fig_worst = operations.top_worst_graph(False, worst_3, '#d61111', 'Worst transactions')
    fig_ring = operations.ring_chart(closed_transactions)

    # Handle open positions for chart
    if include_open:
        filtered_df_3 = open_df.copy()
        filtered_df_3.loc[open_df["date_sell"] == "OPEN", "date_sell"] = today
        chart_data = filtered_df_3
    else:
        chart_data = filtered_df

    # Create chart data
    daily = create_daily_cumulative(chart_data)
    chart_df = daily.pivot(index="date_sell", columns="owner", values="cumulative").ffill()

    with col1:
        st.markdown("Total Earnings")
        st.line_chart(chart_df)

        with st.expander("Show all transactions details", expanded=False):
            st.dataframe(open_df.drop(columns=["quantity_buy", "price_sell", "quantity_sell"]),
                         hide_index=True, column_config=
                         {
                             "owner": st.column_config.TextColumn("Owner"),
                             "stock": st.column_config.TextColumn("Stock"),
                             "ticker": st.column_config.TextColumn("Ticker"),
                             "price_buy": st.column_config.NumberColumn("Buy Price"),
                             "total_buy": st.column_config.NumberColumn("Buy tot", format="%.2f"),
                             "date_buy": st.column_config.DateColumn("Buy Date"),
                             "total_sell": st.column_config.NumberColumn("Sell tot", format="%.2f"),
                             "date_sell": st.column_config.DateColumn("Sell Date"),
                             "currency": st.column_config.TextColumn("Currency"),
                             "dividends": st.column_config.NumberColumn("Dividends", format="%.2f"),
                             "earning": st.column_config.NumberColumn("Earnings", format="%.2f €"),
                         }
                         )
        st.write("")

    with col2:
        st.plotly_chart(fig_best, use_container_width=True)
        st.write("")
        st.plotly_chart(fig_worst, use_container_width=True)
        # st.write("")
        # st.plotly_chart(fig_ring, use_container_width=True)
else:
    st.info("Select at least one owner to view data.")

# Session state to track button click
if "active_form" not in st.session_state:
    st.session_state.active_form = None


def toggle_form(form_name):
    if st.session_state.active_form == form_name:
        st.session_state.active_form = None  # Close if already open
    else:
        st.session_state.active_form = form_name  # Open the new form


# Button to show the form
with col1:
    col_1, col_2, col_3 = st.columns([1, 1, 1], gap="small")
    with col_1:
        if st.button("➕ Add transaction", use_container_width=True):
            toggle_form("A")

    with col_2:
        if st.button("✔️ Modify open position", use_container_width=True):
            toggle_form("B")

    with col_3:
        if st.button("❌ Delete record", use_container_width=True):
            toggle_form("C")

# Display form if button1 clicked
with col1:
    if st.session_state.active_form == "A":
        st.subheader("New Transaction")

        # Initialize session state for sold checkbox if not exists
        if 'sold_checkbox' not in st.session_state:
            st.session_state.sold_checkbox = False

        # Checkbox outside form with session state
        sold = st.checkbox("Has this stock been sold?", key='sold_checkbox')

        with st.form("form_a"):
            owner = st.selectbox("Select Owner", df["owner"].unique())
            stock = st.text_input("Stock")
            ticker = st.text_input("Ticker (e.g. TSLA)")
            price_buy = st.number_input("Stock buy price", step=0.001)
            quantity_buy = st.number_input("Q.ty", step=0.01)
            date_buy = st.date_input("Date buy", value=today)
            currency = st.selectbox("Currency", ["EUR", "USD", "PLN"])

            # Initialize default values
            price_sell = None
            date_sell = None
            quantity_sell = None
            dividends = 0

            # Show additional fields based on session state
            if st.session_state.sold_checkbox:
                price_sell = st.number_input("Stock sale price", step=0.001)
                quantity_sell = st.number_input("Q.ty sold", step=0.01)
                date_sell = st.date_input("Date sold", value=today)
                dividends = st.number_input("Dividends received", step=0.01)

            if st.form_submit_button("Submit"):
                engine = db_operations.get_connection()
                db_operations.new_stock_to_db(engine, owner, stock, price_buy, date_buy, quantity_buy,
                                              price_sell, date_sell, quantity_sell, currency, ticker, dividends)
                clear_cache()  # Clear cache after adding new data
                st.success("Transaction added successfully!")
                # Reset the checkbox after successful submission
                st.session_state.sold_checkbox = False

    elif st.session_state.active_form == "B":
        # SOLUTION 1: Move the owner selection outside the form
        st.subheader("Modify open position")

        action = st.radio("", ("Close transaction", "Additional Purchase"))

        if action == "Close transaction":
            selected_owner = st.selectbox("Select Owner", df["owner"].unique(), key="close_owner_select")

            # Filter open positions for that owner
            open_stocks = df[(df["owner"] == selected_owner) & (df["date_sell"].isna())]

            if not open_stocks.empty:
                with st.form("form_b"):
                    # Create selectbox of stock names
                    selected_stock = st.selectbox("Select open stock", open_stocks["stock"].unique())
                    price_sell = st.number_input("Sell Price", step=0.001)
                    quantity_sell = st.number_input("Q.ty", step=0.01)
                    date_sell = st.date_input("Date sold", value=today)
                    dividends = st.number_input("Dividends received", step=0.01)

                    if st.form_submit_button("Submit"):
                        engine = db_operations.get_connection()
                        db_operations.close_stock(engine, selected_owner, selected_stock, price_sell, date_sell,
                                                  quantity_sell, dividends)
                        clear_cache()  # Clear cache after closing position
                        st.success("Position closed successfully!")
        else:
            selected_owner = st.selectbox("Select Owner", df["owner"].unique(), key="close_owner_select")

            # Filter open positions for that owner
            open_stocks = df[(df["owner"] == selected_owner) & (df["date_sell"].isna())]
            if not open_stocks.empty:
                with st.form("form_b"):
                    # Create selectbox of stock names
                    selected_stock = st.selectbox("Select open stock", open_stocks["stock"].unique())
                    new_price = st.number_input("Buy Price", step=0.001)
                    new_qty = st.number_input("Q.ty", step=0.01)

                    if st.form_submit_button("Submit"):
                        engine = db_operations.get_connection()
                        db_operations.add_etf(engine, selected_owner, selected_stock, new_price, new_qty)
                        clear_cache()  # Clear cache after closing position

    elif st.session_state.active_form == "C":
        with st.form("form_c"):
            st.subheader("Delete record")
            delete_id = st.number_input("Record ID", step=1)

            if st.form_submit_button("Submit"):
                engine = db_operations.get_connection()
                db_operations.delete_stock(engine, delete_id)
                clear_cache()  # Clear cache after deleting record
                st.success("Record deleted successfully!")

with cols[-1]:
    st.plotly_chart(fig_ring, use_container_width=True)
