from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from datetime import datetime
import re

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def convert_date(date_str):
    """Convert various date formats to YYYY-MM-DD."""
    date_str = str(date_str).strip()
    date_formats = ["%d-%m-%Y", "%m-%d-%Y", "%d-%m-%y", "%Y-%m-%d"]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None  # Return None if no format matches

def clean_amount(amount):
    """Convert amount to float and remove non-numeric characters."""
    amount = str(amount).lower().replace(",", "").strip()
    amount = re.sub(r"[^\d.]", "", amount)
    return float(amount) if amount else None

def process_statement(input_path, output_path):
    """Standardizes the bank statement."""
    try:
        # Read CSV file
        df = pd.read_csv(input_path)

        # Debugging: Print detected column names
        print("Detected Columns:", df.columns.tolist())

        # Drop unnamed columns
        df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]

        # Ensure all column names are strings
        df.columns = df.columns.astype(str).str.strip()

        # Convert all columns to string type to prevent .str errors
        df = df.astype(str)

        # Find transaction column dynamically
        transaction_col = next((col for col in df.columns if "transaction" in col.lower()), None)

        if not transaction_col:
            return f"Error: No valid transaction column found. Detected columns: {df.columns.tolist()}"

        # Extract transactions from detected column
        df["Date"] = df[transaction_col].str.extract(r'(\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2})')
        df["Transaction Description"] = df[transaction_col].str.replace(r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}', '', regex=True).str.extract(r'([\w\s]+)')
        df["Amount"] = df[transaction_col].str.extract(r'([\d,]+\.\d{2})')

        # Convert formats
        df["Date"] = df["Date"].apply(convert_date)
        df["Amount"] = df["Amount"].apply(clean_amount)

        # Drop NaN values (rows where no transaction was extracted)
        df = df.dropna(subset=["Date", "Transaction Description", "Amount"])

        # Save cleaned output
        df.to_csv(output_path, index=False)
        return None

    except Exception as e:
        return str(e)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            filename = file.filename
            
            # Ensure it's a CSV file
            if not filename.endswith(".csv"):
                return "Error: Please upload a CSV file."

            input_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Construct output filename by replacing "Input" with "Output"
            output_filename = filename.replace("Input", "Output")
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            # Save uploaded file
            file.save(input_path)

            # Process file
            error = process_statement(input_path, output_path)
            if error:
                return f"Error processing file: {error}"

            return send_file(output_path, as_attachment=True, download_name=output_filename)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
