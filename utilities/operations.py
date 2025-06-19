import requests
import json
import pandas as pd
from sqlalchemy import create_engine, text, update, MetaData, Table
import streamlit as st


# Load current data
def load_data():
    # Connect to Neon PostgreSQL
    engine = create_engine(st.secrets["db_connection"])
    query = "SELECT * FROM transactions ORDER BY id"
    return pd.read_sql(query, engine), engine


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
            st.rerun()
    else:
        st.error("Please fill all fields.")


def api_request_fx(currency, transaction_date) -> float:
    try:
        url = f'https://api.frankfurter.dev/v1/{transaction_date}?symbols={currency}'
        r = requests.get(url)
        parsed = json.loads(r.text)
        response = parsed['rates']
        fx_rate = list(response.values())[0]
        return fx_rate
    except Exception as e:
        print(f'Error fetching exchange rate: {str(e)}')


def convert_to_eur(row, price, date):
    if row["currency"] != "EUR" and not pd.isna(row[date]):
        return row[price] / api_request_fx(row["currency"], row[date])
    return row[price]


# class Stocks:
#     def __init__(self, owner, name, open_date, closing_date, open_price, closing_price):
#         self.owner = owner
#         self.name = name
#         self.open_date = open_date
#         self.closing_date = closing_date
#         self.open_price = open_price
#         self.closing_price = closing_price
