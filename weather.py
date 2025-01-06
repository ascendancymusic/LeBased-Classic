import requests
from datetime import datetime, timedelta
import creds
# Cache dictionary to store the weather data with the fetch time
weather_cache = {}

def fetch_weather(date):
    city_id = 633680 # Turku
    cache_duration = timedelta(minutes=30)
    
    # Check if the data for the requested date is in the cache and is still valid
    if date in weather_cache:
        cached_data, fetch_time = weather_cache[date]
        if datetime.now() - fetch_time < cache_duration:
            return cached_data
    
    url = f'http://api.openweathermap.org/data/2.5/forecast?id={city_id}&appid={creds.api_key}&units=metric'
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'list' in data:
            for forecast in data['list']:
                forecast_date = datetime.fromtimestamp(forecast['dt'])
                if forecast_date.date() == date.date():
                    temp = round(forecast['main']['temp'])
                    rain_probability = forecast['pop'] * 100
                    desc = forecast['weather'][0]['description']

                    # Calculate spaces based on the length of the description
                    desc_length = len(desc) + 2  # Add 2 for ": "
                    spaces = ' ' * (16 - desc_length)  # 16 is the fixed width for "Chance of Rain: "
                    
                    result = (
                        f"[font=Tex]{desc.capitalize()}:{spaces}[/font]"
                        f"[font=TexBold]{temp}°C[/font]\n"
                        f"[font=Tex]Chance of Rain:{' ' * (16 - 15)}[/font]"
                        f"[font=TexBold]{round(rain_probability)}%[/font]"
                    )
                    
                    # Update the cache
                    weather_cache[date] = (result, datetime.now())
                    
                    return result
            return "No weather data available"
        else:
            return "No weather data available"
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return "No weather data available"

if __name__ == '__main__':
    weather_data = fetch_weather(datetime.now())
    print(weather_data)  # For testing purposes
