from __future__ import division
import math
import base64
from string import ascii_letters, digits
from collections import MutableMapping, defaultdict
import pymel.core as pm
import time
import sys
import datetime

def get_defaultdict():
    for k, v in globals().iteritems():
        v = str(v)
        if any(i in v for i in ("function defaultdict", "<type 'collections.defaultdict'>")):
            return eval(k)
        if "module 'collections'" in v:
            return eval(k + '.defaultdict')
    return 'invalid'

def int_to_bin(x, padding=0):
    return ('{' + '0:0{}b'.format(padding) + '}').format(x)

def convert_to_bytes(x):
    x_len = len(x)
    if x_len % 8:
        x += '0' * (8 - x_len % 8)
    as_list = [int(x[i:i + 8], 2) for i in range(0, len(x), 8)]
    return ''.join(chr(i) for i in as_list)

def convert_from_bytes(x):
    return ''.join(int_to_bin(i, 8) for i in x)

class StoreData:
    _dd = get_defaultdict()
    TYPES = [bool, int, str, dict, list, tuple, float, unicode, tuple, complex, type(None), set, _dd, 'other']
    _TYPES = {long: int} #Treat the key type as the value type
    TYPE_LEN = int(math.ceil(math.log(len(TYPES), 2)))
    LOC = 'C:/Users/Peter/AppData/Roaming/IndexDataTest'
    #need to fix float('inf') and defaultdict
    
    def save(self, x):
        data = base64.b64encode(convert_to_bytes(self._encode_value(x)))
        return data
    
    def load(self, x):
        data, offset = self._decode_value(convert_from_bytes(bytearray(base64.b64decode(x))))
        return data
    
    def _encode_value(self, x, _int_force_negative=False):
        item_type = type(x)
        if item_type in self._TYPES:
            item_type = self._TYPES[item_type]
        
        if item_type not in self.TYPES:
            #print "Warning: {} is not offically supported".format(item_type)
            item_type = 'other'
            x = str(x)
            try:
                eval(x)
            except SyntaxError:
                raise ValueError('unable to decode {} from string'.format(item_type))
        
        type_id = self.TYPES.index(item_type)
        encoded_string = int_to_bin(type_id, self.TYPE_LEN)
        
        #Get the length of the input
        if item_type == bool:
            item_bin = str(int(bool(x)))
            return encoded_string + '1' + item_bin
        
        elif item_type == type(None):
            return encoded_string + '10'

        if item_type in (int, str, unicode, 'other'):
            if item_type == int:
                item_bin = int_to_bin(x).replace('-', '')
                
            elif item_type in (str, unicode, 'other'):
                item_bin = ''.join(int_to_bin(ord(i), 8) for i in x)
                
            item_len = len(item_bin)
            num_bytes_int = (item_len - 1) // 8 + 1
            
        elif item_type in (float, complex):
            num_bytes_int = 2
        
        elif item_type in (list, tuple, dict, set):
            num_bytes_int = len(x)
       
        elif item_type == self._dd:
            num_bytes_int = len(x) + 1
            
        #Convert input length into number of bytes
        num_bytes_bin = int_to_bin(num_bytes_int)
        num_bytes_len = len(num_bytes_bin)
        if num_bytes_len % 8:
            num_bytes_bin = '0' * (8 - num_bytes_len % 8) + num_bytes_bin
        
        num_bytes_len = (len(num_bytes_bin) - 1) // 8 + 1
        
        encoded_string += '0' * (num_bytes_len - 1) + '1'
        encoded_string += num_bytes_bin
        
        #Convert input to bytes
        if item_type in (int, str, unicode, 'other'):
            
            if item_type == int:
                encoded_string += '0' if x > 0 else '1'
            
            remaining_bits = item_len % 8
            if remaining_bits:
                item_bin = '0' * (8 - item_len % 8) + item_bin
            
            encoded_string += item_bin
            
        elif item_type == float:
            x_split = str(x).split('.')
            encoded_string += '0' if x >= 0 else '1'
            encoded_string += self._encode_value(int(x_split[0]))
            encoded_string += self._encode_value(x_split[1])
        
        elif item_type == complex:
            encoded_string += self._encode_value(x.real)
            encoded_string += self._encode_value(x.imag)
        
        elif item_type in (list, tuple, set):
            for i in x:
                encoded_string += self._encode_value(i)
                
        elif item_type == self._dd:
            dd_type = type(defaultdict(_MovementInfo).default_factory())
            dd_type = str(dd_type).replace("<class '__main__.", '').replace("'>", '')
            encoded_string += self._encode_value(str(dd_type))
            for k, v in x.iteritems():
                encoded_string += self._encode_value(k)
                encoded_string += self._encode_value(v)
            
        elif item_type == dict:
            for k, v in x.iteritems():
                encoded_string += self._encode_value(k)
                encoded_string += self._encode_value(v)
                
        return encoded_string

    def _decode_value(self, x, start=0):
        
        #Find the item type
        start_offset = start
        end_offset = start_offset + self.TYPE_LEN
        type_id = int(x[start_offset:end_offset], 2)
        item_type = self.TYPES[type_id]
        
        #Find how many bytes the number of bytes is
        byte_length = 0
        while not int(x[end_offset + byte_length]):
            byte_length += 1
        byte_length += 1
        
        #Calculate the number of bytes
        start_offset = end_offset + byte_length
        end_offset = start_offset + byte_length * 8
        num_bytes = int(x[start_offset:end_offset], 2)
        
        #Decode the rest
        if item_type in (int, str, unicode, 'other'):
            start_offset = end_offset
            
            if item_type == int:
                is_negative = int(x[start_offset])
                start_offset += 1
            
            end_offset = start_offset + num_bytes * 8
            data = x[start_offset:end_offset]
            
            if item_type == int:
                data = int(data, 2) * (-1 if is_negative else 1)
                
            elif item_type in (str, unicode, 'other'):
                data = ''.join(chr(int(data[i:i + 8], 2)) for i in range(0, len(data), 8))
                
                if item_type == 'other':
                    data = eval(data)
                    #type(defaultdict(_MovementInfo).default_factory())
                    
        
        elif item_type in (list, tuple, set):
            data = []
            for i in range(num_bytes):
                value, end_offset = self._decode_value(x, start=end_offset)
                data.append(value)
            if item_type == tuple:
                data = tuple(data)
            elif item_type == set:
                data = set(data)
        
        elif item_type == dict:
            data = {}
            for i in range(num_bytes):
                k, end_offset = self._decode_value(x, start=end_offset)
                v, end_offset = self._decode_value(x, start=end_offset)
                data[k] = v
        
        elif item_type == self._dd:
            default_type, end_offset = self._decode_value(x, start=end_offset)
            #print default_type
            #eval(default_type)
            try:
                data = self._dd(eval(default_type))
            except SyntaxError:
                raise ValueError("an unknown variable type was encoded, can't decode")
            for i in range(num_bytes - 1):
                k, end_offset = self._decode_value(x, start=end_offset)
                v, end_offset = self._decode_value(x, start=end_offset)
                #print k, v
                data[k] = v
                
        elif item_type == float:
            data = []
            is_negative = int(x[end_offset])
            end_offset += 1
            for i in range(2):
                value, end_offset = self._decode_value(x, start=end_offset)
                data.append(str(value))
            data = float('.'.join(data)) * (-1 if is_negative else 1)
        
        elif item_type == complex:
            data = []
            for i in range(2):
                value, end_offset = self._decode_value(x, start=end_offset)
                data.append(str(value))
            data = map(float, data)
            data = data[0] + data[1] * 1j
        
        elif item_type == bool:
            end_offset = start_offset + 1
            data = bool(int(x[start_offset:end_offset]))
        
        elif item_type == type(None):
            end_offset = start_offset + 1
            data = None
        
        return data, end_offset


    def _decode_file(self, f, start=0):
        
        #Find the item type
        start_offset = start
        end_offset = start_offset + self.TYPE_LEN
        f.seek(start_offset)
        type_id = int(f.read(self.TYPE_LEN), 2)
        item_type = self.TYPES[type_id]
        
        #Find how many bytes the number of bytes is
        byte_length = 0
        #while not int(x[end_offset + byte_length]):
        while not int(f.read(1)):
            byte_length += 1
        byte_length += 1
        
        #Calculate the number of bytes
        start_offset = end_offset + byte_length
        end_offset = start_offset + byte_length * 8
        x = f.read(byte_length * 8)
        #num_bytes = int(x[start_offset:end_offset], 2)
        num_bytes = int(x, 2)
        
        #Decode the rest
        if item_type in (int, str, unicode):
            start_offset = end_offset
            
            if item_type == int:
                #f.seek(start_offset)
                x = f.read(1)
                is_negative = int(x)
                start_offset += 1
            
            end_offset = start_offset + num_bytes * 8
            #f.seek(start_offset)
            x = f.read(num_bytes * 8)
            data = x
        
            if item_type == int:
                data = int(data, 2) * (-1 if is_negative else 1)
                
            elif item_type in (str, unicode):
                data = ''.join(chr(int(data[i:i + 8], 2)) for i in range(0, len(data), 8))
        
        elif item_type in (list, tuple):
            data = []
            for i in range(num_bytes):
                value, end_offset = self._decode_file(f, start=end_offset)
                data.append(value)
            if item_type == tuple:
                data = tuple(data)
        
        elif item_type == dict:
            data = {}
            for i in range(num_bytes):
                k, end_offset = self._decode_file(f, start=end_offset)
                v, end_offset = self._decode_file(f, start=end_offset)
                data[k] = v
        
        elif item_type == float:
            data = []
            x = f.read(1)
            is_negative = int(x)
            end_offset += 1
            for i in range(2):
                value, end_offset = self._decode_file(f, start=end_offset)
                data.append(str(value))
            data = float('.'.join(data)) * (-1 if is_negative else 1)
        
        elif item_type == complex:
            data = []
            for i in range(2):
                value, end_offset = self._decode_file(f, start=end_offset)
                data.append(str(value))
            data = map(float, data)
            data = data[0] + data[1] * 1j
        
        elif item_type == bool:
            end_offset = start_offset + 1
            x = f.read(1)
            data = bool(int(x))
        
        elif item_type == type(None):
            end_offset = start_offset + 1
            data = None
        
        return data, end_offset

    def _savefile(self, x):
        data = self._encode_value(x)
        remainder = len(data) % 8
        if remainder:
            data += '0' * (8 - remainder)
            
        with open(self.LOC, 'w') as f:
            f.write(data)
    
    def _readfile(self):
        with open(self.LOC, 'r') as f:
            data, offset = self._decode_file(f)
        return data


