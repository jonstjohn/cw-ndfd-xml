import datetime
import os.path
import urllib.request

from cw_ndfd_xml import dwml
from cw_ndfd_xml import utils
from cw_ndfd_xml import ndfd

class LocationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Forecast:

    def generate(self, latitude, longitude):
        """Generate forecast data

        Returns:
            Dictionary of data
        """
        ws = ndfd.WebService()
        xml_str = ws.xml(latitude, longitude)

        parser = ForecastParser()
        return parser.parse(xml_str)

class ForecastParser:
    """Convert XML to forecast data"""

    codes =  {
        'Daily Maximum Temperature' : 'maxt',
        'Daily Minimum Temperature' : 'mint',
        '12 Hourly Probability of Precipitation' : 'pop12',
        'Temperature' : 'temp',
        'Dew Point' : 'td',
        'Apparent Temperature' : 'apt',
        'Cloud Cover Amount' : 'sky',
        'Wind Direction' : 'wdir',
        'Wind Speed' : 'wspd',
        'Wind Speed Gust' : 'wgust',
        'Weather Type, Coverage, and Intensity' : 'wx',
        'Liquid Precipitation Amount' : 'qpf',
        'Snow Amount' : 'snow',
        'Relative Humidity' : 'rhm',
        'Conditions Icons' : 'sym'
    }

    def parse(self, xml):
        
        parser = dwml.DwmlParser()
        doc = parser.parse(xml)

        daily = self._daily(doc)
        hourly = self._hourly(doc)
        forecast_data = {'daily': daily, 'hourly': hourly}
        return self._cleanup(forecast_data)

    def _daily(self, doc):
        
        code_map = { v: k for k, v in self.codes.items() }
        
        daily = {}
            
        daily = self._combine_daily(daily, 'high', 
            self._aggregate(doc.parameter(code_map['maxt']).values, 'first'))
        daily = self._combine_daily(daily, 'low',
            self._daily_low(
                doc.parameter(code_map['mint']).values,
                doc.parameter(code_map['temp']).values))
        daily = self._combine_daily(daily, 'precip_day', 
            self._aggregate(doc.parameter(code_map['pop12']).values, 'first',
                skipper = self._skip_different_startend_date))
        daily = self._combine_daily(daily, 'precip_night',
            self._aggregate(doc.parameter(code_map['pop12']).values, 'first',
                skipper = self._skip_same_startend_date))
        daily = self._combine_daily(daily, 'rain_amount',
            self._aggregate(doc.parameter(code_map['qpf']).values, 'sum', True, 2,
                skipper = self._skip_empty_value, min_values=3))
        daily = self._combine_daily(daily, 'snow_amount',
            self._aggregate(doc.parameter(code_map['snow']).values, 'sum', True, 1,
                skipper = self._skip_empty_value, min_values=3))
        daily = self._combine_daily(daily, 'relative_humidity',
            self._aggregate(doc.parameter(code_map['rhm']).values, 'average'))
        daily = self._combine_daily(daily, 'wind_gust', 
            self._aggregate(doc.parameter(code_map['wgust']).values, 'max', 
            formatter = self._format_wind))
        daily = self._combine_daily(daily,  'wind_sustained', 
            self._aggregate(doc.parameter(code_map['wspd']).values, 'average', 
                formatter = self._format_wind))
        daily = self._combine_daily(daily, 'weather', 
            self._aggregate(doc.parameter(code_map['wx']).values, 'first-nonempty', False, 
                formatter = self._format_weather, 
                skipper = self._skip_night))
        daily = self._combine_daily(daily, 'wsym', 
            self._aggregate(doc.parameter(code_map['sym']).values, 'frequent', False, 
                formatter = self._format_symbol, 
                skipper = self._skip_night_symbol))

        return daily

    def _hourly(self, doc):

        code_map = { v: k for k, v in self.codes.items() }

        hourly = {}
        hourly = self._combine_hourly(hourly, 'temp',
            self._single(doc.parameter(code_map['temp']).values)
        )
        hourly = self._combine_hourly(hourly, 'precip',
            self._single(doc.parameter(code_map['pop12']).values)
        )
        hourly = self._combine_hourly(hourly, 'relative_humidity',
            self._single(doc.parameter(code_map['rhm']).values)
        )
        hourly = self._combine_hourly(hourly, 'rain_amount',
            self._single(doc.parameter(code_map['qpf']).values)
        )
        hourly = self._combine_hourly(hourly, 'snow_amount',
            self._single(doc.parameter(code_map['snow']).values)
        )
        hourly = self._combine_hourly(hourly, 'wind_sustained',
            self._single(doc.parameter(code_map['wspd']).values,
                self._format_wind)
        )
        hourly = self._combine_hourly(hourly, 'wind_gust',
            self._single(doc.parameter(code_map['wgust']).values, 
                self._format_wind)
        )
        hourly = self._combine_hourly(hourly, 'sky',
            self._single(doc.parameter(code_map['sky']).values)
        )
        hourly = self._combine_hourly(hourly, 'weather',
            self._single(doc.parameter(code_map['wx']).values, 
                self._format_weather)
        )
        hourly = self._combine_hourly(hourly, 'wsym',
            self._single(doc.parameter(code_map['sym']).values, 
                self._format_symbol)
        )
        return hourly

    def _combine_hourly(self, hourly, code, additional):
        """Add additional data to the hourly forecast

        Args:
            code: Key for the forecast value
            hourly: Dictionary of format [date][time][code] = value
            additional: Dictionary of [date][time] = value

        Returns:
            New hourly dictionary
        """
        for start_date in additional.keys():
            if start_date not in hourly:
                hourly[start_date] = {}
            for start_time in additional[start_date].keys():
                if start_time not in hourly[start_date]:
                    hourly[start_date][start_time] = {}    
                hourly[start_date][start_time][code] = additional[start_date][start_time]

        return hourly

    def _combine_daily(self, daily, code, additional):
        """Add additional data to the daily forecast

        Args:
            code: Key for the forecast value
            hourly: Dictionary of format [date][code] = value
            additional: Dictionary of [date] = value

        Returns:
            New daily dictionary
        """
        for start_date in additional.keys():
            if start_date not in daily:
                daily[start_date] = {}
            daily[start_date][code] = additional[start_date]

        return daily

    def _daily_low(self, dailies, hourlies):
        """Find daily for each date of either the minimum for the day or
            the minimum for the hourly values

        Args:
            dailies: [DwmlParameterValue] for daily min
            hourlies: [DwmlParameterValue] for hourly temps

        Returns:
            Dictionary of dates to minimum temperatures
        """

        data = {}

        # Daily mins typically start on one date and end on the next
        # If we don't have a daily min then we probably don't have the whole time
        # period. It is safe to ignore it.
        # First, let's setup our data using the end date, since we know that we
        # have a complete period.
        # For now, we must ignore the fact that we may have a lower temperature in the
        # previous evening and hope to catch that in the hourly temps
        for day in dailies:
            end_date = day.end.strftime('%Y-%m-%d')
            data[end_date] = day.value

        # Now let's loop over the hourlies to see if any forecast temps are lower than the dailies
        # Here we will use the start and end dates, since we assume the temp is valid over the entire
        # time period
        for hour in hourlies:
            # Check start date
            start_date = hour.start.strftime('%Y-%m-%d')
            if start_date in data and int(hour.value) < int(data[start_date]):
                data[start_date] = hour.value

            # Check end date
            if hour.end:
                end_date = hour.end.strftime('%Y-%m-%d')
                if end_date in data and int(hour.value) < int(data[end_date]):
                    data[end_date] = hour.value

        return data

    def _format_symbol(self, value):
        """Format weather symbol

        Args:
            value: String

        Returns:
            Weather symbol, e.g., nshr80.jpg
        """
        return self._symbol_from_link(value)
        
    def _format_wind(self, knots):
        return int(float(knots) * 1.15077945) if knots else None

    def _format_weather(self, weather_line):
        
        # split weather line to get text description
        try:

           elements = weather_line.split('|')
           coverage_element = elements[1]
           intensity_element = elements[2]
           weather_type_element = elements[3]
        
           ctmp = coverage_element.split(':')
           coverage = ctmp[1]

           itmp = intensity_element.split(':')
           intensity = itmp[1]
           if intensity == 'none':

               intensity = ''

           wtmp = weather_type_element.split(':')
           weather = wtmp[1]

           str = ''
           if coverage == 'likely':

               str = "{} {} {}".format(intensity, weather, coverage)

           elif coverage == 'chance' or coverage == 'slight chance':

               str = "{} of {} {}".format(coverage, intensity, weather)

           elif coverage == 'definitely':

               str = "{} {}".format(intensity, weather)

           else:

               str = "{} {} {}".format(coverage, intensity, weather)

           return str

        except:

           return ''

    def _aggregate(self, values, function, is_numeric = True, decimal = 0, 
                 skipper = None, formatter = None, min_values = None):
        """Aggregate a set of parameter values by date based on a function

        Args:
            values: [DwmlParameterValue]
            function: String of supported functions: average, sum, max, min, first, first-nonempty, frequent
            is_numeric: True if value should be considered numeric
            decimal: Number of decimals for a numeric value
            skipper: A function that takes a DwmlParameterValue and determines if it should be skipped
            formatter: A function that formats a DwmlParameterValue.value
            min_values: Minimum number of values that need to be present to aggregate

        Returns:
            Dictionary where keys are SQL-formatted dates and value is the aggregated value
        """

        # Add values to data indexed by start date
        indexed_values = {}
        for v in values:

            # Ignore empty values if we are expecting numeric
            if is_numeric and not v.value:
                continue

            # Apply skipper function
            if skipper and skipper(v):
                continue

            start_date = v.start.strftime('%Y-%m-%d')
            if start_date not in indexed_values.keys():
                indexed_values[start_date] = []

            # Convert to float TODO - probably should be in a formatter function
            value = float(v.value) if is_numeric and len(str(v.value)) else v.value
            indexed_values[start_date].append(value)

        data = {} 
        for date, values in indexed_values.items():
           
           
            # If measuring rain amount and don't have a full 3 data points
            # May be slightly inaccurate
            #if label in ('rain_amount', 'snow_amount') and len(values) < 3:
            #    continue
            if min_values and len(values) < min_values:
                continue
           
            # Apply aggregate function
            if function == 'average': value = sum(values)/len(values)
            elif function == 'sum': value = sum(values)
            elif function == 'max': value = max(values)
            elif function == 'min': value = min(values)
            elif function == 'first': value = values[0]
            elif function == 'first-nonempty': value = self._first_nonempty(values)
            elif function == 'frequent': value = self._most_frequent(values)
            else: value = values[0] 

            if is_numeric:
                if decimal == 0: value = int(value)
                else: value = round(value, decimal)
                  
            if formatter:
                value = formatter(value)
           
            data[date] = value

        return data

    def _first_nonempty(self, values):
        for v in values:
            if len(str(v)) > 0:
                return v
        return None

    def _most_frequent(self, values):
        
        # Create dictionary of values to number of times it occurred
        counts = {}
        for val in values:
            if not val in counts:
                counts[val] = 0
            counts[val] = counts[val] + 1

        # Loop over dictionary and set val to most frequently seen one
        maxCount = 0
        for k, v in counts.items():
            if v > maxCount:
                val = k
                maxCount = v
        return val

    def _single(self, values, formatter = None):

        data = {}
        for v in values:
            start_date = v.start.strftime('%Y-%m-%d')
            start_time = v.start.strftime('%H:%M:%S')

            if start_date not in data.keys():
                data[start_date] = {}

            value = formatter(v.value) if formatter else v.value
            data[start_date][start_time] = value

        return data

    def _is_night(self, time):
        """Check to see if time is at night
            For now this is just a rough approximation
            withou taking in time of year

        Args:
            dt: Time object

        Returns:
            True if it is at night
        """
        sunrise, sunset = datetime.time(6, 0, 0), datetime.time(18, 0, 0)
        return time < sunrise or time > sunset
        

    def _skip_night(self, value):
        return self._is_night(value.start.time())
    
    def _skip_different_startend_date(self, value):
        return value.start.date() != value.end.date()        

    def _skip_same_startend_date(self, value):
        return value.start.date() == value.end.date()        

    def _skip_empty_value(self, value):
        return len(value.value) == 0
    
    def _skip_night_symbol(self, parameter_value):
        """Skip night symbols (used for daily)

        Args:
            value: DwmlParameterValue

        Returns:
            True if it should be skipped
        """
        link = parameter_value.value
        if not link:
            return False
        symbol = self._symbol_from_link(link)
        if not symbol:
            return False
        return self._is_night_symbol(symbol)

    def _is_night_symbol(self, symbol):
        """Check to see if a symbol is a night symbol

        Args:
            symbol: E.g., nra80.jpg

        Returns:
            True if this is a nighttime symbol, False if not or empty
        """
        if not symbol:
            return False
        return symbol[0] == 'n' if len(symbol) else False

    def _symbol_from_link(self, link):
        """Get the weather symbol from the full link

        Args:
            link: Fully URL link

        Returns:
            Symbol portion of link or None
        """
        if not link:
            return None
        return link.split('/')[-1] if '/' in link else None

    def _cleanup(self, data):
        """Do some final cleanup on the data

        Args:
            data: Dictionary of 
                {'daily': [{ date: { key: value } }],
                    'hourly': [{ date: { time: { key: value } } }]}

        Returns:
            Same data structure, cleanup up
        """
        """
        if not self._includePast:
           
           from datetime import date
           
           today = date.today()
           month = today.month if len(str(today.month)) == 2 else "0" + str(today.month)
           day = today.day if len(str(today.day)) == 2 else "0" + str(today.day)
           sqlToday = "{0}-{1}-{2}".format(today.year, month, day)
           
           for date in list(self.forecast_data['daily']): #.keys():
               
               if date < sqlToday:
                  
                  del self.forecast_data['daily'][date]
                  
           for date in list(self.forecast_data['hourly']): # .keys():
               
               if date < sqlToday:
                  
                  del self.forecast_data['hourly'][date]
        """
           
        # Fill in precip and rain blanks
        tmpPrecip = None
        averageRain = None
        averageSnow = None
        dates = list(data['hourly']) # .keys()
        dates.sort()
       
        # Iterate over dates
        for date in dates:
            times = list(data['hourly'][date])
            times.sort()
            for time in times:

                # Get precip for time - 'precip' is pop12
                currentPrecip = data['hourly'][date][time]['precip'] if 'precip' in data['hourly'][date][time] else None
              
                # If precip from previous period exists and current precip doesn't exist, use previous cycle
                if tmpPrecip and not currentPrecip:
                    data['hourly'][date][time]['precip'] = tmpPrecip

                # If there is current precip, update tmp precip to use in the next cycle
                if currentPrecip:
                    tmpPrecip = currentPrecip
                  
                # If rain amount is available, it is 6-hour, divide in half and carry over to next time
                if 'rain_amount' in data['hourly'][date][time] and data['hourly'][date][time]['rain_amount']:
                    averageRain = round(float(data['hourly'][date][time]['rain_amount'])/2,2)
                    data['hourly'][date][time]['rain_amount'] = averageRain
               
                # Does not have rain, check to see if we have carry-over average rain
                else:
                    if averageRain != 0:
                        data['hourly'][date][time]['rain_amount'] = averageRain  
                    averageRain = 0
                  
                # If snow amount is available, it is 6-hour, divide in half and carry over to next time
                if 'snow_amount' in data['hourly'][date][time] and data['hourly'][date][time]['snow_amount']:
                    averageSnow = round(float(data['hourly'][date][time]['snow_amount'])/2,2)
                    data['hourly'][date][time]['snow_amount'] = averageSnow
                # Does not have snow, check to see if we have carry-over average snow
                else:
                    if averageSnow != 0:
                        data['hourly'][date][time]['snow_amount'] = averageSnow  
                    averageSnow = 0
                  
                # Remove times that only have precip and no temp
                if not 'temp' in data['hourly'][date][time]:
                    data['hourly'][date].pop(time)

        return data
           
