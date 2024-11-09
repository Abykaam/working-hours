from flask import Flask, render_template, request, send_file
import pandas as pd
import os
import csv

app = Flask(__name__)

# Ensure a folder for saving uploaded and generated files
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def txt_to_csv(input_txt_file, output_csv_file):
    """Convert a .txt file to a .csv file"""
    with open(input_txt_file, mode='r') as file:
        lines = file.readlines()

    # Strip leading/trailing whitespace and split by tabs for each line
    header = lines[0].strip().split('\t')  # First line is the header
    rows = [line.strip().split('\t') for line in lines[1:]]  # Remaining lines are data

    # Write the output to a CSV file
    with open(output_csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header row
        writer.writerows(rows)  # Write the data rows

def time_to_hours_minutes(decimal_hours):
    """Convert decimal hours to hours:minutes format"""
    hours = int(decimal_hours)
    minutes = round((decimal_hours - hours) * 60)
    return f"{hours} hours {minutes} minute"  # Format as "X hours Y minute"

def process_input_table(input_data):
    """Process the log data from a text file"""
    # Convert .txt data into DataFrame and calculate attendance
    lines = input_data.strip().split('\n')
    
    # Split the first line for headers
    headers = lines[0].strip().split()  # Split by space
    
    # Process the rest of the data, splitting by space
    data = [line.strip().split() for line in lines[1:]]
    
    # Create a DataFrame
    df = pd.DataFrame(data, columns=headers)
    
    # Convert Log Date to datetime and handle the "Device id" column
    df["Log Date"] = pd.to_datetime(df["Log Date"])
    
    # Sort data by "Log Date"
    df = df.sort_values(by="Log Date")

    # Calculate the working hours per day
    df["Date"] = df["Log Date"].dt.date
    df["Time"] = df["Log Date"].dt.time
    
    # Use 'Punch In' and 'Punch Out' instead of 'min' and 'max'
    grouped = df.groupby("Date")["Log Date"].agg(["min", "max"])
    
    # Rename 'min' and 'max' columns to 'Punch In' and 'Punch Out'
    grouped.rename(columns={"min": "Punch In", "max": "Punch Out"}, inplace=True)

    # Calculate the difference in time for working hours
    grouped["Hours Worked"] = (grouped["Punch Out"] - grouped["Punch In"]).dt.total_seconds() / 3600

    # Convert decimal hours to hours:minutes format
    grouped["Hours Worked (HH:MM)"] = grouped["Hours Worked"].apply(time_to_hours_minutes)

    return df, grouped

@app.route('/', methods=['GET', 'POST'])
def index():
    tables = None
    total_hours = None
    total_hours_formatted = '0 hours 0 minute'  # Default value to prevent UnboundLocalError

    if request.method == 'POST':
        if 'txtFile' in request.files:
            txt_file = request.files['txtFile']
            if txt_file and txt_file.filename.endswith('.txt'):
                # Save the uploaded .txt file
                input_txt_file = os.path.join(UPLOAD_FOLDER, txt_file.filename)
                txt_file.save(input_txt_file)

                # Convert the .txt file to .csv
                output_csv_file = os.path.join(OUTPUT_FOLDER, 'Attendance.csv')
                try:
                    txt_to_csv(input_txt_file, output_csv_file)
                    return send_file(output_csv_file, as_attachment=True)

                except Exception as e:
                    return f"<p>Error processing data: {e}</p>"
        
        elif 'csvFile' in request.files:
            csv_file = request.files['csvFile']
            if csv_file and csv_file.filename.endswith('.csv'):
                # Read the uploaded CSV file
                df = pd.read_csv(csv_file)
                
                # Perform calculations or attendance logic
                df["Log Date"] = pd.to_datetime(df["Log Date"])
                df["Date"] = df["Log Date"].dt.date
                df["Time"] = df["Log Date"].dt.time
                
                # Use 'Punch In' and 'Punch Out' instead of 'min' and 'max'
                grouped = df.groupby("Date")["Log Date"].agg(["min", "max"])

                # Rename 'min' and 'max' columns to 'Punch In' and 'Punch Out'
                grouped.rename(columns={"min": "Punch In", "max": "Punch Out"}, inplace=True)

                # Calculate the difference in time for working hours
                grouped["Hours Worked"] = (grouped["Punch Out"] - grouped["Punch In"]).dt.total_seconds() / 3600
                
                # Convert decimal hours to hours:minutes format for each day
                grouped["Hours Worked (HH:MM)"] = grouped["Hours Worked"].apply(time_to_hours_minutes)

                # Example: Assuming `grouped["Hours Worked"].sum()` gives a decimal value
                total_hours1 = grouped["Hours Worked"].sum()

                # Format the total hours worked in hours and minutes format
                total_hours_formatted = time_to_hours_minutes(total_hours1)
                total_hours = total_hours_formatted

                tables = grouped.to_html(classes='table table-bordered', header=True, index=True)

    return render_template('index.html', tables=tables, total_hours=total_hours, total_hours_formatted=total_hours_formatted)

# if __name__ == '__main__':
#     app.run(debug=True)
