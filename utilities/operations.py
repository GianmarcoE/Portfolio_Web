import datetime
import requests
import json
import pandas as pd
import plotly.graph_objects as go
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

    # Get unique tickers for open positions
    open_tickers = df.loc[open_mask, "ticker"].unique()

    if len(open_tickers) == 0:
        return df

    try:
        # Single API call to fetch all current prices
        current_prices = yf.download(
            tickers=list(open_tickers),
            period="1d",
            group_by="ticker",
            auto_adjust=True,
            prepost=True,
            threads=True
        )

        # Extract the most recent close price for each ticker
        ticker_prices = {}

        if len(open_tickers) == 1:
            # Single ticker case - data structure is different
            ticker = open_tickers[0]
            if not current_prices.empty and "Close" in current_prices.columns:
                ticker_prices[ticker] = current_prices["Close"].iloc[-1]
        else:
            # Multiple tickers case
            for ticker in open_tickers:
                try:
                    if ticker in current_prices.columns.get_level_values(0):
                        close_data = current_prices[ticker]["Close"]
                        if not close_data.empty:
                            ticker_prices[ticker] = close_data.iloc[-1]
                except (KeyError, IndexError):
                    print(f"Could not extract price for {ticker}")
                    continue

        # Update dataframe with fetched prices
        for ticker, current_price in ticker_prices.items():
            stock_mask = (df["ticker"] == ticker) & open_mask
            df.loc[stock_mask, "total_sell"] = current_price * df.loc[stock_mask, "quantity_buy"]
            df.loc[stock_mask, "earning"] = round(df.loc[stock_mask, "total_sell"] - df.loc[stock_mask, "total_buy"], 2)
            df.loc[stock_mask, "date_sell"] = datetime.date.today()
            df.loc[stock_mask, "earning"] = df.apply(lambda row: convert_to_eur(row, "earning", "date_sell"), axis=1)
            df.loc[stock_mask, "date_sell"] = "OPEN"

        # Report any tickers that couldn't be fetched
        failed_tickers = set(open_tickers) - set(ticker_prices.keys())
        for ticker in failed_tickers:
            print(f"Could not fetch price for {ticker}")

    except Exception as e:
        print(f"Error fetching prices: {e}")
        # Fallback to original method if bulk fetch fails
        for ticker in open_tickers:
            try:
                current_price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
                stock_mask = (df["ticker"] == ticker) & open_mask
                df.loc[stock_mask, "total_sell"] = current_price * df.loc[stock_mask, "quantity_buy"]
                df.loc[stock_mask, "earning"] = round(
                    df.loc[stock_mask, "total_sell"] - df.loc[stock_mask, "total_buy"], 2)
                df.loc[stock_mask, "date_sell"] = datetime.date.today()
                df.loc[stock_mask, "earning"] = df.apply(lambda row: convert_to_eur(row, "earning", "date_sell"),
                                                         axis=1)
                df.loc[stock_mask, "date_sell"] = "OPEN"
            except Exception as ticker_error:
                print(f"Could not fetch price for {ticker}: {ticker_error}")

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

    fig = go.Figure()

    # Add bar trace with modern styling
    fig.add_trace(go.Bar(
        x=stocks['label'],
        y=stocks['earning'],
        # Modern color scheme
        marker=dict(
            color=color,  # Modern indigo color
            line=dict(width=0),  # Remove border
            # This creates rounded corners - adjust the radius as needed
            cornerradius=8
        ),
        text=stocks['earning'],
        textposition='outside',  # Position text outside/above the bars
        # Make bars thinner
        width=0.4,  # Adjust this value (0.1 to 1.0) to control bar thickness
        textfont=dict(color='white', size=12, family='Arial')
    ))

    # Update layout for modern appearance
    fig.update_layout(
        title=dict(
            text=graph_title,
            x=0.35,  # Center the title
            font=dict(size=15, family='Arial', color='#b8b6b6')
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,  # Hide Y-axis scale numbers
            range=[graph_range[0], graph_range[1]],
            visible=False  # Completely hide Y-axis
        ),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(family='Arial', color='#1f2937'),
        margin=dict(l=40, r=40, t=60, b=50),
        height=300,
        width=300,
        showlegend=False
    )
    return fig


def badges(bcolor, color, text):
    # Create HTML badge instead of st.badge
    html_badge = f"""
                       <span style="
                           background-color: {bcolor};
                           color: {color};
                           padding: 4px 8px;
                           border-radius: 8px;
                           font-size: 14px;
                           font-weight: bold;
                           margin-left: 8px;
                           margin-top: 8px;
                           display: inline;
                           white-space: nowrap;
                           vertical-align: middle;
                       ">{text}</span>
                       """
    return html_badge
