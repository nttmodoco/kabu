#!/usr/bin/env python3
"""analyze.py - 毎日実行される株価分析スクリプト"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

WATCHLIST = {
    "7203.T": "トヨタ",
    "9984.T": "ソフトバンクG",
    "6758.T": "ソニー",
    "AAPL": "Apple",
    "NVDA": "NVIDIA",
}


def analyze():
    results = []
    daily_records = []
    errors = []
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).resolve().parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    for ticker, name in WATCHLIST.items():
        try:
            df = yf.download(
                ticker,
                period="1mo",
                interval="1d",
                progress=False,
                auto_adjust=True,
                actions=False,
            )

            if df is None or df.empty:
                errors.append({
                    "date": today,
                    "ticker": ticker,
                    "name": name,
                    "error": "取得データなし",
                })
                continue

            if "Close" not in df.columns:
                errors.append({
                    "date": today,
                    "ticker": ticker,
                    "name": name,
                    "error": "Close列が存在しません",
                })
                continue

            close = df["Close"].dropna()
            if close.empty:
                errors.append({
                    "date": today,
                    "ticker": ticker,
                    "name": name,
                    "error": "Closeデータなし",
                })
                continue

            for date, value in close.items():
                daily_records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "name": name,
                    "close": round(float(value), 2),
                })

            current = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) > 1 else current
            change_1d = (current / prev - 1) * 100 if prev else 0.0
            change_1m = (current / close.iloc[0] - 1) * 100 if len(close) > 1 else 0.0

            ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else float(close.mean())
            ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None

            rsi_delta = close.diff()
            gain = rsi_delta.clip(lower=0).rolling(14).mean()
            loss = (-rsi_delta.clip(upper=0)).rolling(14).mean()
            last_loss = float(loss.iloc[-1]) if len(loss) > 0 else 0.0
            last_gain = float(gain.iloc[-1]) if len(gain) > 0 else 0.0
            rsi = 50.0
            if last_loss > 0:
                rsi = float(100 - (100 / (1 + last_gain / last_loss)))
            elif last_gain > 0:
                rsi = 100.0

            signal = []
            if current > ma20:
                signal.append("MA20上")
            if rsi < 30:
                signal.append("RSI売られすぎ")
            elif rsi > 70:
                signal.append("RSI買われすぎ")

            results.append({
                "date": today,
                "ticker": ticker,
                "name": name,
                "price": round(current, 2),
                "change_1d": round(change_1d, 2),
                "change_1m": round(change_1m, 2),
                "ma20": round(ma20, 2),
                "ma50": round(ma50, 2) if ma50 is not None else None,
                "rsi": round(rsi, 1),
                "signals": ", ".join(signal) if signal else "なし",
            })

        except Exception as exc:
            errors.append({
                "date": today,
                "ticker": ticker,
                "name": name,
                "error": str(exc),
            })
            print(f"エラー {ticker}: {exc}")

    df_results = pd.DataFrame(results)
    daily_output = {
        "generated_at": today,
        "period": "1mo",
        "interval": "1d",
        "records": daily_records,
        "errors": errors,
    }

    json_path = output_dir / f"{today}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(daily_output, f, ensure_ascii=False, indent=2)

    if not df_results.empty:
        df_results.to_csv(output_dir / "latest.csv", index=False, encoding="utf-8-sig")
        print(df_results.to_string(index=False))
    else:
        print("取得できた銘柄データはありませんでした。")

    print(f"\n分析完了: {len(results)}銘柄成功 / {len(errors)}件失敗 ({today})")
    print(f"出力先: {json_path}")
    return df_results


if __name__ == "__main__":
    analyze()
