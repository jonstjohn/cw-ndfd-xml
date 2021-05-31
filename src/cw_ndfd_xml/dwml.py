"""Handles DWML related actions, such as parsing

Used to convert an DWML XML string into an object representation
for easier processing.

  Typical usage example:

  parser = DwmlParser()
  doc = parser.parse(xml) # DwmlDoc object
  legacy_formatted_data = doc.as_legacy_data() # Legacy dictionary
"""
from xml.etree import ElementTree

import dateutil.parser

PARAMETERS = {
    'temperature': ( # DWML tag
        { 'element': 'maxt', 'name':'Daily Maximum Temperature', 'attribs': {'type': 'maximum'} },
        { 'element': 'mint', 'name':'Daily Minimum Temperature', 'attribs': {'type': 'minimum'} },
        { 'element': 'temp', 'name':'Temperature', 'attribs': {'type': 'hourly'} },
        { 'element': 'apt', 'name':'Apparent Temperature', 'attribs': {'type': 'apparent'} }
),
    'precipitation': (
        { 'element': 'qpf', 'name': 'Liquid Precipitation Amount', 'attribs': {'type': 'liquid'} },
        { 'element': 'snow', 'name': 'Snow Amount', 'attribs': {'type': 'snow'} }
    ),
    'wind-speed': (
        { 'element': 'wspd', 'name': 'Wind Speed', 'attribs': {'type': 'sustained'} },
        { 'element': 'wgust', 'name': 'Wind Gust', 'attribs': {'type': 'gust'} }
    ),
    'cloud-amount': (
        { 'element': 'sky', 'name': 'Cloud Cover Amount', 'attribs': {'type': 'total'} }
    ),
    'probability-of-precipitation': (
        { 'element': 'pop12', 'name': '12 Hourly Probability of Precipitation', 'attribs': {'type': '12 hour'} }
    ),
    'relative': (
        { 'element': 'rhm', 'name': 'Relative Humidity', 'attribs': {'type': 'relative'} }
    ),
    'weather': (
        { 'element': 'wx', 'name': 'Weather Type, Coverage, and Intensity' }
    ),
    'conditions-icon': (
        { 'element': 'sym', 'name': 'Conditions Icons' }
    )
}

class DwmlParameterValue:
    """Represents a parameter value

    Attributes:
        value: Raw value
        start: Datetime object representing start
        end: Datetime object representing end
    """
    def __init__(self, value, start, end):
        self.value = value
        self.start = start
        self.end = end

    def as_legacy_data(self):
        return { 
            'value': self.value, 
            'start': self.format_legacy_datetime(self.start), 
            'end': self.format_legacy_datetime(self.end) if self.end else None 
        }

    def format_legacy_datetime(self, dt):
        return dt.isoformat()

class DwmlParameter:
    """Represents a Dwml parameter
    
    Attributes:
        tag: String for the DWML tag
        name: String for the parameter name tag
        time_layout_key: String for the key associated with the time layout
        values: List of values
        typ: String for the type attribute for the parameter tag
        units: String for the 'units' attribute of the parameter tag

    """
    def __init__(self, tag, name, time_layout_key, values, typ=None, units=None):
        self.tag = tag
        self.name = name
        self.time_layout_key = time_layout_key
        self.values = values
        self.typ = typ
        self.units = units


