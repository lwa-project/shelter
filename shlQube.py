
import time
import logging
import threading
import requests
import xml.etree.ElementTree as ET

shlQubeLogger = logging.getLogger('__main__')


__version__ = '0.3'
__all__ = ['get_iceqube_status', 'get_iceqube_lead_status', 'get_iceqube_settings',
           'get_iceqube_temperatures', 'get_iceqube_setpoint', 'set_iceqube_setpoint',
           'get_iceqube_cooling_offset', 'set_iceqube_cooling_offset',
           'get_webrelay_status', 'get_webrelay_state', 'set_webrelay_state']


def _temp_to_value(degreesF):
    """
    Convert a temperature in Fahrenheit into a value acceptable to an IceQube
    controller
    """
    
    return round(((degreesF * 2) - 64) * 5 / 9.)


def _value_to_temp(value):
    """
    Convert a temperature from an IceQube controller into Fahrenheit
    """
    
    return ((value * 9 / 5.) + 64) / 2.


def _tdiff_to_value(delta_degreesF):
    """
    Convert a temperature difference/offset in Fahrenheit into a value
    acceptable to an IceQube controller
    """
    
    return round(delta_degreesF * 10 / 9.)


def _value_to_tdiff(value):
    """
    Convert a temperature difference/offset from an IceQube controller into a
    differnce/offswet in Fahrenheit
    """
    
    return value * 9 / 10.


class IceQubeAccessLimiter(object):
    """
    Context manager to make sure we do not send too many commands to the IceQube
    controller at once
    """
    
    def __init__(self, wait_time=1.0):
        self._wait_time = float(wait_time)
        self._last_request = 0.0
        self._lock = threading.RLock()
        
    def __enter__(self):
        self._lock.acquire()
        while time.time() - self._last_request < self._wait_time:
            time.sleep(0.1)
            
        return self
        
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._last_request = time.time()
        self._lock.release()


_IQAL = IceQubeAccessLimiter()


def get_iceqube_status(ip_address):
    """
    Poll the IceQube controller at the provided address and return dictionary of
    the current status (cooling, heating, alarm, and filter).  Returns None if
    there was a problem communicating with the controller.
    """
    
    value = None
    
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/ledstate.cgi",
                                   timeout=20)
            value = int(response.text)
            
            value = {'cooling': bool(value & 8),
                     'heating': bool(value & 4),
                     'alarm':   bool(value & 2),
                     'filter':  bool(value & 1)}
        except Exception as e:
            shlQubeLogger.warn("Failed to retrieve status from %s: %s", ip_address, str(e))
            
    return value


def get_iceqube_lead_status(ip_address):
    """
    Poll the IceQube controller at the provided address and return if the unit
    is current the lead unit.  Returns True if it is, False if it is not, or
    None if an error occurred.
    """
    
    value = None
    
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/display.cgi",
                                   timeout=20)
            value = (response.text.find('LEAD') != -1)
        except Exception as e:
            shlQubeLogger.warn("Failed to retrieve status from %s: %s", ip_address, str(e))
            
    return value


def get_iceqube_settings(ip_address):
    """
    Poll the IceQube controller at the provided address for the complete list of
    user settings as a `xml.etree.ElementTree` instance.  If the settings cannot
    be loaded None is returned instead.
    """
    
    settings = None
    
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/usersettings.xml",
                                   timeout=20)
            settings = ET.fromstring(response.text)
        except Exception as e:
            shlQubeLogger.warn("Failed to retrieve settings from %s: %s", ip_address, str(e))
            
    return settings


def get_iceqube_temperatures(ip_address):
    """
    Poll the IceQube controller at the provided address for the current
    temperature of the enclosure and the condenser.  Returns a dictionary
    with the values or None if there was a problem.
    """
    
    value = None
    
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/temperatures.cgi",
                                   timeout=20)
            enc, etemp, con, ctemp = response.text.split(None, 3)
            enc = enc.lower().replace(':', '')
            etemp = float(etemp.replace('F', ''))
            con = con.lower().replace(':', '')
            ctemp = float(ctemp.replace('F', ''))
            value = {enc: etemp, con: ctemp}
        except Exception as e:
            shlQubeLogger.warn("Failed to retrieve temperatures from %s: %s", ip_address, str(e))
            
    return value


