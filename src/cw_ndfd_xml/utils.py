import dateutil.parser

# Convert XML date to SQL - TODO - look at what we are doing here with the timezone offset
def convert_xml_datetime_sql(xml_date):
    try:
        dt = dateutil.parser.isoparse(xml_date)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return '' # TODO, this should probably return none
