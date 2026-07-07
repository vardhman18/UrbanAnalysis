import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import pydeck as pdk

data = {
    'City': ['NEW YORK NY', 'CHICAGO IL', 'LOS ANGELES CA', 'MIAMI FL', 'SILICON VALLEY', 
             'ORANGE COUNTY', 'SAN DIEGO CA', 'PHOENIX AZ', 'DALLAS TX', 'ATLANTA GA', 
             'DENVER CO', 'AUSTIN TX', 'SEATTLE WA', 'TUCSON AZ', 'SAN FRANCISCO CA', 
             'SACRAMENTO CA', 'PITTSBURGH PA', 'WASHINGTON DC', 'NASHVILLE TN', 'BOSTON MA'],
    'Latitude': [40.7128, 41.8781, 34.0522, 25.7617, 37.3875, 
                 33.7175, 32.7157, 33.4484, 32.7767, 33.4484, 
                 39.7392, 30.2672, 47.6062, 32.2226, 37.7749, 
                 38.5816, 40.4406, 38.9072, 36.1627, 42.3601],
    'Longitude': [-74.0060, -87.6298, -118.2437, -80.1918, -122.0575, 
                  -117.8311, -117.1611, -112.0740, -96.7970, -84.3870, 
                  -104.9903, -97.7431, -122.3321, -110.9747, -122.4194, 
                  -121.4944, -79.9959, -77.0369, -86.7816, -71.0589]
}

cities_df = pd.DataFrame(data)

st.set_page_config(page_title='Cab Data Analysis', layout='wide')

@st.cache_data
def load_data():
    cab_data = pd.read_csv('Cab_Data.csv')
    city_data = pd.read_csv('City.csv')
    customer_data = pd.read_csv('Customer_ID.csv')
    transaction_data = pd.read_csv('Transaction_ID.csv')
    return cab_data, city_data, customer_data, transaction_data

cab_data, city_data, customer_data, transaction_data = load_data()

cab_data['Date of Travel'] = pd.to_datetime(cab_data['Date of Travel'], errors='coerce', origin='1899-12-30')

merged_data = cab_data.merge(transaction_data, on='Transaction ID', how='left')
merged_data = merged_data.merge(customer_data, on='Customer ID', how='left')
merged_data = merged_data.merge(city_data, on='City', how='left')