def get_iceqube_setpoint(ip_address):
    """
    Poll the IceQube controller at the provided address and return the current
    set point in Fahrenheit.  Returns None if there was a problem communicating
    with the controller.
    """
    
    value = None
    
    with _IQAL:
        try:
            settings = get_iceqube_settings(ip_address)
            value = settings.find('COOLON').text
            value = float(value) * 9 / 5. + 32
            value = round(value)
        except Exception as e:
            shlQubeLogger.warn("Failed to retrieve setpoint from %s: %s", ip_address, str(e))
            
    return value


def set_iceqube_setpoint(ip_address, setpoint):
    """
    Set the setpoint (in degrees F) of the IceQube controller at the provided
    address.  Return True if successful, False otherwise.
    """
    
    value = _temp_to_value(setpoint)
    status = False
    
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/1?07={value}&30=1&2F=1",
                                   timeout=20)
            if response.text.startswith('Settings have been updated'):
                status = True
        except Exception as e:
            shlQubeLogger.error("Failed to set setpoint on %s: %s", ip_address, str(e))
            
    return status


def get_iceqube_cooling_offset(ip_address):
    """
    Poll the IceQube controller at the provided address and return the current
    cooling offset in Fahrenheit.  Return None if a problem was encountered.
    """
    
    offset = None
    
    settings = get_iceqube_settings(ip_address)
    if settings is not None:
        offset = settings.find('COOL_OFFSET').text
        if offset == 'T':
            offset = 0.0
        else:
            offset = float(offset)
        offset = _value_to_tdiff(offset)
            
    return offset
 
 
def set_iceqube_cooling_offset(ip_address, offset):
    """
    Set the cooling offset (in degrees F) of the IceQube controller at the
    provided address.  Return True if successful, False otherwise.
    """
    
    value = _tdiff_to_value(offset)
    status = False
    
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/1?92={value}&30=1&2F=1",
                                   timeout=20)
            if response.text.startswith('Settings have been updated'):
                status = True
        except Exception as e:
            shlQubeLogger.error("Failed to set cooling offset on %s: %s", ip_address, str(e))
            
    return status


def get_webrelay_status(ip_address):
    """
    Return the status of a WebRelay-10 device.  Returns a complete list of the
    device's status as a `xml.etree.ElementTree` instance.  If the status
    cannot be loaded None is returned instead.
    """
    
    status = None
    with _IQAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/state.xml",
                                   timeout=20)
            status = ET.fromstring(response.text)
        except Exception as e:
            shlQubeLogger.error("Failed to query WebRelay-10 status: %s", str(e))
            
    return status


def get_webrelay_state(ip_address, relay):
    """
    Return the status of a particular relay (or list of relays) controlled by
    a WebRelay-10 device.  Return the relay state(s) as integers or None if
    there was a problem querying the device.
    """
    
    is_list = True
    if not isinstance(relay, (tuple, list)):
        is_list = False
        relay = [relay,]
    for r in relay:
        if r < 0 or r > 10:
            raise ValueError(f"Invalid relay '{r}'")
            
    status = get_webrelay_status(ip_address)
    
    state = None
    if status is not None:
        state = []
        for r in relay:
            for child in status:
                if child.tag == f"relay{r}state":
                    state.append(int(child.text))
                    
    if not is_list:
        state = state[0]
        
    return state
            
            
def set_webrelay_state(ip_address, relay, state):
    """
    Control a WebRelay-10 device to set the specified relay (or list of relays)
    to the provided state.  Valid states are 0 = off, 1 = on, 2 = power cycle.
    Return True if successful, False otherwise.
    """
    
    if not isinstance(relay, (tuple, list)):
        relay = [relay,]
    for r in relay:
        if r < 0 or r > 10:
            raise ValueError(f"Invalid relay '{r}'")
    if state not in (0, 1, 2):
        raise ValueError(f"Invalid state '{state}'")
        
    status = False
    with _IQAL:
        try:
            qs = ''
            for r in relay:
                qs += f"relay{r}State={state}&"
            qs = qs[:-1]
            
            session = requests.Session()
            response = session.get(f"http://{ip_address}/state.xml?{qs}",
                                   timeout=20)
            status = True
        except Exception as e:
            shlQubeLogger.error("Failed to set WebRelay-10 relay %s state: %s", str(relay), str(e))
            
    return status
