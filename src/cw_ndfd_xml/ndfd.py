import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

ELEMENT_NAMES = { 'maxt':'Maximum Temperature',
'mint':'Minimum Temperature',
'temp':'3 Hourly Temperature',
'dew':'Dewpoint Temperature',
'appt':'Apparent Temperature',
'pop12':'12 Hour Probability of Precipitation',
'qpf':'Liquid Precipitation Amount',
'snow':'Snowfall Amount',
'sky':'Cloud Cover Amount',
'rh':'Relative Humidity',
'wspd':'Wind Speed',
'wdir':'Wind Direction',
'wx':'Weather',
'icons':'Weather Icons',
'waveh':'Wave Height',
'incw34':'Probabilistic Tropical Cyclone Wind Speed >34 Knots (Incremental)',
'incw50':'Probabilistic Tropical Cyclone Wind Speed >50 Knots (Incremental)',
'incw64':'Probabilistic Tropical Cyclone Wind Speed >64 Knots (Incremental)',
'cumw34':'Probabilistic Tropical Cyclone Wind Speed >34 Knots (Cumulative)',
'cumw50':'Probabilistic Tropical Cyclone Wind Speed >50 Knots (Cumulative)',
'cumw64':'Probabilistic Tropical Cyclone Wind Speed >64 Knots (Cumulative)',
'wgust':'Wind Gust',
'conhazo':'Convective Hazard Outlook',
'ptornado':'Probability of Tornadoes',
'phail':'Probability of Hail',
'ptstmwinds':'Probability of Damaging Thunderstorm Winds',
'pxtornado':'Probability of Extreme Tornadoes',
'pxhail':'Probability of Extreme Hail',
'pxtstmwinds':'Probability of Extreme Thunderstorm Winds',
'ptotsvrtstm':'Probability of Severe Thunderstorms',
'pxtotsvrtstm':'Probability of Extreme Severe Thunderstorms',
'tmpabv14d':'Probability of 8- To 14-Day Average Temperature Above Normal',
'tmpblw14d':'Probability of 8- To 14-Day Average Temperature Below Normal',
'tmpabv30d':'Probability of One-Month Average Temperature Above Normal',
'tmpblw30d':'Probability of One-Month Average Temperature Below Normal',
'tmpabv90d':'Probability of Three-Month Average Temperature Above Normal',
'tmpblw90d':'Probability of Three-Month Average Temperature Below Normal',
'prcpabv14d':'Probability of 8- To 14-Day Total Precipitation Above Median',
'prcpblw14d':'Probability of 8- To 14-Day Total Precipitation Below Median',
'prcpabv30d':'Probability of One-Month Total Precipitation Above Median',
'prcpblw30d':'Probability of One-Month Total Precipitation Below Median',
'prcpabv90d':'Probability of Three-Month Total Precipitation Above Median',
'prcpblw90d':'Probability of Three-Month Total Precipitation Below Median',
'precipa_r':'Real-time Mesoscale Analysis Precipitation',
'sky_r':'Real-time Mesoscale Analysis GOES Effective Cloud Amount',
'td_r':'Real-time Mesoscale Analysis Dewpoint Temperature',
'temp_r':'Real-time Mesoscale Analysis Temperature',
'wdir_r':'Real-time Mesoscale Analysis Wind Direction',
'wwa':'Watches, Warnings, and Advisories',
'wspd_r':'Real-time Mesoscale Analysis Wind Speed'}

WEB_SERVICE_URL = 'https://graphical.weather.gov/xml/SOAP_server/ndfdXMLclient.php'
WEB_SERVICE_PARAMS = [ 'maxt', 'temp', 'mint', 'pop12', 'sky', 'wspd', 'appt', 'qpf', 'snow', 'wx', 'wgust', 'icons', 'rh' ]

class WebService:

    def xml(self, latitude, longitude):
        params = { param : param for param in WEB_SERVICE_PARAMS }
        params['lat'] = latitude
        params['lon'] = longitude
        params['product'] = 'time-series'
        params['Submit'] = 'Submit'

        s = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        response = requests.get(WEB_SERVICE_URL, params)
        return response.text