class _MovementInfo(object):
    def __init__(self, location_data=None, location_absolute=None, rotation_data=None, rotation_absolute=None, scale_data=None, scale_absolute=None, visibility_data=None, visibility_absolute=None):
        self.location_coordinates = location_data
        self.rotation_coordinates = rotation_data
        self.scale_coordinates = scale_data
        self.visibility_coordinates = visibility_data
        self.location_absolute = location_absolute
        self.rotation_absolute = rotation_absolute
        self.scale_absolute = scale_absolute
        self.visibility_absolute = visibility_absolute
    
    def __repr__(self):
        return ('{x.__class__.__name__}(location_data={x.location_coordinates}, '
                                       'location_absolute={x.location_absolute}, '
                                       'rotation_data={x.rotation_coordinates}, '
                                       'rotation_absolute={x.rotation_absolute}, '
                                       'scale_data={x.scale_coordinates}, '
                                       'scale_absolute={x.scale_absolute}, '
                                       'visibility_data={x.location_coordinates}, '
                                       'visibility_absolute={x.visibility_absolute})').format(x=self)
    
    def __eq__(self, other):
        if type(other) != _MovementInfo:
            return False
        return (self.location_coordinates == other.location_coordinates 
                and self.rotation_coordinates == other.rotation_coordinates 
                and self.scale_coordinates == other.scale_coordinates 
                and self.visibility_coordinates == other.visibility_coordinates
                and self.location_absolute == other.location_absolute
                and self.rotation_absolute == other.rotation_absolute
                and self.scale_absolute == other.scale_absolute
                and self.visibility_coordinates == other.visibility_coordinates
                )


def load_data(attempt=0):
    try:
        return StoreData().load(str(pm.fileInfo['AssemblyScript']))
    except KeyError:
        pm.fileInfo['AssemblyScript'] = StoreData().save({})
        if not attempt:
            return load_data(attempt + 1)
        else:
            return {}

def save_data(data):
    pm.fileInfo['AssemblyScript'] = StoreData().save(data)

class SetGroup(_MovementInfo):
    
    def __init__(self, name=None, offset=0.0, distance=0.0, random=0.0, selection=None, origin=(0.0, 0.0, 0.0), bounce=0.0, list_order=None):
        
        if name is None:
            raise TypeError('name of group must be provided')
        self.name = name
        
        #super(SetGroup, self).__init__(location, rotation, scale, visibility)
        
        if selection is None:
            self.selection = []
        else:
            self.selection = selection
        self.origin = origin
        
        self.bounce = bounce
        
        self.offset = offset
        self.distance = distance
        self.random = random
        
        
        self.frame = defaultdict(_MovementInfo)
        self.frame[0.0]
        self.frame[5.0]
        self.frame[50.0]
        self.frame[10.0]
        
        self.list_order = list_order
    
    def __repr__(self):
        return '{x.__class__.__name__}()'.format(x=self)
    
    def validate(self):
        if self.selection is None:
            raise TypeError('selection is not defined')
        elif not self.selection:
            raise TypeError('selection is empty')
        elif not isinstance(self.selection, (tuple, list)):
            raise TypeError('selection must be a tuple or list')
    
    def save(self):
        self.load()
        #self.validate()
        self.data[self.name] = {'ObjectSelection': set(self.selection),
                                'ObjectOrigin': self.origin,
                                'FrameOffset': self.offset,
                                'FrameDistance': self.distance,
                                'BounceDistance': self.bounce,
                                'RandomOffset': self.random,
                                'Axis': (False, False, False),
                                'ListOrder': self.list_order,
                                'Frames': self.frame}
        pm.fileInfo['AssemblyScript'] = StoreData().save(self.data)

    def load(self):
        self.data = load_data()
    

