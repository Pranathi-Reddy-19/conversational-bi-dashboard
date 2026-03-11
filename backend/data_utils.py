import pandas as pd
import io
import re

def detect_header_row(uploaded_file_bytes, encoding):
    sample = pd.read_csv(io.BytesIO(uploaded_file_bytes), header=None, nrows=10, encoding=encoding)
    best_row = 0
    max_text = 0
    for i, row in sample.iterrows():
        text_count = sum(isinstance(x, str) for x in row)
        if text_count > max_text:
            max_text = text_count
            best_row = i
    return best_row

def clean_uploaded_csv(file_bytes):
    raw = file_bytes
    encodings = ["utf-8", "latin1", "cp1252", "utf-16"]
    text = None

    for enc in encodings:
        try:
            text = raw.decode(enc)
            break
        except:
            continue

    if text is None:
        text = raw.decode("utf-8", errors="ignore")

    match = re.search(r"<pre.*?>(.*?)</pre>", text, re.DOTALL)
    if match:
        text = match.group(1)

    csv_data = io.StringIO(text)
    sample = pd.read_csv(csv_data, header=None, nrows=10)
    best_row = 0
    max_text = 0
    for i, row in sample.iterrows():
        text_count = sum(isinstance(x, str) for x in row)
        if text_count > max_text:
            max_text = text_count
            best_row = i

    csv_data.seek(0)
    df = pd.read_csv(csv_data, header=best_row)
    df = df.dropna(how="all")
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.columns = df.columns.astype(str).str.replace(r"[^\x00-\x7F]+", "", regex=True)
    return df

def clean_column_names(df):
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("[^a-zA-Z0-9_]", "", regex=True)
    )
    return df

def generate_schema(df):
    schema_lines = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        try:
            unique_cnt = df[col].nunique()
        except Exception:
            unique_cnt = 0

        if "int" in dtype or "float" in dtype:
            sql_type = "INTEGER" if "int" in dtype else "FLOAT"
            try:
                min_val = df[col].min()
                max_val = df[col].max()
                if pd.isna(min_val) or pd.isna(max_val):
                    profile = f"Type: {sql_type}, Uniques: {unique_cnt}"
                else:
                    if "float" in dtype:
                        profile = f"Type: {sql_type}, Uniques: {unique_cnt}, Min: {min_val:.2f}, Max: {max_val:.2f}"
                    else:
                        profile = f"Type: {sql_type}, Uniques: {unique_cnt}, Min: {min_val}, Max: {max_val}"
            except Exception:
                profile = f"Type: {sql_type}, Uniques: {unique_cnt}"
        else:
            sql_type = "TEXT"
            if unique_cnt <= 5 and unique_cnt > 0:
                try:
                    examples = df[col].dropna().unique().tolist()
                    examples_str = ", ".join(f"'{str(x)}'" for x in examples)
                    profile = f"Type: {sql_type}, Uniques: {unique_cnt}, Values: [{examples_str}]"
                except Exception:
                    profile = f"Type: {sql_type}, Uniques: {unique_cnt}"
            else:
                profile = f"Type: {sql_type}, Uniques: {unique_cnt}"

        schema_lines.append(f"- {col} ({profile})")

    return "\n".join(schema_lines)

def generate_kpi_cards(df):
    try:
        numeric_df = df.select_dtypes(include=['number'])
    except:
        return [{"label": "Total Records", "value": f"{len(df):,}"}]

    if numeric_df.empty:
        return [{"label": "Total Records", "value": f"{len(df):,}"}]

    targets = [
        {"keys": ["rev", "sale", "prof", "amt", "tot"], "label": "Revenue", "func": "sum", "prefix": "$"},
        {"keys": ["click", "visit", "view", "user", "traff"], "label": "Clicks", "func": "sum", "prefix": ""},
        {"keys": ["roi", "marg", "rate", "perc", "conv"], "label": "Avg ROI", "func": "mean", "prefix": ""},
    ]

    found_metrics = []
    used_cols = set()

    for t in targets:
        matched = False
        k_list = t.get("keys", [])
        for col_val in numeric_df.columns:
            col_str = str(col_val)
            if col_str in used_cols: 
                continue
            if any(k in col_str.lower() for k in k_list):
                val_obj = numeric_df[col_val].sum() if t.get("func") == "sum" else numeric_df[col_val].mean()
                try:
                    val = float(val_obj)
                except:
                    val = 0.0

                prefix = str(t.get("prefix", ""))
                suffix = "%" if ("roi" in " ".join(k_list) or "rate" in " ".join(k_list)) and abs(val) < 1000 else ""

                if val >= 1_000_000:
                    formatted = f"{prefix}{val/1_000_000:.2f}M{suffix}"
                elif val >= 1_000:
                    formatted = f"{prefix}{val/1_000:.2f}K{suffix}"
                else:
                    formatted = f"{prefix}{val:.2f}{suffix}"

                found_metrics.append({"label": str(t.get("label", "")), "value": formatted})
                used_cols.add(col_str)
                matched = True
                break

        if not matched:
            for col_val in numeric_df.columns:
                col_str = str(col_val)
                if col_str not in used_cols:
                    val_obj = numeric_df[col_val].sum() if t.get("func") == "sum" else numeric_df[col_val].mean()
                    try:
                        val = float(val_obj)
                    except:
                        val = 0.0

                    lbl = str(t.get("label", "")) if t.get("func") == "mean" else f"Tot {col_str[:10].title()}"
                    prefix = str(t.get("prefix", ""))

                    if val >= 1_000_000:
                        formatted = f"{prefix}{val/1_000_000:.2f}M"
                    elif val >= 1_000:
                        formatted = f"{prefix}{val/1_000:.2f}K"
                    else:
                        formatted = f"{prefix}{val:.2f}"

                    found_metrics.append({"label": lbl, "value": formatted})
                    used_cols.add(col_str)
                    break 

    if not found_metrics:
        found_metrics.append({"label": "Total Records", "value": f"{len(df):,}"})
    return found_metrics
