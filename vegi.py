import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# Daily_Collection DataFrame from previous version
Daily_Collection = pd.DataFrame({
    "Collection Date": [
        "2025-09-06", "2025-09-06", "2025-09-06", "2025-09-06",
        "2025-09-06", "2025-09-06", "2025-09-05"
    ],
    "Vehicle No": [
        "JH03AS-8355", "JH03A5-0918", "JH03A5-0920", "JH03A5-0921",
        "JH03A5-0919", "JH03A5-0922", "JH03A5-0922"
    ],
    "Amount": [0, 300, 0, 300, 300, 300, 300],
    "Meter Reading": [13700, 5019, 1501, 5008, 2937, 3207, 3116],
    "Name": [
        "Kamesh", "Pankaj", "Zero Collection", "GK",
        "Satyendra", "Rijwan Ansari", "Satyendra"
    ],
    "Distance": [0, 100, 0, 77, 112, 91, 24],
    "Previous Amount": [300, 300, 0, 0, 0, 300, 350]
})

# Recent_Collection DataFrame from the latest query
Recent_Collection = pd.DataFrame({
    "Collection Date": [
        "2025-09-06", "2025-09-06", "2025-09-06", "2025-09-05",
        "2025-09-05", "2025-09-04", "2025-09-04", "2025-09-03"
    ],
    "Vehicle No": [
        "JH03AS-8355", "JH03A5-0918", "JH03A5-0920", "JH03B6-1234",
        "JH03C7-5678", "JH03D8-9012", "JH03E9-3456", "JH03F0-7890"
    ],
    "Amount": [0, 300, 0, 500, 150, 250, 0, 400],
    "Distance": [0, 100, 0, 120, 50, 80, 0, 95],
    "Name": [
        "Kamesh", "Pankaj", "Zero Collection", "Rajesh",
        "Priya", "Amit", "Zero Collection", "Sunil"
    ]
})

# Sort and keep latest 8 records for Recent_Collection
Recent_Collection = Recent_Collection.sort_values(
    by="Collection Date", ascending=False
).head(8)

# HTML + CSS for both sets of cards
html_content = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap');

.card-container {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: flex-start;
    align-items: flex-start;
}
.card {
    background: linear-gradient(135deg, #2a9d8f, #264653); /* New background color */
    border-radius: 12px;
    padding: 12px;
    color: #000000; /* Text color is now black by default */
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
    width: 160px; /* New width */
    height: 95px; /* New height */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    font-family: 'Poppins', sans-serif;
    position: relative;
    overflow: hidden;
}
.card::before {
    content: '';
    position: absolute;
    top: -10px;
    left: -10px;
    width: 30px;
    height: 30px;
    background: #ffffff30;
    border-radius: 50%;
    transform: scale(0);
    transition: transform 0.4s ease;
}
.card:hover::before {
    transform: scale(20);
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 18px rgba(0, 0, 0, 0.35);
}

.vehicle-no {
    font-size: 1.1em;
    font-weight: 600;
    margin-bottom: 5px;
    z-index: 1;
    color: #ffffff; /* Vehicle number remains white */
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    z-index: 1;
}

.date, .meter-reading-header {
    font-size: 0.7em;
    font-weight: 600;
    opacity: 1;
    z-index: 1;
}

.info-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: auto; /* Pushes this section to the bottom */
}

.info-left, .info-right {
    display: flex;
    flex-direction: column;
    font-size: 0.75em;
    z-index: 1;
}
.info-value {
    font-weight: 600;
}
.info-value.name {
    text-align: right;
}
</style>

<div class="card-container">
"""

# Add each row from Daily_Collection as a card
html_content += "<h2>Daily Collection</h2>"
for index, row in Daily_Collection.iterrows():
    html_content += f"""
    <div class="card">
        <div class="vehicle-no">{row['Vehicle No']}</div>
        <div class="card-header">
            <div class="date">{row['Collection Date']}</div>
            <div class="meter-reading-header">{row['Meter Reading']} Km</div>
        </div>
        <div class="info-row">
            <div class="info-left">
                <div class="info-value" >₹ {row['Amount']}</div>
                <div class="info-value">{row['Distance']} km</div>
            </div>
            <div class="info-right">
                <div class="info-value name">{row['Name']}</div>
            </div>
        </div>
    </div>
    """

# Add each row from Recent_Collection as a card
html_content += "<h2>Recent Collection</h2>"
for _, row in Recent_Collection.iterrows():
    # Note: Recent_Collection does not have a "Meter Reading" column, so we exclude it.
    html_content += f"""
        <div class="card">
            <div class="vehicle-no">{row['Vehicle No']}</div>
            <div class="card-header">
                <div class="date">{row['Collection Date']}</div>
            </div>
            <div class="info-row">
                <div class="info-left">
                    <div class="info-value">₹ {row['Amount']}</div>
                    <div class="info-value">{row['Distance']} km</div>
                </div>
                <div class="info-right">
                    <div class="info-value name">{row['Name']}</div>
                </div>
            </div>
        </div>
    """

html_content += "</div>"

# Render HTML
components.html(html_content, height=600, scrolling=False)