class DwmlParser:
    """Parses DWML strings into object a DwmlDoc representation
    """
    def parse(self, xml):
        """Parse an XML string into object representation

        Args;
            xml: XML string

        Returns:
            DwmlDoc
        """
        tree = ElementTree.fromstring(xml)
        locations = self.parse_locations(tree)
        time_layouts = self.parse_time_layouts(tree)
        parameters = self.parse_parameters(tree, time_layouts)
        return DwmlDoc(locations, time_layouts, parameters)

    def parse_locations(self, tree):
        """Parse locations from a tree

        Args:
            tree: ElementTree tree

        Returns:
            [DwmlLocation]
        """
        locations = []
        for location in tree.getiterator('location'):
            name = None
            latitude = None
            longitude = None
            for child in location.getchildren():
                if child.tag == 'location-key':
                    name = child.text
                if child.tag == 'point':
                    if 'latitude' in child.attrib: 
                        latitude = child.attrib['latitude']
                    if 'longitude' in child.attrib: 
                        longitude = child.attrib['longitude']
            locations.append(DwmlLocation(name, latitude, longitude))
        return locations
                    
    
    def parse_time_layouts(self, tree):
        """Get time layouts

        Args:
            tree: ElementTree tree

        Returns:
            Dictionary of { key: DwmlTimeLayout }
        """
        time_layouts = {}

        # Iterate over every time-layout tag
        for time_layout in tree.getiterator("time-layout"):
            key = None
            coordinate = time_layout.attrib.get('time-coordinate')
            summarization = time_layout.attrib.get('summarization')
            periods = []

            # Iterate over child tags
            for child in time_layout.getchildren():
                if (child.tag == 'layout-key'):
                    key = child.text
                if (child.tag == 'start-valid-time'):
                    periods.append([child.text, None])
                if (child.tag == 'end-valid-time'):
                    periods[len(periods)-1][1] = child.text 

            time_layouts[key] = DwmlTimeLayout(key, coordinate, summarization, periods)
                    
        return time_layouts

    def parse_parameters(self, tree, time_layouts):
        """Parse parameters

        Args:
            tree: ElementTree tree

        Returns:
            List of parameters
        """
        parameters = []
        for parameter in tree.find('data/parameters').getchildren(): 
            tag = None
            name = None
            time_layout_key = None
            values = []
            typ = None
            units = None

            tag = parameter.tag
            time_layout_key = parameter.attrib.get('time-layout')
            typ = parameter.attrib.get('type')
            units = parameter.attrib.get('units')
            
            for child in parameter.getchildren():
                if child.tag == 'name':
                    name = child.text
                if child.tag in ('value', 'icon-link'):
                    values.append(child.text)
                elif child.tag == 'weather-conditions':
                    value = '' # TODO change to None
                    for grand in child.getchildren():
                        if grand.tag == 'value':
                            value += self.format_weather(grand.attrib.get('coverage'), grand.attrib.get('intensity'),
                                    grand.attrib.get('weather-type'), grand.attrib.get('qualifier'))
                    values.append(value)

            pvalues = []
            for v, periods in zip(values, time_layouts[time_layout_key].periods):
                parameter_value = DwmlParameterValue(v,
                   dateutil.parser.isoparse(periods[0]),
                   dateutil.parser.isoparse(periods[1]) if periods[1] else None)
                pvalues.append(parameter_value)
                #pvalues.append(DwmlParameterValue(v, periods[0], periods[1]))

            parameters.append(
                DwmlParameter(tag, name, time_layout_key,
                    pvalues, typ, units))

        return parameters

    def format_weather(self, coverage, intensity, weather_type, qualifier):
        """Format weather value

        Args:
            coverage: String for coverage
            intensity: String for intensity
            weather_type: String for weather type
            qualifier: String for qualifier

        Returns:
            String formatted weather
        """
        return "|coverage:{}|intensity:{}|weather-type:{}|qualifier:{}".format(
            coverage, intensity, weather_type, qualifier)

class DwmlDoc:
    """Representation of a DWML document

    Attributes:
        locations: [DwmlLocation]
        time_layouts: Dictionary of time layouts { key: DwmlTimeLayout }
        parameters: [DwmlParameter]
    """
    def __init__(self, locations, time_layouts, parameters):
        self.locations = locations
        self.time_layouts = time_layouts
        self.parameters = parameters

    def parameter(self, name):
        return next(p for p in self.parameters if p.name == name)

    def as_legacy_data(self):
        """Get the doc as legacy data

        Returns:
            Data dictionary
            {'[name, e.g., Daily Maximum Temperature]':
                {'name': '[name, e.g., Daily Maximium Temperature]', 'values':
                    [{'value': '[value, e.g., 33]',
                        'start': '[start date, e.g., 2020-02-07T07:00:00-05:00]',
                        'end': '[end date, e.g., 2020-02-07T19:00:00-05:00]'},
                        ...
                    ]
                },
                ...
            }
        """
        data = {}
        for parameter in self.parameters:
            values = [ v.as_legacy_data() for v in parameter.values]
            data[parameter.name] = { 'name': parameter.name, 'values': values } 
        return data


class DwmlLocation:
    def __init__(self, name, latitude, longitude):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

class DwmlTimeLayout:
    def __init__(self, key, coordinate, summarization, periods):
        self.key = key
        self.coordinate = coordinate
        self.summarization = summarization
        self.periods = periods