class UserInterface(object):
    name = 'Assembler'
    
    def __init__(self):
        self._reset_settings()
        self.inputs = defaultdict(dict)
        self.reload()
        self._group_new_count = 0
        self._group_unsaved = []
    
    def _reset_settings(self, _debug=0):
        try:
            existing_scriptjobs = self._settings['ScriptJobs']
        except AttributeError:
            existing_scriptjobs = []
        self._settings = {'GroupObjects': set(),
                          'GroupName': None,
                          'HideSelected': True,
                          'CurrentFrame': None,
                          'LastFrameSelection': {},
                          'LastFrameData': defaultdict(lambda: defaultdict(dict)),
                          'ScriptJobs': existing_scriptjobs
                          }
    
    def reload(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Reload all', indent=_debug)
        self.data = load_data()
        self._original_data = load_data()
        self.reload_objects(_debug=_debug + 1)
    
    def reload_objects(self, _debug=0):
        """Refresh the list of objects."""
        self._debug_print(sys._getframe().f_code.co_name, 'Objects: Rebuild list', indent=_debug)
        
        #Get a list of all scene objects (without cameras)
        scene_objects = pm.ls(dag=True, exactType=pm.nodetypes.Transform)
        for cam_name in (i.replace('Shape', '') for i in pm.ls(exactType=pm.nodetypes.Camera)):
            try: 
                del scene_objects[scene_objects.index(pm.nodetypes.Transform(cam_name))]
            except (pm.MayaNodeError, ValueError):
                pass
        self.scene_objects = set(map(str, scene_objects))
        
    def display(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Draw user interface', indent=_debug)
        
        self.reload(_debug=_debug + 1)
        
        if pm.window(self.name, exists=True):
            pm.deleteUI(self.name, window=True)

        self.win = pm.window(self.name, title=self.name, sizeable=True, resizeToFitChildren=True)
        #pm.scriptJob(event=('SelectionChanged', self.test), parent=win)
        pm.scriptJob(event=('DagObjectCreated', self._objects_refresh), parent=self.win)
        
        with pm.rowColumnLayout(numberOfColumns=1):
            with pm.rowColumnLayout(numberOfColumns=5):
                with pm.rowColumnLayout(numberOfColumns=1):
                    
                    with pm.rowColumnLayout(numberOfColumns=3):
                        pm.text(label='Group Selection', align='left')
                        pm.text(label='')
                        self.inputs[pm.textScrollList]['Groups'] = pm.textScrollList(allowMultiSelection=False, append=['error'], height=100, selectCommand=pm.Callback(self._group_select_new))
                        
                        pm.text(label='')
                        pm.text(label='')
                        with pm.rowColumnLayout(numberOfColumns=9):
                            self.inputs[pm.button]['GroupAdd'] = pm.button(label='+', command=pm.Callback(self._group_add))
                            pm.text(label='')
                            self.inputs[pm.button]['GroupRemove'] = pm.button(label='-', command=pm.Callback(self._group_delete))
                            pm.text(label='')
                            self.inputs[pm.button]['GroupMoveUp'] = pm.button(label='^', command=pm.Callback(self._group_up))
                            pm.text(label='')
                            self.inputs[pm.button]['GroupMoveDown'] = pm.button(label='v', command=pm.Callback(self._group_down))
                            pm.text(label='')
                            self.inputs[pm.button]['GroupClean'] = pm.button(label='Remove empty groups', command=pm.Callback(self._group_clean))
                                      
                        pm.text(label='Object Selection')
                        pm.text(label='')
                        self.inputs[pm.textScrollList]['AllObjects'] = pm.textScrollList(allowMultiSelection=True, append=['error'], height=200, selectCommand=pm.Callback(self._objects_select))
                       
                        pm.text(label='')      
                        pm.text(label='')      
                        with pm.rowColumnLayout(numberOfColumns=3):
                            self.inputs[pm.button]['ObjectRefresh'] = pm.button(label='Refresh', command=pm.Callback(self._objects_refresh))
                            pm.text(label='')
                            self.inputs[pm.checkBox]['ObjectHide'] = pm.checkBox(label='Hide selected objects', value=self._settings['HideSelected'], changeCommand=pm.Callback(self._objects_hide))
            
                pm.text(label='')
                    
                with pm.rowColumnLayout(numberOfColumns=1):
                    with pm.rowColumnLayout(numberOfColumns=3):
                        pm.text(label='Group Name', align='right')
                        pm.text(label='')
                        self.inputs[pm.textField]['GroupName'] = pm.textField(text='error', changeCommand=pm.Callback(self._group_name_save))
                        pm.text(label='Frame Offset', align='right')
                        pm.text(label='')
                        self.inputs[pm.floatSliderGrp]['FrameOffset'] = pm.floatSliderGrp(field=True, value=0, fieldMinValue=-float('inf'), fieldMaxValue=float('inf'), minValue=-1000, maxValue=1000, precision=2, changeCommand=pm.Callback(self._group_settings_save))
                        pm.text(label='Random Offset', align='right')
                        pm.text(label='')
                        self.inputs[pm.floatSliderGrp]['RandomOffset'] = pm.floatSliderGrp(field=True, value=0, fieldMinValue=0, fieldMaxValue=float('inf'), precision=2, changeCommand=pm.Callback(self._group_settings_save))
                        pm.text(label='Overshoot Distance', align='right')
                        pm.text(label='')
                        self.inputs[pm.floatSliderGrp]['BounceDistance'] = pm.floatSliderGrp(field=True, value=0, fieldMinValue=0, fieldMaxValue=float('inf'), precision=2, changeCommand=pm.Callback(self._group_settings_save))
                        pm.text(label='')
                        pm.text(label='')
                        pm.text(label='')
                        pm.text(label='Distance Per Frame', align='right')
                        pm.text(label='')
                        self.inputs[pm.floatSliderGrp]['DistanceUnits'] = pm.floatSliderGrp(field=True, value=100, fieldMinValue=0, fieldMaxValue=float('inf'), maxValue=1000, precision=2, changeCommand=pm.Callback(self._group_settings_save))
                        pm.text(label='Animation Origin', align='right')
                        pm.text(label='')
                        with pm.rowColumnLayout(numberOfColumns=3):
                            self.inputs[pm.textField]['OriginX'] = pm.textField(text='error', changeCommand=pm.Callback(self._group_settings_save))
                            self.inputs[pm.textField]['OriginY'] = pm.textField(text='error', changeCommand=pm.Callback(self._group_settings_save))
                            self.inputs[pm.textField]['OriginZ'] = pm.textField(text='error', changeCommand=pm.Callback(self._group_settings_save))
                        pm.text(label='')
                        pm.text(label='')
                        self.inputs[pm.button]['OriginApply'] = pm.button(label='Use Current Selection', command=pm.Callback(self._set_origin_location))
                        
                        pm.text(label='Animation Axis', align='right')
                        pm.text(label='')
                        with pm.rowColumnLayout(numberOfColumns=5):
                            self.inputs[pm.checkBox]['OriginX'] = pm.checkBox(label='X', value=False, changeCommand=pm.Callback(self._group_settings_save))
                            pm.text(label='')
                            self.inputs[pm.checkBox]['OriginY'] = pm.checkBox(label='Y', value=False, changeCommand=pm.Callback(self._group_settings_save))
                            pm.text(label='')
                            self.inputs[pm.checkBox]['OriginZ'] = pm.checkBox(label='Z', value=False, changeCommand=pm.Callback(self._group_settings_save))
                        pm.text(label='')
                        pm.text(label='')
                        pm.text(label='')
                        pm.text(label='Frame Selection', align='right')
                        
                        pm.text(label='')
                        self.inputs[pm.textScrollList]['FrameSelection'] = pm.textScrollList(allowMultiSelection=False, append=['error'], height=100, selectCommand=pm.Callback(self._frame_select_new))
                        pm.text(label='')
                        pm.text(label='')
                        with pm.rowColumnLayout(numberOfColumns=3):
                            self.inputs[pm.button]['FrameAdd'] = pm.button(label='+', command=pm.Callback(self._frame_add))
                            pm.text(label='')
                            self.inputs[pm.button]['FrameRemove'] = pm.button(label='-', command=pm.Callback(self._frame_remove))

                pm.text(label='')
                    
                with pm.scrollLayout():
                    with pm.rowColumnLayout(numberOfColumns=1):
                        with pm.rowColumnLayout(numberOfColumns=3):
                            pm.text(label='Frame', align='right')
                            pm.text(label='')
                            self.inputs[pm.floatSliderGrp]['CurrentFrame'] = pm.floatSliderGrp(field=True, value=0, fieldMinValue=-float('inf'), fieldMaxValue=float('inf'), precision=2, changeCommand=pm.Callback(self._frame_change))
                        
                        with pm.frameLayout(label='Location', collapsable=False, collapse=False) as self.inputs[pm.frameLayout]['Location']:
                            with pm.tabLayout(tabsVisible=False):
                                with pm.rowColumnLayout(numberOfColumns=1):
                                    self.inputs[pm.checkBox]['FrameLocDisable'] = pm.checkBox(label='Disable', value=True, changeCommand=pm.Callback(self._frame_data_disable))
                                    with pm.rowColumnLayout(numberOfColumns=7):
                                        self.inputs[pm.text]['FrameLocCoordinates'] = pm.text(label='Coordinates', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.text]['FrameLocMin'] = pm.text(label='min', align='center')
                                        pm.text(label='')
                                        self.inputs[pm.text]['FrameLocMax'] = pm.text(label='max', align='center')
                                        pm.text(label='')
                                        self.inputs[pm.text]['FrameLocJoin'] = pm.text(label='join', align='center')
                                        self.inputs[pm.text]['FrameLocX'] = pm.text(label='x', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameLocXMin'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameLocXMax'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.checkBox]['FrameLocXJoin'] = pm.checkBox(label='', value=True, changeCommand=pm.Callback(self._frame_data_join))
                                        self.inputs[pm.text]['FrameLocY'] = pm.text(label='y', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameLocYMin'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameLocYMax'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.checkBox]['FrameLocYJoin'] = pm.checkBox(label='', value=True, changeCommand=pm.Callback(self._frame_data_join))
                                        self.inputs[pm.text]['FrameLocZ'] = pm.text(label='z', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameLocZMin'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameLocZMax'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.checkBox]['FrameLocZJoin'] = pm.checkBox(label='', value=True, changeCommand=pm.Callback(self._frame_data_join))
                                                                                
                                    with pm.rowColumnLayout(numberOfColumns=5):
                                        pm.radioCollection()
                                        self.inputs[pm.radioButton]['FrameLocAbsolute'] = pm.radioButton(label='Absolute', onCommand=pm.Callback(self._relative_frame_change_radio))
                                        with pm.rowColumnLayout(numberOfColumns=2): 
                                            self.inputs[pm.radioButton]['FrameLocRelative'] = pm.radioButton(label='Relative to', select=True, onCommand=pm.Callback(self._relative_frame_change_radio))
                                            self.inputs[pm.radioButton]['FrameLocList'] = pm.optionMenu(label='', changeCommand=pm.Callback(self._relative_frame_change_dropdown))
                                            pm.menuItem(label='Current Location')
                                        pm.text(label='')
                                        pm.text(label='')
                                        pm.text(label='')
                                        
                                        
                        with pm.frameLayout(label='Rotation', collapsable=False, collapse=False) as self.inputs[pm.frameLayout]['Rotation']:
                            with pm.tabLayout(tabsVisible=False):
                                with pm.rowColumnLayout(numberOfColumns=1):
                                    self.inputs[pm.checkBox]['FrameRotDisable'] = pm.checkBox(label='Disable', value=True, changeCommand=pm.Callback(self._frame_data_disable))
                                    with pm.rowColumnLayout(numberOfColumns=7):
                                        self.inputs[pm.text]['FrameRotCoordinates'] = pm.text(label='Coordinates', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.text]['FrameRotMin'] = pm.text(label='min', align='center')
                                        pm.text(label='')
                                        self.inputs[pm.text]['FrameRotMax'] = pm.text(label='max', align='center')
                                        pm.text(label='')
                                        self.inputs[pm.text]['FrameRotJoin'] = pm.text(label='join', align='center')
                                        self.inputs[pm.text]['FrameRotX'] = pm.text(label='x', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameRotXMin'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameRotXMax'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.checkBox]['FrameRotXJoin'] = pm.checkBox(label='', value=True, changeCommand=pm.Callback(self._frame_data_join))
                                        self.inputs[pm.text]['FrameRotY'] = pm.text(label='y', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameRotYMin'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameRotYMax'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.checkBox]['FrameRotYJoin'] = pm.checkBox(label='', value=True, changeCommand=pm.Callback(self._frame_data_join))
                                        self.inputs[pm.text]['FrameRotZ'] = pm.text(label='z', align='right')
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameRotZMin'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.textField]['FrameRotZMax'] = pm.textField(text='error', changeCommand=pm.Callback(self._frame_data_set))
                                        pm.text(label='')
                                        self.inputs[pm.checkBox]['FrameRotZJoin'] = pm.checkBox(label='', value=True, changeCommand=pm.Callback(self._frame_data_join))
                                                        
                                    with pm.rowColumnLayout(numberOfColumns=5):
                                        pm.radioCollection()
                                        self.inputs[pm.radioButton]['FrameRotAbsolute'] = pm.radioButton(label='Absolute', onCommand=pm.Callback(self._relative_frame_change_radio))
                                        with pm.rowColumnLayout(numberOfColumns=2): 
                                            self.inputs[pm.radioButton]['FrameRotRelative'] = pm.radioButton(label='Relative to', select=True, onCommand=pm.Callback(self._relative_frame_change_radio))
                                            self.inputs[pm.radioButton]['FrameRotList'] = pm.optionMenu(label='', changeCommand=pm.Callback(self._relative_frame_change_dropdown))
                                            pm.menuItem(label='Current Rotation')
                                        pm.text(label='')
                                        pm.text(label='')
                                        pm.text(label='')
                    
            with pm.rowColumnLayout(numberOfColumns=5):
                button_width = 50
                button_padding = 10
                pm.text(label=' ' * button_padding)
                pm.text(label=' ' * button_width)
                pm.text(label=' ' * button_padding)
                pm.text(label=' ' * button_width)
                pm.text(label=' ' * button_padding)
                pm.text(label='')
                self.inputs[pm.button]['UIRefresh'] = pm.button(label='Reload', command=pm.Callback(self._refresh_ui))
                pm.text(label='')
                self.inputs[pm.button]['ObjectSave'] = pm.button(label='Save All', command=pm.Callback(self._save_all))
                pm.text(label='')
                pm.text(label='')
                pm.button(label='Print Info', command=pm.Callback(self.generate_animation))
                pm.text(label='')

        self._objects_select(_debug=_debug + 1)
        self._group_select_new(_debug=_debug + 1)
        self._frame_select_new(_debug=_debug + 1)
        self.save(_debug=_debug + 1)
        self._redraw_groups(_debug=_debug + 1)
        self._frame_select_new(_debug=_debug + 1)
        self._relative_frame_redraw(_debug=_debug + 1)
        pm.showWindow()
   
   
    def save(self, original=False, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Save into scene', indent=_debug)
        if original:
            pm.fileInfo['AssemblyScript'] = StoreData().save(self._original_data)
        else:
            pm.fileInfo['AssemblyScript'] = StoreData().save(self.data)
            self._group_unsaved = []
            self._visibility_save(_debug=_debug + 1)
            self.reload(_debug=_debug + 1)
    
    def generate_animation(self, _debug=0):
        self._save_all(_debug=_debug + 1)
        
        spacing = '  '
        
        #print pm.fileInfo['AssemblyScript']
        for frame, data in sorted(self.data.iteritems(), key=lambda (x, y): y['ListOrder']):
            print 'Group: {}'.format(frame)
            
            print '{s}Frame Offset: {}'.format(data['FrameOffset'], s=spacing)
            print '{s}Frame Distance: {}'.format(data['FrameDistance'], s=spacing)
            print '{s}Random Offset: {}'.format(data['RandomOffset'], s=spacing)
            print '{s}Object Origin: {}'.format(data['ObjectOrigin'], s=spacing)
            print '{s}Animation Axis: {}'.format(data['Axis'], s=spacing)
            print '{s}Bounce Distance: {}'.format(data['BounceDistance'], s=spacing)
            print '{s}Keyframes:'.format(s=spacing)
            for keyframe in sorted(data['Frames'].keys()):
                print '{s}{s}{}:'.format(keyframe, s=spacing)
                print '{s}{s}{s}Range: {} to {}'.format(keyframe + data['FrameOffset'] - data['RandomOffset'], keyframe + data['FrameOffset'] + data['RandomOffset'], s=spacing)
                for k, v in {'Location': (data['Frames'][keyframe].location_coordinates, data['Frames'][keyframe].location_absolute),
                             'Rotation': (data['Frames'][keyframe].rotation_coordinates, data['Frames'][keyframe].rotation_absolute),
                             'Scale': (data['Frames'][keyframe].scale_coordinates, data['Frames'][keyframe].scale_absolute),
                             'Visibility': (data['Frames'][keyframe].visibility_coordinates, data['Frames'][keyframe].visibility_absolute)}.iteritems():
                    if v[0] is None:
                        print '{s}{s}{s}{}: Disabled'.format(k, s=spacing)
                    else:
                        print '{s}{s}{s}{}:'.format(k, s=spacing)
                        print '{s}{s}{s}{s}Settings: {}'.format(v[0], s=spacing)
                        print '{s}{s}{s}{s}Absolute/Relative: {}'.format('absolute' if v[1] is True else 'relative' if v[1] is None else 'relative to {}'.format(v[1]), s=spacing)
            
            if data['ObjectSelection']:
                print '{s}Selected Objects:'.format(s=spacing)
                for i in sorted(data['ObjectSelection']):
                    print '{s}{s}{}'.format(i, s=spacing)
    
    def _relative_frame_change_dropdown(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Dropdown change', indent=_debug)
        if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] is not None:
            
            selected_frame = self._frame_dropdown_format(pm.optionMenu(self.inputs[pm.radioButton]['FrameLocList'], query=True, value=True), undo=True)
            if self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_absolute is not True:
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_absolute = selected_frame
            self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['LocationAbsolute'] = selected_frame
            
            selected_frame = self._frame_dropdown_format(pm.optionMenu(self.inputs[pm.radioButton]['FrameRotList'], query=True, value=True), undo=True)
            if self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_absolute is not True:
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_absolute = selected_frame
            self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['RotationAbsolute'] = selected_frame
                
    
    def _relative_frame_change_radio(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Radio update', indent=_debug)
        
        if self._settings['GroupName'] is not None and self._settings['GroupName'] in self.data and self._settings['CurrentFrame'] is not None:
            
            location_is_absolute = pm.radioButton(self.inputs[pm.radioButton]['FrameLocAbsolute'], query=True, select=True)
            location_is_relative = pm.radioButton(self.inputs[pm.radioButton]['FrameLocRelative'], query=True, select=True)
            
            if location_is_absolute:
                old_location = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_absolute
                if old_location is not True:
                    self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['LocationAbsolute'] = old_location
                
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_absolute = True
                
            else:
                pm.optionMenu(self.inputs[pm.radioButton]['FrameLocList'], edit=True, enable=True)
                
                if 'LocationAbsolute' in self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]:
                    old_location = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['LocationAbsolute']
                else:
                    old_location = None
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_absolute = old_location
            
            rotation_is_absolute = pm.radioButton(self.inputs[pm.radioButton]['FrameRotAbsolute'], query=True, select=True)
            rotation_is_relative = pm.radioButton(self.inputs[pm.radioButton]['FrameRotRelative'], query=True, select=True)
            
            if rotation_is_absolute:
                old_rotation = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_absolute
                if old_rotation is not True:
                    self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['RotationAbsolute'] = old_rotation
                
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_absolute = True
                
            else:
                pm.optionMenu(self.inputs[pm.radioButton]['FrameRotList'], edit=True, enable=True)
                if 'RotationAbsolute' in self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]:
                    old_rotation = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['RotationAbsolute']
                else:
                    old_rotation = None
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_absolute = old_rotation
                
        self._frame_data_disable(_debug=_debug + 1)
        self._relative_frame_redraw(_debug=_debug + 1)
    
    def _relative_frame_redraw(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Dropdown redraw', indent=_debug)
        temp_data = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]
        
        #Get stored values
        if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] in self.data[self._settings['GroupName']]['Frames']:
            
            stored_data = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']]
            loc = stored_data.location_absolute
            rot = stored_data.rotation_absolute
        else:
            loc = None
            rot = None
            
            
        stuff = {'Loc': (loc, 'LocationAbsolute', 'Current Location'),
                 'Rot': (rot, 'RotationAbsolute', 'Current Rotation')}
        
        for i in stuff:
            
            name_start = 'Frame{}'.format(i)
            dropdown_options = pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], query=True, itemListLong=True)
            for j in dropdown_options[1:]:
                pm.deleteUI(j)
                
            if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] is not None:
                for j in sorted(self.data[self._settings['GroupName']]['Frames'].keys()):
                    if j != self._settings['CurrentFrame']:
                        pm.menuItem(label=self._frame_dropdown_format(j), parent=self.inputs[pm.radioButton]['{}List'.format(name_start)])
                        
                if stuff[i][0] is True:
                    #Get temporary value
                    old_value = None
                    if stuff[i][1] in temp_data:
                        old_value = temp_data[stuff[i][1]]
                    if old_value is None:
                        old_value = stuff[i][2]
                    else:
                        old_value = self._frame_dropdown_format(old_value)
                    pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], edit=True, enable=False, value=old_value)
                    
                else:
                    if stuff[i][0] is None:
                        pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], edit=True, value=stuff[i][2])
                    else:
                        pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], edit=True, value=self._frame_dropdown_format(stuff[i][0]))
                
            #Disable frame controls
            else:
                pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], edit=True, enable=False, value=stuff[i][2])
    
    def _frame_dropdown_format(self, i, undo=False, _debug=0):
        """Format the name of the frames."""
        if undo:
            try:
                return float(i.replace('Frame ', ''))
            except ValueError:
                return None
        else:
            if str(i)[-2:] == '.0':
                i = int(i)
            return 'Frame {}'.format(i)
    
    def _frame_data_disable(self, _debug=0):
        """Turn on or off location for each frame."""
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Disable location', indent=_debug)
        
        loc_disable = pm.checkBox(self.inputs[pm.checkBox]['FrameLocDisable'], query=True, value=True)
        rot_disable = pm.checkBox(self.inputs[pm.checkBox]['FrameRotDisable'], query=True, value=True)
        
        disable_items = {'Loc': loc_disable,
                         'Rot': rot_disable}
        
        #Control the visibility
        for i in disable_items:
            
            name_start = 'Frame{}'.format(i)
            
            #Disable if max or min value
            if self._settings['GroupName'] is not None:
                if self.data[self._settings['GroupName']]['Frames'] and max(self.data[self._settings['GroupName']]['Frames'].keys()) == self._settings['CurrentFrame']:
                    disable_items[i] = True
                    pm.checkBox(self.inputs[pm.checkBox]['{}Disable'.format(name_start)], edit=True, enable=False, value=True)
                    pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], edit=True, enable=False)
                
            
            override = pm.checkBox(self.inputs[pm.checkBox]['{}Disable'.format(name_start)], query=True, value=True)
            for j in 'XYZ':
                for k in ('Min', 'Max', 'Join'):
                    name_checkbox = '{}{}{}'.format(name_start, j, k)
                    if k == 'Join':
                        pm.checkBox(self.inputs[pm.checkBox][name_checkbox], edit=True, enable=not disable_items[i])
                    else:
                        pm.textField(self.inputs[pm.textField][name_checkbox], edit=True, enable=not disable_items[i])
        
            if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] is not None:
                pm.radioButton(self.inputs[pm.radioButton]['{}Absolute'.format(name_start)], edit=True, enable=not disable_items[i])
                pm.radioButton(self.inputs[pm.radioButton]['{}Relative'.format(name_start)], edit=True, enable=not disable_items[i])
                pm.optionMenu(self.inputs[pm.radioButton]['{}List'.format(name_start)], edit=True, enable=not disable_items[i] or not override)
                for j in ('Coordinates', 'Min', 'Max', 'Join', 'X', 'Y', 'Z'):
                    pm.text(self.inputs[pm.text]['{}{}'.format(name_start, j)], edit=True, enable=not disable_items[i])
                     
        #Store data 
        if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] is not None:
            
            current_location = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_coordinates
            
            #Send location to temporary storage
            if loc_disable:
                if current_location is not None:
                    self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['Location'] = current_location
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_coordinates = None
            
            #Load location from temporary storage
            elif current_location is None:
                try:
                    location = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']].pop('Location')
                    if location is None:
                        raise KeyError()
                except KeyError:
                    location = (0.0, 0.0, 0.0)
                    
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_coordinates = location
            
            current_rotation = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_coordinates
            
            #Send rotation to temporary storage
            if rot_disable:
                if current_rotation is not None:
                    self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['Rotation'] = current_rotation
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_coordinates = None
            
            #Load rotation from temporary storage
            elif current_rotation is None:
                try:
                    rotation = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']].pop('Rotation')
                    if rotation is None:
                        raise KeyError()
                except KeyError:
                    rotation = (0.0, 0.0, 0.0)
                    
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_coordinates = rotation
                
        self._redraw_groups(_debug=_debug + 1)
        #self._visibility_save(_debug=_debug + 1)
        #self._frame_data_join(_debug=_debug + 1)
    
    def _frame_data_set(self, _debug=0):
        """Store the current values input into the frame location fields."""
        
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Set data', indent=_debug)
        if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] is not None:
            
            
            old_loc = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_coordinates
            old_rot = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_coordinates
            #old_scale = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].scale_coordinates
            #old_vis = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].visibility_coordinates
            
            old_stuff = {}
            if old_loc is not None:
                old_stuff['Loc'] = {'X': old_loc[0],
                                    'Y': old_loc[1],
                                    'Z': old_loc[2]}
            if old_rot is not None:
                old_stuff['Rot'] = {'X': old_rot[0],
                                    'Y': old_rot[1],
                                    'Z': old_rot[2]}
                                 
            results = defaultdict(list)
            for i in old_stuff:
                name_base = 'Frame{}'.format(i)
                for j in ('X', 'Y', 'Z'):
                    
                    #Get the current value
                    name_start = '{}{}'.format(name_base, j)
                    val_join = pm.checkBox(self.inputs[pm.checkBox]['{}Join'.format(name_start)], query=True, value=True)
                    try:
                        val_min = float(pm.textField(self.inputs[pm.textField]['{}Min'.format(name_start)], query=True, text=True))
                        val_max = float(pm.textField(self.inputs[pm.textField]['{}Max'.format(name_start)], query=True, text=True))
                        
                    #Revert to old value if any errors
                    except ValueError:
                        try:
                            val_min, val_max = old_stuff[i][j]
                        except TypeError:
                            val_min = val_max = old_stuff[i][j]
                    
                    #Adjust the max/min values
                    try:
                        val_min_changed = val_min != old_stuff[i][j][0]
                        val_max_changed = val_min != old_stuff[i][j][1] and not val_join
                    except TypeError:
                        val_min_changed = val_min != old_stuff[i][j]
                        val_max_changed = val_min != old_stuff[i][j] and not val_join
                    if val_min_changed and val_min > val_max:
                        val_max = val_min
                    elif val_max_changed and val_max < val_min:
                        val_min = val_max
                    
                    #Set the text fields to the processed values
                    pm.textField(self.inputs[pm.textField]['{}Min'.format(name_start)], edit=True, text=val_min)
                    pm.textField(self.inputs[pm.textField]['{}Max'.format(name_start)], edit=True, text=val_max)
                    
                    #Store the values to save afterwards
                    results[i].append(val_min if val_join else (val_min, val_max))
            
            if old_loc is not None:
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].location_coordinates = tuple(results['Loc'])
            if old_rot is not None:
                self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']].rotation_coordinates = tuple(results['Rot'])
            
            self._frame_select_new(_debug=_debug + 1)
    
    
    def _frame_data_join(self, _debug=0):
        """Run whenever a join checkbox is changed in the frame options.
        Updates the visibility of min and max boxes, and uses 'override' to hide all, since it is run after the location disable.
        """
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Toggle joined options', indent=_debug)
        
        if self._settings['GroupName'] is not None:
            for i in ('Loc', 'Rot'):
                name_base = 'Frame{}'.format(i)
                override = pm.checkBox(self.inputs[pm.checkBox]['{}Disable'.format(name_base)], query=True, value=True)
                for j in ('X', 'Y', 'Z'):
                    name_start = '{}{}'.format(name_base, j)
                    join_values = pm.checkBox(self.inputs[pm.checkBox][name_start + 'Join'], query=True, value=True)
                    min_value = float(pm.textField(self.inputs[pm.textField][name_start + 'Min'], query=True, text=True))
                    if join_values:
                        pm.textField(self.inputs[pm.textField][name_start + 'Max'], edit=True, enable=False, text=min_value)
                    else:
                        pm.textField(self.inputs[pm.textField][name_start + 'Max'], edit=True, enable=True and not override)
    
    def _frame_get_name(self, frame, _debug=0):
        
        frame_name = 'Frame {}'.format(frame)
        if self._settings['CurrentFrame'] == min(self.data[self._settings['GroupName']]['Frames'].keys()):
            frame_name += ' (start)'
        elif self._settings['CurrentFrame'] == max(self.data[self._settings['GroupName']]['Frames'].keys()):
            frame_name += ' (end)'
        return frame_name
    
    def _frame_select(self, refresh=True, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Update settings', indent=_debug)
        if refresh:
            self._group_select_new(_debug=_debug + 1)
            
        frame_name = self._frame_get_name(self._settings['CurrentFrame'])
        pm.textScrollList(self.inputs[pm.textScrollList]['FrameSelection'], edit=True, selectItem=frame_name)
        pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['CurrentFrame'], edit=True, value=self._settings['CurrentFrame'])
        self._redraw_groups(_debug=_debug + 1)
    
    def _frame_change(self, _debug=0):
        """Update settings whenever a keyframe is renamed."""
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Change', indent=_debug)
        
        new_frame = pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['CurrentFrame'], query=True, value=True)
        
        if new_frame != self._settings['CurrentFrame']:
            
            while new_frame in self.data[self._settings['GroupName']]['Frames']:
                new_frame += 1
            
            #Assign stored values a new frame
            if self._settings['GroupName'] and self._settings['CurrentFrame'] is not None:
                self.data[self._settings['GroupName']]['Frames'][new_frame] = self.data[self._settings['GroupName']]['Frames'].pop(self._settings['CurrentFrame'])
                
                if 'Location' in self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]:
                    self._settings['LastFrameData'][self._settings['GroupName']][new_frame]['Location'] = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']].pop('Location')
                if 'LocationAbsolute' in self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]:
                    self._settings['LastFrameData'][self._settings['GroupName']][new_frame]['LocationAbsolute'] = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']].pop('LocationAbsolute')
       
                if 'Rotation' in self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]:
                    self._settings['LastFrameData'][self._settings['GroupName']][new_frame]['Rotation'] = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']].pop('Rotation')
                if 'RotationAbsolute' in self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]:
                    self._settings['LastFrameData'][self._settings['GroupName']][new_frame]['RotationAbsolute'] = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']].pop('RotationAbsolute')
       
            #Update any relative values
            for frame in self.data[self._settings['GroupName']]['Frames']:
                location_absolute = self.data[self._settings['GroupName']]['Frames'][frame].location_absolute
                if location_absolute is not True and location_absolute is not None:
                    if location_absolute == self._settings['CurrentFrame']:
                        self.data[self._settings['GroupName']]['Frames'][frame].location_absolute = new_frame
                        
                rotation_absolute = self.data[self._settings['GroupName']]['Frames'][frame].rotation_absolute
                if rotation_absolute is not True and rotation_absolute is not None:
                    if rotation_absolute == self._settings['CurrentFrame']:
                        self.data[self._settings['GroupName']]['Frames'][frame].rotation_absolute = new_frame
            
            #Update any relative temporary values
            for i in ('Location', 'Rotation'):
                name_absolute = '{}Absolute'.format(i)
                for frame in self._settings['LastFrameData'][self._settings['GroupName']]:
                    if name_absolute in self._settings['LastFrameData'][self._settings['GroupName']][frame]:
                        absolute_value = self._settings['LastFrameData'][self._settings['GroupName']][frame][name_absolute]
                        if absolute_value is not True and absolute_value is not None:
                            if absolute_value == self._settings['CurrentFrame']:
                                self._settings['LastFrameData'][self._settings['GroupName']][frame][name_absolute] = new_frame
       
        self._settings['CurrentFrame'] = new_frame
        self._settings['LastFrameSelection'][self._settings['GroupName']] = new_frame
        self._group_select_new(_debug=_debug + 1)
        self._frame_select(False, _debug=_debug + 1)
                    
    def _frame_select_new(self, reset=True, _debug=0):
        """Update settings when a new frame is selected."""
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Select', indent=_debug)
        
        if reset:
            try:
                current_frame = pm.textScrollList(self.inputs[pm.textScrollList]['FrameSelection'], query=True, selectItem=True)[0]
                
            except IndexError:
                self._settings['CurrentFrame'] = None
            else:
                self._settings['CurrentFrame'] = float(''.join(i for i in current_frame if i in digits or i == '.'))
                
        
        #Load previous selection
        if self._settings['GroupName'] is not None:
            if self._settings['CurrentFrame'] is not None:
                self._settings['LastFrameSelection'][self._settings['GroupName']] = self._settings['CurrentFrame']
            
            elif self._settings['GroupName'] in self._settings['LastFrameSelection']:
                self._settings['CurrentFrame'] = self._settings['LastFrameSelection'][self._settings['GroupName']]
                self._frame_select(False)
        
        #Control what is enabled
        enable = self._settings['CurrentFrame'] is not None
        enable_keyframe = enable and self._settings['CurrentFrame']
        pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['CurrentFrame'], edit=True, enable=enable_keyframe, value=self._settings['CurrentFrame'] or 0.0)
        for i in ('Loc', 'Rot'):
            name_start = 'Frame{}'.format(i)
            pm.checkBox(self.inputs[pm.checkBox]['{}Disable'.format(name_start)], edit=True, enable=enable)
        
        #Read stored values
        if self._settings['GroupName'] is not None and self._settings['CurrentFrame'] is not None:
            frame_data = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']]
            location = frame_data.location_coordinates
            location_absolute = frame_data.location_absolute
            rotation = frame_data.rotation_coordinates
            rotation_absolute = frame_data.rotation_absolute
        else:
            location = None
            location_absolute = None
            rotation = None
            rotation_absolute = None
            
        pm.checkBox(self.inputs[pm.checkBox]['FrameLocDisable'], edit=True, value=location is None)
        pm.checkBox(self.inputs[pm.checkBox]['FrameRotDisable'], edit=True, value=rotation is None)
        
        #Assign stored data if it is disabled
        if location is None:
            try:
                location = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['Location']
                if location is None:
                    raise KeyError()
            except KeyError:
                location = (0.0, 0.0, 0.0)
        if rotation is None:
            try:
                rotation = self._settings['LastFrameData'][self._settings['GroupName']][self._settings['CurrentFrame']]['Rotation']
                if rotation is None:
                    raise KeyError()
            except KeyError:
                rotation = (0.0, 0.0, 0.0)
        
        self._frame_data_disable(_debug=_debug + 1)
        stuff = {'Loc': (location, location_absolute),
                 'Rot': (rotation, rotation_absolute)}
                 
        for i in stuff:
            name_start = 'Frame{}'.format(i)
            for count, j in enumerate(('X', 'Y', 'Z')):
                try:
                    pm.textField(self.inputs[pm.textField]['{}{}Min'.format(name_start, j)], edit=True, text=stuff[i][0][count][0])
                    pm.textField(self.inputs[pm.textField]['{}{}Max'.format(name_start, j)], edit=True, text=stuff[i][0][count][1])
                    pm.checkBox(self.inputs[pm.checkBox]['{}{}Join'.format(name_start, j)], edit=True, value=False)
                except TypeError:
                    pm.textField(self.inputs[pm.textField]['{}{}Min'.format(name_start, j)], edit=True, text=stuff[i][0][count])
                    pm.textField(self.inputs[pm.textField]['{}{}Max'.format(name_start, j)], edit=True, text=stuff[i][0][count])
                    pm.checkBox(self.inputs[pm.checkBox]['{}{}Join'.format(name_start, j)], edit=True, value=True)
            pm.radioButton(self.inputs[pm.radioButton]['{}Absolute'.format(name_start)], edit=True, select=stuff[i][1] is True)
            pm.radioButton(self.inputs[pm.radioButton]['{}Relative'.format(name_start)], edit=True, select=stuff[i][1] is not True)
        
        self._frame_data_join(_debug=_debug + 1)
        self._relative_frame_redraw(_debug=_debug + 1)
    
    def _frame_add(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Add', indent=_debug)
        
        if self._settings['GroupName'] is not None:
            if self._settings['CurrentFrame'] is not None:
                new_frame = self._settings['CurrentFrame'] + 1
            else:
                new_frame = max(self.data[self._settings['GroupName']]['Frames'].keys()) + 1
            while new_frame in self.data[self._settings['GroupName']]['Frames']:
                new_frame += 1
            self.data[self._settings['GroupName']]['Frames'][new_frame]
            self._settings['CurrentFrame'] = new_frame
            self._settings['LastFrameSelection'][self._settings['GroupName']] = new_frame
            self._frame_select(_debug=_debug + 1)
            

    def _frame_remove(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Keyframe: Remove', indent=_debug)
        
        if self._settings['GroupName'] and self._settings['CurrentFrame']:
            all_frames = sorted(self.data[self._settings['GroupName']]['Frames'].keys())
            num_frames = len(all_frames)
            closest_frame = all_frames[all_frames.index(self._settings['CurrentFrame']) - 1]
            if self._settings['CurrentFrame'] and num_frames > 2:
                del self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']]
                self._settings['CurrentFrame'] = closest_frame
                self._settings['LastFrameSelection'][self._settings['GroupName']] = closest_frame
            
            #Validate any relative locations and remove if non existant
            all_frames = set(self.data[self._settings['GroupName']]['Frames'])
            for frame in self.data[self._settings['GroupName']]['Frames']:
                
                location_absolute = self.data[self._settings['GroupName']]['Frames'][frame].location_absolute
                if location_absolute is not True and location_absolute is not None and location_absolute not in all_frames:
                    self.data[self._settings['GroupName']]['Frames'][frame].location_absolute = None
                    
                rotation_absolute = self.data[self._settings['GroupName']]['Frames'][frame].rotation_absolute
                if rotation_absolute is not True and rotation_absolute is not None and rotation_absolute not in all_frames:
                    self.data[self._settings['GroupName']]['Frames'][frame].rotation_absolute = None
                    
                    
            for frame in self._settings['LastFrameData'][self._settings['GroupName']]:
                for i in ('Location', 'Rotation'):
                    name = '{}Absolute'.format(i)
                    if name in self._settings['LastFrameData'][self._settings['GroupName']][frame]:
                        absolute_value = self._settings['LastFrameData'][self._settings['GroupName']][frame][name]
                        if absolute_value is not True and absolute_value is not None and absolute_value not in all_frames:
                            self._settings['LastFrameData'][self._settings['GroupName']][frame][name] = None
                        
            self._frame_select(_debug=_debug + 1)
    
    def _group_settings_save(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Update', indent=_debug)
        
        if self._settings['GroupName'] is not None:
            self.data[self._settings['GroupName']]['FrameOffset'] = pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['FrameOffset'], query=True, value=True)
            self.data[self._settings['GroupName']]['RandomOffset'] = pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['RandomOffset'], query=True, value=True)
            self.data[self._settings['GroupName']]['BounceDistance'] = pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['BounceDistance'], query=True, value=True)
            self.data[self._settings['GroupName']]['FrameDistance'] = pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['DistanceUnits'], query=True, value=True)
            
            try:
                origin_x = float(pm.textField(self.inputs[pm.textField]['OriginX'], query=True, text=True))
            except ValueError:
                origin_x = self.data[self._settings['GroupName']]['ObjectOrigin'][0]
            try:
                origin_y = float(pm.textField(self.inputs[pm.textField]['OriginY'], query=True, text=True))
            except ValueError:
                origin_y = self.data[self._settings['GroupName']]['ObjectOrigin'][1]
            try:
                origin_z = float(pm.textField(self.inputs[pm.textField]['OriginZ'], query=True, text=True))
            except ValueError:
                origin_z = self.data[self._settings['GroupName']]['ObjectOrigin'][2]
            self.data[self._settings['GroupName']]['ObjectOrigin'] = (origin_x, origin_y, origin_z)
            pm.textField(self.inputs[pm.textField]['OriginX'], edit=True, text=origin_x)
            pm.textField(self.inputs[pm.textField]['OriginY'], edit=True, text=origin_y)
            pm.textField(self.inputs[pm.textField]['OriginZ'], edit=True, text=origin_z)
            
            
            self.data[self._settings['GroupName']]['Axis'] = (pm.checkBox(self.inputs[pm.checkBox]['OriginX'], query=True, value=True),
                                                              pm.checkBox(self.inputs[pm.checkBox]['OriginY'], query=True, value=True),
                                                              pm.checkBox(self.inputs[pm.checkBox]['OriginZ'], query=True, value=True))
            

            self._redraw_groups(_debug=_debug + 1)
    
    def _group_name_save(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Set name', indent=_debug)
        
        if self._settings['GroupName'] is not None:
            new_name = str(pm.textField(self.inputs[pm.textField]['GroupName'], query=True, text=True))
            new_name = ''.join(i for i in new_name if i in ascii_letters + digits + '.-_ "~')
            
            old_data = self.data[self._settings['GroupName']]
            
            #Delete old keys
            try:
                del self.data[self._settings['GroupName']]
            except KeyError:
                pass
            try:
                del self._original_data[self._settings['GroupName']]
            except KeyError:
                pass
                
            #Force unique name
            if new_name in self.data:
                count = 1
                while '{}.{}'.format(new_name, count) in self.data:
                    count += 1
                new_name = '{}.{}'.format(new_name, count)
        
            if self._settings['GroupName'] in self._settings['LastFrameSelection']:
                self._settings['LastFrameSelection'][new_name] = self._settings['LastFrameSelection'].pop(self._settings['GroupName'])
        
            self.data[new_name] = old_data
            self._settings['GroupName'] = new_name
            self._redraw_groups(_debug=_debug + 1)
        
    
    def _group_select_new(self, _debug=0):
        try:
            self._settings['GroupName'] = pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], query=True, selectItem=True)[0].split(' (')[0].replace('*', '')
            if self._settings['GroupName'] not in self.data:
                self._settings['GroupName'] = None
                raise IndexError()
            
        except IndexError:
            self._settings['GroupName'] = None
            pm.textField(self.inputs[pm.textField]['GroupName'], edit=True, text='no selection', enable=False)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['DistanceUnits'], edit=True, value=0, enable=False)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['FrameOffset'], edit=True, value=0, enable=False)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['RandomOffset'], edit=True, value=0, enable=False)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['BounceDistance'], edit=True, value=0, enable=False)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['DistanceUnits'], edit=True, value=0, enable=False)
            pm.button(self.inputs[pm.button]['OriginApply'], edit=True, label='Use Current Selection', enable=False)
            pm.textField(self.inputs[pm.textField]['OriginX'], edit=True, text='no selection', enable=False)
            pm.textField(self.inputs[pm.textField]['OriginY'], edit=True, text='no selection', enable=False)
            pm.textField(self.inputs[pm.textField]['OriginZ'], edit=True, text='no selection', enable=False)
            pm.checkBox(self.inputs[pm.checkBox]['OriginX'], edit=True, value=False, enable=False)
            pm.checkBox(self.inputs[pm.checkBox]['OriginY'], edit=True, value=False, enable=False)
            pm.checkBox(self.inputs[pm.checkBox]['OriginZ'], edit=True, value=False, enable=False)
            pm.textScrollList(self.inputs[pm.textScrollList]['FrameSelection'], edit=True, enable=False, removeAll=True)
            pm.button(self.inputs[pm.button]['FrameAdd'], edit=True, enable=False)
            
            for i in ('Loc', 'Rot'):
                name_start = 'Frame{}'.format(i)
                for j in ('Coordinates', 'Min', 'Max', 'Join', 'X', 'Y', 'Z'):
                    pm.text(self.inputs[pm.text]['{}{}'.format(name_start, j)], edit=True, enable=False)
                pm.radioButton(self.inputs[pm.radioButton]['{}Absolute'.format(name_start)], edit=True, select=False, enable=False)
                pm.radioButton(self.inputs[pm.radioButton]['{}Relative'.format(name_start)], edit=True, select=True, enable=False)
                

        else:            
            pm.textField(self.inputs[pm.textField]['GroupName'], edit=True, text=self._settings['GroupName'], enable=True)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['DistanceUnits'], edit=True, value=self.data[self._settings['GroupName']]['FrameDistance'], enable=True)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['FrameOffset'], edit=True, value=self.data[self._settings['GroupName']]['FrameOffset'], enable=True)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['RandomOffset'], edit=True, value=self.data[self._settings['GroupName']]['RandomOffset'], enable=True)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['BounceDistance'], edit=True, value=self.data[self._settings['GroupName']]['BounceDistance'], enable=True)
            pm.floatSliderGrp(self.inputs[pm.floatSliderGrp]['DistanceUnits'], edit=True, value=self.data[self._settings['GroupName']]['FrameDistance'], enable=True)
            pm.button(self.inputs[pm.button]['OriginApply'], edit=True, label='Use Current Selection', enable=True)
            origin = self.data[self._settings['GroupName']]['ObjectOrigin']
            pm.textField(self.inputs[pm.textField]['OriginX'], edit=True, text=origin[0], enable=True)
            pm.textField(self.inputs[pm.textField]['OriginY'], edit=True, text=origin[1], enable=True)
            pm.textField(self.inputs[pm.textField]['OriginZ'], edit=True, text=origin[2], enable=True)
            pm.checkBox(self.inputs[pm.checkBox]['OriginX'], edit=True, value=self.data[self._settings['GroupName']]['Axis'][0], enable=True)
            pm.checkBox(self.inputs[pm.checkBox]['OriginY'], edit=True, value=self.data[self._settings['GroupName']]['Axis'][1], enable=True)
            pm.checkBox(self.inputs[pm.checkBox]['OriginZ'], edit=True, value=self.data[self._settings['GroupName']]['Axis'][2], enable=True)
            
            if self._settings['CurrentFrame'] is not None:
                stored_data = self.data[self._settings['GroupName']]['Frames'][self._settings['CurrentFrame']]
                stuff = {'Loc': stored_data.location_absolute,
                         'Rot': stored_data.rotation_absolute}
                for i in stuff:
                    name_start = 'Frame{}'.format(i)
                    try:
                        pm.radioButton(self.inputs[pm.radioButton]['{}Absolute'.format(name_start)], edit=True, select=stuff[i] is True, enable=True)
                        pm.radioButton(self.inputs[pm.radioButton]['{}Relative'.format(name_start)], edit=True, select=stuff[i] is not True, enable=True)
                    except NameError:
                        pm.radioButton(self.inputs[pm.radioButton]['{}Absolute'.format(name_start)], edit=True, select=False, enable=False)
                        pm.radioButton(self.inputs[pm.radioButton]['{}Relative'.format(name_start)], edit=True, select=True, enable=False)
                
            
            frames = ['Frame {}'.format(i) for i in sorted(self.data[self._settings['GroupName']]['Frames'].keys())]
            frames[0] += ' (start)'
            frames[-1] += ' (end)'
            pm.textScrollList(self.inputs[pm.textScrollList]['FrameSelection'], edit=True, enable=True, removeAll=True, append=frames)
            pm.button(self.inputs[pm.button]['FrameAdd'], edit=True, enable=True)
            self._settings['CurrentFrame'] = None
        
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Changed to {}'.format(self._settings['GroupName']), indent=_debug)
        
        self._redraw_selection(_debug=_debug + 1)
        self._frame_select_new(False, _debug=_debug + 1)
        self._objects_select(_redraw=False, _debug=_debug + 1)
    
    def _set_origin_location(self, _debug=0):
        '''Set location of origin to the current selection, and average multiple objects if needed.'''
        self._debug_print(sys._getframe().f_code.co_name, 'Origin: Set location', indent=_debug)
        
        selected_objects = pm.ls(selection=True)
        if selected_objects:
            try:
                object_locations = [i.getTranslation() for i in selected_objects]
                average_x = sum(x for x, y, z in object_locations) / len(selected_objects)
                average_y = sum(y for x, y, z in object_locations) / len(selected_objects)
                average_z = sum(z for x, y, z in object_locations) / len(selected_objects)
                pm.textField(self.inputs[pm.textField]['OriginX'], edit=True, text=average_x)
                pm.textField(self.inputs[pm.textField]['OriginY'], edit=True, text=average_y)
                pm.textField(self.inputs[pm.textField]['OriginZ'], edit=True, text=average_z)
                pm.button(self.inputs[pm.button]['OriginApply'], edit=True, label='Use Current Selection')
                self._group_settings_save(_debug=_debug + 1)
            except AttributeError:
                pm.button(self.inputs[pm.button]['OriginApply'], edit=True, label='Use Current Selection (error with selection)')
        else:
            pm.button(self.inputs[pm.button]['OriginApply'], edit=True, label='Use Current Selection (nothing selected)')
    
    def _refresh_ui(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Reload settings', indent=_debug)
        
        self._reset_settings(_debug=_debug + 1)
        self.reload(_debug=_debug + 1)
        for k in self._group_unsaved:
            del self._original_data[k]
            del self.data[k]
        self._group_unsaved = []
        self.save(original=True)
        self._group_select_new(_debug=_debug + 1)
        self._redraw_groups(_debug=_debug + 1)
        self._redraw_selection(_debug=_debug + 1)
        
    def _group_clean(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Clean', indent=_debug)
        
        try:
            current_index = self.data[self._settings['GroupName']]['ListOrder']
        except KeyError:
            current_index = len(self.data) - 1
        original_group = self._settings['GroupName']
            
        #Delete any group that is empty
        new_keys = set(self.data.keys()) - set(self._original_data.keys())
        for k, v in sorted(self._original_data.iteritems(), key=lambda (x, y): y['ListOrder']):
            if not len(v['ObjectSelection']):
                self._settings['GroupName'] = k
                self._group_delete(_debug=_debug + 1)
                #print k, self.data.keys()
        for k in new_keys:
            if not len(v['ObjectSelection']):
                self._settings['GroupName'] = k
                self._group_delete(_debug=_debug + 1)
        
        #Reselect a group
        if original_group in self.data:
            self._settings['GroupName'] = original_group
        else:
            try:
                self._settings['GroupName'] = [k for k, v in self.data.iteritems() if v['ListOrder'] == min(len(self.data) - 1, max(0, current_index))][0]
            except IndexError:
                self._settings['GroupName'] = None
        self._redraw_selection(_debug=_debug + 1)
        self._redraw_groups(_debug=_debug + 1)
        self._group_select_new(_debug=_debug + 1)
    
    def _group_add(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Add', indent=_debug)
        
        current_index = len(self.data) - 1
        if self._settings['GroupName'] is not None:
            current_index = self.data[self._settings['GroupName']]['ListOrder']
        for k, v in self.data.iteritems():
            if v['ListOrder'] > current_index:
                self.data[k]['ListOrder'] += 1
        
        self._settings['GroupName'] = 'group {}'.format(self._group_new_count)
        self._group_new_count += 1
        g = SetGroup(self._settings['GroupName'], list_order=current_index + 1)
        g.save()
        self.data[self._settings['GroupName']] = load_data()[self._settings['GroupName']]
        
        self._group_unsaved.append(self._settings['GroupName'])
        self._redraw_selection(_debug=_debug + 1)
        self._redraw_groups(_debug=_debug + 1)
        self._group_select_new(_debug=_debug + 1)
    
    def _group_delete(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Delete', indent=_debug)
        
        if self._settings['GroupName'] not in self.data:
            self._settings['GroupName'] = None
        
        else:
            current_index = self.data[self._settings['GroupName']]['ListOrder']
            for k, v in self.data.iteritems():
                if v['ListOrder'] > current_index:
                    self.data[k]['ListOrder'] -= 1
            del self.data[self._settings['GroupName']]
            try:
                self._settings['GroupName'] = [k for k, v in self.data.iteritems() if v['ListOrder'] == max(0, current_index - 1)][0]
            except IndexError:
                self._settings['GroupName'] = None
                
        self._frame_select_new(_debug=_debug + 1)
        if self._settings['GroupName'] is not None:
            self._redraw_selection(_debug=_debug + 1)
            self._redraw_groups(_debug=_debug + 1)
            self._group_select_new(_debug=_debug + 1)
        
        
    def _group_up(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Move up', indent=_debug)
        if self._settings['GroupName'] is not None:
            list_order = self.data[self._settings['GroupName']]['ListOrder']
            closest_lower = [None, -float('inf')]
            for k, v in self.data.iteritems():
                if closest_lower[1] < v['ListOrder'] < list_order:
                    closest_lower = [k, v['ListOrder']]
            if closest_lower[0] is not None:
                self.data[self._settings['GroupName']]['ListOrder'], self.data[closest_lower[0]]['ListOrder'] = self.data[closest_lower[0]]['ListOrder'], self.data[self._settings['GroupName']]['ListOrder']
            self._redraw_groups(_debug=_debug + 1)
        
    def _group_down(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Group: Move down', indent=_debug)
        if self._settings['GroupName'] is not None:
            list_order = self.data[self._settings['GroupName']]['ListOrder']
            closest_higher = [None, float('inf')]
            for k, v in self.data.iteritems():
                if list_order < v['ListOrder'] < closest_higher[1]:
                    closest_higher = [k, v['ListOrder']]
            if closest_higher[0] is not None:
                self.data[self._settings['GroupName']]['ListOrder'], self.data[closest_higher[0]]['ListOrder'] = self.data[closest_higher[0]]['ListOrder'], self.data[self._settings['GroupName']]['ListOrder']
            self._redraw_groups(_debug=_debug + 1)
    
    def _objects_select(self, _redraw=True, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Objects: New selection, update visibility', indent=_debug)
        
        #If nothing is selected disable controls
        if self._settings['GroupName'] is None or self._settings['GroupName'] not in self.data:
            pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, enable=False)
            pm.button(self.inputs[pm.button]['ObjectSave'], edit=True, enable=False)
            
        #Set button visibility if things have changed
        else:
            pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, enable=True)
            self._settings['GroupObjects'] = set(map(str, pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], query=True, selectItem=True)))
            self.data[self._settings['GroupName']]['ObjectSelection'] = self._settings['GroupObjects']
        
        self._visibility_save(_debug=_debug + 1)
        if _redraw:
            self._redraw_groups(_debug=_debug + 1)
    
    def _visibility_save(self, _debug=0):
        
        changed = False
        
        #Check for new selection
        try:
            changed = self.data[self._settings['GroupName']] != self._original_data[self._settings['GroupName']]
        except KeyError:
            changed = False
        
        if not changed:
            changed = sorted(self.data.iteritems(), key=lambda (x, y): y['ListOrder']) != sorted(self._original_data.iteritems(), key=lambda (x, y): y['ListOrder'])
        
        #Check for if empty groups were removed
        if not changed:
            changed = sorted(self.data.keys()) != sorted(self._original_data.keys())
            
        self._debug_print(sys._getframe().f_code.co_name, 'Save: Toggle button visibility ({})'.format(changed), indent=_debug)

        pm.button(self.inputs[pm.button]['ObjectSave'], edit=True, enable=changed)
    
    def _objects_refresh(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Objects: Redraw', indent=_debug)
        #self.reload()
        self.reload_objects(_debug=_debug + 1)
        self._redraw_selection(_debug=_debug + 1)
        
    def _save_all(self, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, 'Save: Store all', indent=_debug)
        #self.data[self._settings['GroupName']]['ObjectSelection'] = set(self._settings['GroupObjects'])
        self.save(_debug=_debug + 1)
        self._redraw_selection(_debug=_debug + 1)
        self._redraw_groups(_debug=_debug + 1)
    
    def _objects_hide(self, _debug=0):
        """Toggle if already selected objects should be hidden."""
        
        self._settings['HideSelected'] = pm.checkBox(self.inputs[pm.checkBox]['ObjectHide'], query=True, value=True)
        self._debug_print(sys._getframe().f_code.co_name, 'Selection: Hide ({})'.format(self._settings['HideSelected']), indent=_debug)
        
        self._redraw_selection(_debug=_debug + 1)
        
    def _redraw_selection(self, _debug=0):
        """Redraw the list of objects."""
        self._debug_print(sys._getframe().f_code.co_name, 'Selection: Redraw', indent=_debug)
        
        pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, removeAll=True)
        object_list = set(self.scene_objects)
        try:
            selected_objects = [i for i in self.data[self._settings['GroupName']]['ObjectSelection'] if i in self.scene_objects]
        except KeyError:
            selected_objects = []
        else:
            self._selection_clean(self._settings['GroupName'])
            if self._settings['HideSelected']:
                for k, v in self.data.iteritems():
                    if k != self._settings['GroupName']:
                        object_list.difference_update(v['ObjectSelection'])
            object_list.update(selected_objects)
        object_list = sorted(object_list)
        pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, append=object_list, selectItem=selected_objects)
    
        #Register callbacks to redraw the selection if an object gets deleted
        for i in self.scene_objects:
            try:
                pm.getAttr('{}.aem'.format(i))
            except pm.MayaAttributeError:
                pm.addAttr(i, shortName='aem', longName='AssembleVisibilityMarker')
            pm.scriptJob(attributeDeleted=('{}.aem'.format(i), self._objects_refresh), parent=self.win, runOnce=True)
            
    
    def _redraw_groups(self, _debug=0):
        """Redraw list of groups."""
        self._debug_print(sys._getframe().f_code.co_name, 'Groups: Redraw', indent=_debug)
        
        pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], edit=True, removeAll=True)
        group_names = []
        
        #Get value higher than all other orders currently
        try:
            order_count = max(v['ListOrder'] for v in self.data.values() if v['ListOrder'] is not None) + 1
        except ValueError:
            order_count = 0
            
        order_used = set(v['ListOrder'] for v in self.data.values() if v['ListOrder'] is not None)
        for k, v in sorted(self.data.iteritems(), key=lambda (x, y): y['ListOrder']):
            if v['ListOrder'] is None:
                while order_count in order_used:
                    order_count += 1
                self.data[k]['ListOrder'] = order_count
                self._original_data[k]['ListOrder'] = order_count
                order_count += 1
            
            self._selection_clean(k, _debug=_debug + 1)
            group_names.append(self._group_name_format(k, _debug=_debug + 1))
        
        pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], edit=True, append=group_names)
        if self._settings['GroupName'] is not None:
            pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], edit=True, selectItem=self._group_name_format(self._settings['GroupName'], _debug=_debug + 1))
        self._objects_select(_redraw=False, _debug=_debug + 1)
        self._frame_data_join(_debug=_debug + 1)
    
    def _group_name_format(self, k, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, "Group: Format name '{}'".format(k), indent=_debug)
        """Format the name of the group using the information inside it."""
        try:
            num_items = len(self._original_data[k]['ObjectSelection'])
        except KeyError:
            num_items = 0
            difference = False
        try:
            difference = sorted(self._original_data[k]['ObjectSelection']) != sorted(self.data[k]['ObjectSelection'])
            if not difference:
                difference = self._original_data[k] != self.data[k]
            if not difference:
                difference = self._original_data[k]['Frames'] != self.data[k]['Frames']
                
        except KeyError:
            difference = True
        all_frames = self.data[k]['Frames'].keys()
        num_frames = max(all_frames) - min(all_frames)
        return '{a}{k} ({n}, {f} keyframe{s1}, {l} frame{s2})'.format(k=k, 
                                                                      n='{} object{}'.format(num_items, '' if num_items == 1 else 's') if num_items else 'empty', 
                                                                      a='*' if difference else '', 
                                                                      l=num_frames, 
                                                                      f=len(all_frames), 
                                                                      s1='' if len(all_frames) == 1 else 's',
                                                                      s2='' if num_frames == 1 else 's')
    
    def _selection_clean(self, group, _debug=0):
        self._debug_print(sys._getframe().f_code.co_name, "Selection: Clean group '{}'".format(group), indent=_debug)
        
        """Remove any items from the selection that are not in the scene."""
        original_group = set(self.data[group]['ObjectSelection'])
        self.data[group]['ObjectSelection'] = set(i for i in self.data[group]['ObjectSelection'] if i in self.scene_objects)
        return len(self.data[group]['ObjectSelection']) == len(original_group)
    
    def _debug_print(self, func_name, description, indent=0):
        now = datetime.datetime.now()
        print '[{h}:{m}:{s}]{i} {d} ({c}.{f})'.format(i='  ' * indent, h=now.hour, m=now.minute, s=now.second, d=description, c='self', c2=self.__class__.__name__, f=func_name)
    
    def test(self):
        print 'callback test', self._settings['CurrentFrame']
'''
SelectionChanged - update last frame coordinates
NameChanged - update any selections
DagObjectCreated
'''
pm.fileInfo['AssemblyScript'] = StoreData().save({})
a = SetGroup('test')
a.selection=['pCube1', 'pCone1']
a.save()
for i in range(2):
    a = SetGroup('test'+str(i))
    a.save()
UserInterface().display()
