import datetime

import requests
import json
from datetime import date
import pandas as pd
import plotly.express as px
import yfinance as yf


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


def api_current_price(df):
    # Identify open transactions (no sell date)
    open_mask = df["date_sell"].isna()
    today = "OPEN"

    # For each unique open stock, fetch current price and assign today's date
    for ticker in df.loc[open_mask, "ticker"].unique():
        try:
            current_price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
            # Update price and date in df_display
            stock_mask = (df["ticker"] == ticker) & open_mask
            df.loc[stock_mask, "total_sell"] = current_price * df.loc[stock_mask, "quantity_buy"]
            df.loc[stock_mask, "earning"] = round(df.loc[stock_mask, "total_sell"] - df.loc[stock_mask, "total_buy"], 2)
            df.loc[stock_mask, "date_sell"] = datetime.date.today()
            df.loc[stock_mask, "earning"] = df.apply(lambda row: convert_to_eur(row, "earning", "date_sell"), axis=1)
            df.loc[stock_mask, "date_sell"] = today
        except Exception as e:
            print(f"Could not fetch price for {ticker}: {e}")
    return df


def convert_to_eur(row, price, date):
    if row["currency"] != "EUR" and not pd.isna(row[date]):
        row[date] = datetime.date.today()
        return round(row[price] / api_request_fx(row["currency"], row[date]), 2)
    return round(row[price], 2)


def top_worst_graph(is_top, stocks, color, graph_title):
    if is_top:
        max_value = stocks["earning"].max()
        graph_range = [0, max_value * 1.2]
    else:
        max_value = stocks["earning"].min()
        graph_range = [max_value * 1.2, 0]
    fig = px.bar(
        stocks,
        x='label',
        y='earning',
        text='earning',
        color_discrete_sequence=[color],
        title=graph_title
    )

    fig.update_traces(
                      texttemplate='€ %{text:.2f}',
                      marker_line_width=0,  # remove white border
                      marker_line_color='rgba(0,0,0,0)',
                      textposition='outside',
                      width=0.4,
                      )

    fig.update_layout(
                      xaxis_title='',
                      yaxis_title='',
                      height=280,
                      margin=dict(t=60),
                      showlegend=False,
                      xaxis=dict(showgrid=False),
                      yaxis=dict(showgrid=False, range=[graph_range[0], graph_range[1]]),
                      )
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    return fig