st.markdown("""
    <style>
    [data-testid="stSidebar"] img {
        background: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        border-radius: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.sidebar.image("logo cab3.png", use_column_width=True)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Visualization", "Map View", "Insights & Reports"])

if page == "Home":
    st.title('Urban Mobility Analysis')
    st.header("Key Metrics:")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trips", f"{len(merged_data)}")
    col2.metric("Total Revenue ($)", f"{merged_data['Price Charged'].sum():,.2f}")
    col3.metric("Average Distance (km)", f"{merged_data['KM Travelled'].mean():.2f}")
    st.markdown("---")
    st.write("Use the navigation panel to explore different aspects of the dataset.")

elif page == "Visualization":
    st.title("Data Visualization")
    
    st.sidebar.header("Filter Options")
    
    selected_city = st.sidebar.multiselect("Select City:", merged_data['City'].unique(), default=merged_data['City'].unique())
    selected_company = st.sidebar.multiselect("Select Cab Company:", merged_data['Company'].unique(), default=merged_data['Company'].unique())
    selected_payment = st.sidebar.multiselect("Select Payment Mode:", merged_data['Payment_Mode'].unique(), default=merged_data['Payment_Mode'].unique())
    
    st.markdown("### Selected Filters")
    def format_selection(selection, all_options):
        return "All" if set(selection) == set(all_options) else ", ".join(selection)

    st.write(f"**Selected City:** {format_selection(selected_city, merged_data['City'].unique())}")
    st.write(f"**Selected Cab Company:** {format_selection(selected_company, merged_data['Company'].unique())}")
    st.write(f"**Selected Payment Mode:** {format_selection(selected_payment, merged_data['Payment_Mode'].unique())}")
    
    st.markdown("### Visualization Settings")
    x_axis = st.selectbox("Select X-axis:", ['City', 'Company', 'Payment_Mode', 'Gender', 'Age'])
    hue_axis = st.selectbox("Select Hue (Category Split):", ['Company', 'Payment_Mode', 'Gender', 'City'])
    
    filtered_data = merged_data[
        (merged_data['City'].isin(selected_city)) &
        (merged_data['Company'].isin(selected_company)) &
        (merged_data['Payment_Mode'].isin(selected_payment))
    ]
    
    def plotting_count(x: str, hue: str):
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.set_theme(style='darkgrid')
        ordering = filtered_data[x].value_counts()
        sns.countplot(data=filtered_data, x=x, hue=hue, order=ordering.index[::-1], palette='viridis')
        ax.tick_params(axis='x', rotation=45)
        ax.set_title(f'Count Plot of {x} by {hue}', fontsize=18)
        ax.set_xlabel(x, fontsize=14)
        ax.set_ylabel('Count', fontsize=14) 
        st.pyplot(fig)

    if not filtered_data.empty:
        plotting_count(x_axis, hue_axis)
    else:
        st.warning("No data available for the selected filters.")

elif page == "Map View":
    st.title("Geographic Distribution")
    
    st.sidebar.header("Map Settings")
    
    cab_cities = merged_data['City'].unique().tolist()
    
    # Filter cities based on user selection
    selected_map_cities = st.sidebar.multiselect(
        "Select Cities to Display:",
        options=cities_df['City'].tolist(),
        default=cab_cities if set(cab_cities).issubset(set(cities_df['City'].tolist())) else cities_df['City'].tolist()
    )
    
    if selected_map_cities:
        map_data = cities_df[cities_df['City'].isin(selected_map_cities)].copy()
    else:
        map_data = cities_df.copy()
    
    map_data['marker'] = map_data['City'].apply(lambda x: x[0])
    
    # Compute metrics for each city if we have the data
    if not merged_data.empty:
        # Get trip counts by city
        city_metrics = merged_data.groupby('City').agg({
            'Transaction ID': 'count',
            'Price Charged': 'sum'
        }).reset_index()
        city_metrics.columns = ['City', 'Trip_Count', 'Total_Revenue']
        
        # Show the available cities in both datasets to help debug
        # st.sidebar.subheader("Debug Info")
        # with st.sidebar.expander("City Name Mapping"):
        #     st.write("Cities in map data:", cities_df['City'].tolist())
        #     st.write("Cities in cab data:", merged_data['City'].unique().tolist())
        
        # # Add debug printing
        # st.sidebar.write(f"Records in merged_data: {len(merged_data)}")
        # st.sidebar.write(f"Cities with metrics: {len(city_metrics)}")
        
        # For demonstration, let's create some sample data if real data isn't matching
        if len(map_data) > 0 and len(city_metrics) > 0:
            # First try the real merge
            map_data = map_data.merge(city_metrics, on='City', how='left')
            
            # Check if we got any matches
            match_count = (map_data['Trip_Count'].notnull()).sum()
            # st.sidebar.write(f"Cities matched with data: {match_count}")
            
            # If no matches, let's generate random data for demonstration
            if match_count == 0:
                st.warning("⚠️ City names in your coordinates data don't match city names in your cab data. Using random data for demonstration.")
                import numpy as np
                # Generate random data for demonstration
                map_data['Trip_Count'] = np.random.randint(50, 500, size=len(map_data))
                map_data['Total_Revenue'] = map_data['Trip_Count'] * np.random.randint(20, 50, size=len(map_data))
            else:
                map_data['Trip_Count'] = map_data['Trip_Count'].fillna(0).astype(int)
                map_data['Total_Revenue'] = map_data['Total_Revenue'].fillna(0).astype(float)
        # else:
        #     # Generate sample data if either dataset is empty
        #     import numpy as np
        #     map_data['Trip_Count'] = np.random.randint(50, 500, size=len(map_data))
        #     map_data['Total_Revenue'] = map_data['Trip_Count'] * np.random.randint(20, 50, size=len(map_data))
        
        # Scale the radius by trip count or revenue
        scale_by = st.sidebar.radio(
            "Scale Points By:",
            options=["Trip Count", "Revenue", "Equal Size"],
            index=0
        )
        
        if scale_by == "Trip Count":
            map_data['radius'] = map_data['Trip_Count'] / map_data['Trip_Count'].max() * 50000 + 15000
        elif scale_by == "Revenue":
            map_data['radius'] = map_data['Total_Revenue'] / map_data['Total_Revenue'].max() * 50000 + 15000
        else:
            map_data['radius'] = 25000  # Fixed size - increased for visibility
    else:
        # If no trip data, use fixed radius
        map_data['radius'] = 25000
        map_data['Trip_Count'] = 0
        map_data['Total_Revenue'] = 0
    
    
    map_style = st.sidebar.selectbox(
        "Map Style",
        ["Light", "Dark", "Satellite"],
        index=0
    )
    
    if map_style == "Light":
        mapbox_style = "mapbox://styles/mapbox/light-v10"
    elif map_style == "Dark":
        mapbox_style = "mapbox://styles/mapbox/dark-v10"
    else:
        mapbox_style = "mapbox://styles/mapbox/satellite-v9"
    
    
    color_scheme = st.sidebar.selectbox(
        "Color Scheme",
        ["Red", "Blue", "Green", "Gradient by Data"],
        index=0
    )
    
    if color_scheme == "Red":
        map_data['fill_color'] = [[220, 30, 30, 180] for _ in range(len(map_data))]
    elif color_scheme == "Blue":
        map_data['fill_color'] = [[30, 30, 220, 180] for _ in range(len(map_data))]
    elif color_scheme == "Green":
        map_data['fill_color'] = [[30, 180, 30, 180] for _ in range(len(map_data))]
    else:
        import numpy as np
        if scale_by == "Trip Count" and 'Trip_Count' in map_data.columns:
            normalized_values = map_data['Trip_Count'] / (map_data['Trip_Count'].max() if map_data['Trip_Count'].max() > 0 else 1)
        elif scale_by == "Revenue" and 'Total_Revenue' in map_data.columns:
            normalized_values = map_data['Total_Revenue'] / (map_data['Total_Revenue'].max() if map_data['Total_Revenue'].max() > 0 else 1)
        else:
            normalized_values = np.linspace(0, 1, len(map_data))
            
        map_data['fill_color'] = [
            [int(30 + 220 * v), int(144 * (1-v)), int(255 * (1-v)), 200] 
            for v in normalized_values
        ]
    
    view_state = pdk.ViewState(
        latitude=39.8283, 
        longitude=-98.5795,
        zoom=3,
        pitch=0
    )
    
    base_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position=["Longitude", "Latitude"],
        get_radius="radius",
        get_fill_color="fill_color",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
    )
    
    ring_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position=["Longitude", "Latitude"],
        get_radius=[d + 5000 for d in map_data['radius']],
        get_fill_color=[0, 0, 0, 0], 
        pickable=False,
        opacity=0.8,
        stroked=True,
        get_line_color=[255, 255, 255], 
        get_line_width=1000,
        filled=False,
    )
    
    text_layer = pdk.Layer(
        "TextLayer",
        data=map_data,
        get_position=["Longitude", "Latitude"],
        get_text="City",
        get_size=16,
        get_color=[255, 255, 255],
        get_angle=0,
        get_text_anchor="middle",
        get_alignment_baseline="bottom",
        get_pixel_offset=[0, -20],  
    )
    
    marker_layer = pdk.Layer(
        "TextLayer",
        data=map_data,
        get_position=["Longitude", "Latitude"],
        get_text="marker",
        get_size=20,
        get_color=[255, 255, 255],
        get_angle=0,
        get_text_anchor="middle",
        get_alignment_baseline="center",
    )
    
    layers = [base_layer, ring_layer, text_layer, marker_layer]
    
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=mapbox_style,
        tooltip={
            "html": "<b>{City}</b><br/>"
                   "Trips: {Trip_Count}<br/>"
                   "Revenue: ${Total_Revenue}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white"
            }
        }
    )
    
    
    st.pydeck_chart(deck)
    
    st.subheader("City Data")
    display_columns = ['City', 'Latitude', 'Longitude']
    if 'Trip_Count' in map_data.columns:
        display_columns.extend(['Trip_Count', 'Total_Revenue'])

    row_height = 35  
    max_rows_displayed = 20  
    num_rows = min(len(map_data), max_rows_displayed)

    st.dataframe(
        map_data[display_columns],
    )
        
elif page == "Insights & Reports":
    st.title("Key Insights")
    if len(merged_data) > 0:
       
        top_city = merged_data.groupby('City')['Price Charged'].sum().idxmax()
        st.write(f"- The city generating the highest revenue is **{top_city}**.")
        
        avg_fare = merged_data['Price Charged'].mean()
        st.write(f"- The average fare per trip is **${avg_fare:.2f}**.")
        
        most_common_payment = merged_data['Payment_Mode'].mode()[0]
        st.write(f"- The most commonly used payment mode is **{most_common_payment}**.")
        
        
        total_customers = merged_data['Customer ID'].nunique()
        st.write(f"- Total unique customers: **{total_customers}**.")

        st.markdown("---")
        
        revenue_by_city = merged_data.groupby('City')['Price Charged'].sum().reset_index()
        st.subheader("Revenue by City")
        st.bar_chart(revenue_by_city.set_index('City'))

        st.markdown("---")

        trip_count_by_company = merged_data['Company'].value_counts().reset_index()
        trip_count_by_company.columns = ['Company', 'Trip Count']
        st.subheader("Trip Count by Company")
        st.bar_chart(trip_count_by_company.set_index('Company'))

    else:
        st.write("No data available.")
    
    st.markdown("---")