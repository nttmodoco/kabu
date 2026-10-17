#!/usr/bin/env python3
"""analyze.py - 毎日実行される株価分析スクリプト"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

WATCHLIST = {
    "7203.T": "トヨタ",
    "9984.T": "ソフトバンクG",
    "6758.T": "ソニー",
    "AAPL": "Apple",
    "NVDA": "NVIDIA",
}

def analyze():
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for ticker, name in WATCHLIST.items():
        try:
            df = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)
            if df.empty:
                continue
            
            close = df["Close"]
            current = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            change_1d = (current / prev - 1) * 100
            change_1m = (current / close.iloc[-22] - 1) * 100 if len(close) > 22 else 0
            
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
            
            rsi_delta = close.diff()
            gain = rsi_delta.clip(lower=0).rolling(14).mean()
            loss = (-rsi_delta.clip(upper=0)).rolling(14).mean()
            rsi = float(100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1])))
            
            signal = []
            if current > ma20:
                signal.append("MA20上")
            if rsi < 30:
                signal.append("RSI売られすぎ")
            elif rsi > 70:
                signal.append("RSI買われすぎ")
            
            results.append({
                "date": today, "ticker": ticker, "name": name,
                "price": round(current, 2),
                "change_1d": round(change_1d, 2),
                "change_1m": round(change_1m, 2),
                "ma20": round(ma20, 2),
                "rsi": round(rsi, 1),
                "signals": ", ".join(signal) if signal else "なし"
            })
        except Exception as e:
            print(f"エラー {ticker}: {e}")
    
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    
    # 結果をJSONで保存
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    df_results.to_json(f"{output_dir}/{today}.json", orient="records", force_ascii=False)
    df_results.to_csv(f"{output_dir}/latest.csv", index=False, encoding="utf-8-sig")
    print(f"\n分析完了: {len(results)}銘柄 ({today})")
    return df_results

if __name__ == "__main__":
    analyze()
