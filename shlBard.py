
import time
import logging
import requests
import threading
import xml.etree.ElementTree as ET

shlBardLogger = logging.getLogger('__main__')

__version__ = '0.1'
__all__ = ['get_mc4002_status', 'get_mc4002_alarms', 'get_mc4002_lead_status',
           'set_mc4002_lead_status', 'get_mc4002_setpoint', 'set_mc4002_setpoint',
           'get_mc4002_cooling_offset', 'set_mc4002_cooling_offset']


class MC4002AccessLimiter(object):
    """
    Context manager to make sure we do not send too many commands to the MC4002
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


_MCAL = MC4002AccessLimiter()


def get_mc4002_status(ip_address):
    """
    Poll the MC4002 controller at the provided address and return dictionary of
    the current status (cooling, cooling stage(s) active, heating, heating
    stage(s) active, and alarm).  Returns None if there was a problem
    communicating with the controller.
    """
    
    value = None
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/System/index_stat.xml",
                                   timeout=20)
            settings = ET.fromstring(response.text)
            
            # Heating/cooling status
            heat_cool = settings.find('HeatPmp').text
            
            # Heating/cooling stage
            cool_stage = 0
            for l in range(4):
                cool_stage += (settings.find(f"LED{l}").text != 'OFF')
            heat_stage = 0
            for l in range(4):
                heat_stage += (settings.find(f"LED{l+4}").text != 'OFF')
            
            # Alarms - a union of:
            #  * unit power states
            #  * fire/smoke
            #  * low temperature")
            #  * high temperature 1
            #  * high temperature 2
            #  * controller failure
            alarm = False
            for c in range(2):
                alarm |= (settings.find(f"Row_5_{c}").text != 'CLEAR')
            for a in range(5):
                alarm |= (settings.find(f"GA{a}").text != 'CLEAR')
            
            value = {'cooling': heat_cool.startswith('Cool'),
                     'cooling_stage': cool_stage,
                     'heating': heat_cool.startswith('Heat'),
                     'heating_stage': heat_stage,
                     'alarm':   alarm}
        except Exception as e:
            shlBardLogger.warn("Failed to retrieve status from %s: %s", ip_address, str(e))
            
    return value


def get_mc4002_alarms(ip_address):
    """
    Poll the MC4002 controller at the provided address and return a list of alarm
    codes that are asserted.  Returns None if there was a problem communicating
    with the controller.
    """
    
    value = None
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/System/index_stat.xml",
                                   timeout=20)
            settings = ET.fromstring(response.text)
            
            alarms = []
            for c in range(2):
                if settings.find(f"Row_5_{c}").text != 'CLEAR':
                    alarms.append(f"power loss {c+1}")
            alarm_mapping = {0: 'fire/smoke',
                             1: 'low temperature',
                             2: 'high temperature 1',
                             3: 'high temperature 2',
                             4: 'controller failure'}
            for a in range(5):
                if settings.find(f"GA{a}").text != 'CLEAR':
                    alarms.append(alarm_mapping[a])
            value = alarms
        except Exception as e:
            shlBardLogger.warn("Failed to retrieve list of asserted alarms from %s: %s", ip_address, str(e))
            
    return value


def get_mc4002_lead_status(ip_address):
    """
    Poll the MC4002 controller at the provided address and return if the unit
    is current the lead unit.  Returns 1 if the first unit is in lead, 2 if the
    second is, or None if an error occurred.
    """
    
    lead = None
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/System/index_stat.xml",
                                   timeout=20)
            settings = ET.fromstring(response.text)
            
            lead = (settings.find(f"Row_4_1").text == 'LEAD') + 1
        except Exception as e:
            shlBardLogger.warn("Failed to retrieve status from %s: %s", ip_address, str(e))
            
    return lead


def set_mc4002_lead_status(ip_address):
    status = False
    
    with _MCAL:
        try:
            lead = get_mc4002_lead_status(ip_address) ^ 3
            
            session = requests.Session()
            response = session.post(f"http://{ip_address}/System/setpoints.htm",
                                    data={'Row': 31,
                                          'Value': f"Unit {lead} Lead"},
                                    timeout=20)
            
            new_lead = get_mc4002_lead_status(ip_address)
            status = (lead == new_lead)
        except Exception as e:
            shlBardLogger.warn("Failed to retrieve status from %s: %s", ip_address, str(e))
            
    return status


def get_mc4002_setpoint(ip_address):
    """
    Poll the MC4002 controller at the provided address and return the current
    set point in Fahrenheit.  Returns None if there was a problem communicating
    with the controller.
    """
    
    value = None
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/System/setpoints_stat.xml",
                                   timeout=20)
            settings = ET.fromstring(response.text)
            
            value = int(settings.find('Row_0').text, 10) + 65
        except Exception as e:
            shlBardLogger.warn("Failed to retrieve setpoint from %s: %s", ip_address, str(e))
            
    return value


def set_mc4002_setpoint(ip_address, setpoint):
    """
    Set the setpoint (in degrees F) of the MC4002 controller at the provided
    address.  Return True if successful, False otherwise.
    """
    
    setpoint = int(round(float(setpoint)))
    status = False
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.post(f"http://{ip_address}/System/setpoints.htm",
                                    data={'Row': 0,
                                          'Value': setpoint},
                                    timeout=20)
            
            new_setpoint = get_mc4002_setpoint(ip_address)
            status = (setpoint == new_setpoint)
        except Exception as e:
            shlBardLogger.error("Failed to set setpoint on %s: %s", ip_address, str(e))
            
    return status


def get_mc4002_cooling_offset(ip_address):
    """
    Poll the MC4002 controller at the provided address and return the current
    cooling offset in Fahrenheit.  Return None if a problem was encountered.
    """
    
    offset = None
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.get(f"http://{ip_address}/System/setpoints_stat.xml",
                                   timeout=20)
            settings = ET.fromstring(response.text)
            
            offset = int(settings.find('Row_12').text, 10) + 1
        except Exception as e:
            shlBardLogger.error("Failed to retrieve cooling offset on %s: %s", ip_address, str(e))
            
    return offset


def set_mc4002_cooling_offset(ip_address, offset):
    """
    Set the cooling offset (in degrees F) of the MC4002 controller at the
    provided address.  Return True if successful, False otherwise.
    """
    
    offset = int(round(float(offset)))
    status = False
    
    with _MCAL:
        try:
            session = requests.Session()
            response = session.post(f"http://{ip_address}/System/setpoints.htm",
                                    data={'Row': 12,
                                          'Value': {offset}},
                                    timeout=20)
            
            new_offset = get_mc4002_cooling_offset(ip_address)
            status = (offset == new_offset)
        except Exception as e:
            shlBardLogger.error("Failed to set cooling offset on %s: %s", ip_address, str(e))
            
    return status
