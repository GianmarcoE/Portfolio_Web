from sqlalchemy import create_engine, text, update, MetaData, Table
import streamlit as st
import pandas as pd


def get_connection():
    # Connect to Neon PostgreSQL
    return create_engine(st.secrets["db_connection"])


# Load current data
@st.cache_data(ttl=300)  # cache results for 5 minutes
def load_data(_engine):
    query = "SELECT * FROM transactions ORDER BY id"
    df = pd.read_sql(query, _engine)
    return df


def new_stock_to_db(engine, owner, stock, price_buy, date_buy, quantity_buy,
                    price_sell, date_sell, quantity_sell, currency, ticker, dividends):
    if owner and stock and price_buy > 0 and date_buy:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO transactions (owner, stock, ticker, price_buy, date_buy, quantity_buy,
                                          price_sell, date_sell, quantity_sell, currency, dividends)
                VALUES (:owner, :stock, :ticker, :price_buy, :date_buy, :quantity_buy,
                        :price_sell, :date_sell, :quantity_sell, :currency, :dividends)
            """), {
                "owner": owner,
                "stock": stock,
                "ticker": ticker,
                "price_buy": price_buy,
                "date_buy": date_buy,
                "quantity_buy": quantity_buy,
                "price_sell": price_sell,
                "date_sell": date_sell,
                "quantity_sell": quantity_sell,
                "currency": currency,
                "dividends": dividends
            })
        st.success("Transaction added.")
        st.session_state.show_form = False
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Please fill all fields.")


def close_stock(engine, owner, stock, price_sell, date_sell, quantity_sell, dividends):
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
                    quantity_sell=quantity_sell,
                    date_sell=date_sell,
                    dividends=dividends
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


def delete_stock(engine, record_id):
    """
    Deletes a record from the specified table based on its ID.

    Parameters:
        engine: SQLAlchemy engine connected to your Neon database.
        record_id (int or str): ID of the record to delete.
    """
    with engine.connect() as conn:
        query = text(f"DELETE FROM transactions WHERE id = :id")
        conn.execute(query, {"id": record_id})
        conn.commit()


def add_etf(engine, selected_owner, selected_stock, new_price, new_qty):
    if selected_owner and selected_stock and new_price > 0 and new_qty > 0:
        metadata = MetaData()
        transactions_table = Table("transactions", metadata, autoload_with=engine)
        avg = ((transactions_table.c.price_buy * transactions_table.c.quantity_buy) +
               (new_price * new_qty)) / (transactions_table.c.quantity_buy + new_qty)
        with engine.connect() as conn:
            stmt = (
                update(transactions_table)
                .where(
                    (transactions_table.c.stock == selected_stock) &
                    (transactions_table.c.owner == selected_owner) &
                    (transactions_table.c.date_sell == None)
                )
                .values(
                    price_buy=avg,
                    quantity_buy=transactions_table.c.quantity_buy + new_qty,
                )
            )
            conn.execute(stmt)
            conn.commit()
            st.success("ETF buying added")
    else:
        st.error("Please fill all fields.")


