import time

from influxdb import InfluxDBClient

__version__ = "0.1"
__all__ = ["LWAInfluxClient",]


DEFAULT_INFLUX_HOST = 'fornax.phys.unm.edu'
DEFAULT_INFLUX_PORT = 8086
DEFAULT_INFLUX_SSL = True


class LWAInfluxClient(object):
    """
    Class for interfacing with the LWA InfluxDB server and sending subsystem
    data.
    """
    
    def __init__(self, username, password, database, host=DEFAULT_INFLUX_HOST, port=DEFAULT_INFLUX_PORT, ssl=DEFAULT_INFLUX_SSL):
        self._host = host
        self._port = port
        self._ssl = ssl
        self._username = username
        self._password = password
        self._database = database
        
    @classmethod
    def from_config(cls, config):
        """
        Given an LWA subsystem configuration dictionary, return an initialized LWAInfluxClient.
        """
        
        if not isinstance(config, dict):
            raise TypeError("Expected a configuration dictionary")
            
        args = []
        for key in ('INFLUXUSER', 'INFLUXPASSWORD', 'INFLUXDATABASE'):
            try:
                args.append(config[key])
            except KeyError:
                raise ValueError("Configuration dictionary missing required key: %s" % key)
        for key,default in zip(('INFLUXHOST', 'INFLUXPORT', 'INFLUXSSL'), (DEFAULT_INFLUX_HOST, DEFAULT_INFLUX_PORT, DEFAULT_INFLUX_SSL)):
            try:
                args.append(config[key])
            except KeyError:
                args.append(default)
        return LWAInfluxClient(*args)
        
    @staticmethod
    def now():
        """
        Return an InfluxDB timestamp corresponding to right now.
        """
        
        return int(time.time()*1e9)
        
    def test(self):
        """
        Test the connection to the InfluxDB server.
        """
        
        status = True
        try:
            db = InfluxDBClient(self._host, self._port, self._username, self._password, self._database, self._ssl)
            db.ping()
            db.close()
        except Exception as e:
            status = False
            
        return status
        
    def write(self, json_list):
        """
        Given a list of JSON measurements, write them to InfluxDB.  Return a
        two-element tuple of (status, error) indicating success.  If 'status'
        is False 'error' is a string of the actual exception caught.
        """
        
        if isinstance(json_list, dict):
            json_list = [json_list,]
            
        status = True
        error = None
        try:
            db = InfluxDBClient(self._host, self._port, self._username, self._password, self._database, self._ssl)
            db.write_points(json_list)
            db.close()
        except Exception as e:
            status = False
            error = str(e)
            
        return status, error
