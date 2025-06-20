from sqlalchemy import create_engine, text, update, MetaData, Table
import streamlit as st
import pandas as pd


@st.cache_resource
def get_connection():
    # Connect to Neon PostgreSQL
    return create_engine(st.secrets["db_connection"])


# Load current data
@st.cache_data(ttl=300)  # cache results for 5 minutes
def load_data():
    engine = get_connection()
    query = "SELECT * FROM transactions ORDER BY id"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def new_stock_to_db(engine, owner, stock, price_buy, date_buy, price_sell, date_sell, currency):
    if owner and stock and price_buy > 0 and date_buy:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO transactions (owner, stock, price_buy, date_buy, price_sell, date_sell, currency)
                VALUES (:owner, :stock, :price_buy, :date_buy, :price_sell, :date_sell, :currency)
            """), {
                "owner": owner,
                "stock": stock,
                "price_buy": price_buy,
                "date_buy": date_buy,
                "price_sell": price_sell,
                "date_sell": date_sell,
                "currency": currency
            })
        st.success("Transaction added.")
        st.session_state.show_form = False
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Please fill all fields.")


def close_stock(engine, owner, stock, price_sell, date_sell):
    if owner and stock and price_sell > 0 and date_sell:
        metadata = MetaData()
        transactions_table = Table("transactions", metadata, autoload_with=engine)
        with engine.connect() as conn:
            stmt = (
                update(transactions_table)
                .where(
                    (transactions_table.c.stock == stock) &
                    (transactions_table.c.owner == owner) &
                    (transactions_table.c.date_sell == None)
                )
                .values(
                    price_sell=price_sell,
                    date_sell=date_sell
                )
            )
            conn.execute(stmt)
            conn.commit()
            st.success("Transaction closed!")
            st.session_state.show_form2 = False
            st.cache_data.clear()
            st.rerun()
    else:
        st.error("Please fill all fields.")
