import pandas as pd
import requests
import json
import sqlalchemy
from sqlalchemy import create_engine

# Define variables to be used
api_key = 'xxx'
city = 'Turku'
country = 'FI'
weather_url = f'http://api.openweathermap.org/data/2.5/forecast?q={city},{country}&appid={api_key}&units=metric'

# paths
USER = 'ap'
json_loc = f'C:\\Users\\milli\\Portfolio\\weather_Project\\weather.json'
csv_loc = f'C:\\Users\\milli\\Portfolio\\weather_Project\\weather.csv'
clean_csv_loc = f'C:\\Users\\milli\\Portfolio\\weather_Project\\weather_clean.csv'
db_loc = f'C:\\Users\\milli\\Portfolio\\weather_Project\\weather.db'

# Get weather data
def exract_data():
    # Download the weather data
    response = requests.get(weather_url)
    if response.status_code != 200:
        print('Something went wrong')
        return None
    else:
        data = response.json()
    # Save weather data in json file
    with open(json_loc, 'w') as f:
        json.dump(data, f)

    # Convert json to csv
    # Read json file
    with open(json_loc, 'r') as f:
        # Load json file
        data = json.load(f)
    
    # Extract the list of forecasts from the 'list' key
    forecasts = data['list']

    # Flatten the forecasts and convert to a DataFrame
    df = pd.json_normalize(forecasts)

    # Save DataFrame to a CSV file
    df.to_csv(csv_loc, index=False)

    return df

def clean_data(df):
    # Fill missing values with 0
    df = df.fillna(0)

    # Rename columns
    df = df.rename(columns={
        'dt_txt': 'date',
        'main.temp': 'temp',
        'main.feels_like': 'feels_like',
        'main.temp_min': 'temp_min',
        'main.temp_max': 'temp_max',
        'main.pressure': 'pressure',
        'main.humidity': 'humidity',
        'wind.speed': 'wind_speed',
        'clouds.all': 'clouds',
        'snow.3h': 'snow',
        'rain.3h': 'rain'
    })

    # Drop columns that are not needed
    df = df.drop(['dt', 'weather', 'pop', 'visibility', 'main.sea_level',
                  'main.grnd_level', 'main.temp_kf', 'wind.deg',
                  'wind.gust', 'sys.pod'], axis=1)

    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])

    # Remove duplicates if there are any
    df = df.drop_duplicates(subset=['date'], keep='first')

    # Convert the types of columns to float
    for col in ['temp', 'feels_like', 'temp_min', 'temp_max', 'pressure', 'humidity', 'wind_speed', 'clouds']:
        df[col] = df[col].astype('float64')

    if 'rain' in df.columns:
        df['rain'] = df['rain'].astype('float64')
    if 'snow' in df.columns:
        df['snow'] = df['snow'].astype('float64')

    # Add wind strength column
    '''
    0 - 1.5 m/s = Calm
    1.6 - 3.3 m/s = Light air
    3.4 - 5.4 m/s = Light breeze
    5.5 - 7.9 m/s = Gentle breeze
    8.0 - 10.7 m/s = Moderate breeze
    10.8 - 13.8 m/s = Fresh breeze
    13.9 - 17.1 m/s = Strong breeze
    17.2 - 20.7 m/s = Near gale
    20.8 - 24.4 m/s = Gale
    24.5 - 28.4 m/s = Strong gale
    28.5 - 32.6 m/s = Storm
    < 32.7 = Violent storm
    '''
    df['wind_strength'] = pd.cut(df['wind_speed'], 
                                bins=[0, 1.5, 3.3, 5.4, 7.9, 10.7, 13.8, 17.1, 20.7, 24.4, 28.4, 32.6, 100],
                                labels=['Calm', 'Light air', 'Light breeze', 'Gentle breeze', 'Moderate breeze', 
                                        'Fresh breeze', 'Strong breeze', 'Near gale', 'Gale', 'Strong gale', 'Storm', 
                                        'Violent storm'])

    return df

def calc_averages(df):
    # Calculate daily averages for temperature, humidity and percipitation
    df_day_mean = df.copy()
    # Drop wind strength column as it is categorical and not needed for mean
    df_day_mean = df_day_mean.drop(['wind_strength'], axis=1)
    df_day_mean['date'] = df_day_mean['date'].dt.date
    df_day_mean = df_day_mean.groupby('date').mean().reset_index()

    # Calculate monthly averages for temperature, humidity and percipitation
    # Set 'date' as the index
    df.set_index('date', inplace=True)

    # Calculate the mean and change the column names to include '_mean'
    df_month_mean = df[['temp', 'humidity', 'clouds', 'wind_speed']].resample('M').mean()
    df_month_mean.columns = [f'{col}_mean' for col in df_month_mean.columns]

    # Calculate the standard deviation and change the column names to include '_std'
    df_month_std = df[['temp', 'humidity', 'clouds', 'wind_speed']].resample('M').std()
    df_month_std.columns = [f'{col}_std' for col in df_month_std.columns]

    # Calculate the minimum and change the column names to include '_min'
    df_month_min = df[['temp', 'humidity', 'clouds', 'wind_speed']].resample('M').min()
    df_month_min.columns = [f'{col}_min' for col in df_month_min.columns]

    # Calculate the maximum and change the column names to include '_max'
    df_month_max = df[['temp', 'humidity', 'clouds', 'wind_speed']].resample('M').max()
    df_month_max.columns = [f'{col}_max' for col in df_month_max.columns]

    # Concatenate the statistics DataFrames
    df_month_stats = pd.concat([df_month_mean, df_month_std, df_month_min, df_month_max], axis=1)

    # Change the date to display month name and year only
    df_month_stats.index = df_month_mean.index.strftime('%B %Y')

    return df_day_mean, df_month_stats
    
def load_data(clean_df, day_mean, month_mean):
    # Create a connection to the database
    engine = create_engine(f'sqlite:///{db_loc}')
    sqlite_connection = engine.connect()

    # Create a table for the weather data
    clean_df.to_sql('weather', sqlite_connection, if_exists='replace')

    # Create a table for the daily averages
    day_mean.to_sql('day_mean', sqlite_connection, if_exists='replace')

    # Create a table for the monthly averages
    month_mean.to_sql('month_mean', sqlite_connection, if_exists='replace')

    # Close the connection
    sqlite_connection.close()

    # Save the DataFrame to a csv
    clean_df.to_csv(clean_csv_loc, index=False)

# Define the ETL process
def etl_process():
    # Download and convert the data
    df = exract_data()

    # Clean the data
    clean_df = clean_data(df)

    # Calculate the averages
    day_mean, month_stats = calc_averages(clean_df)

    # Load the data
    load_data(clean_df, day_mean, month_stats)

# Run the ETL process
etl_process()
