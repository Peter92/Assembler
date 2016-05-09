'''
start frame
random frame offset
how far to bounce

how many units per frame
point of origin
use selected object
which axis
'''
from __future__ import division
import math
import base64
from collections import MutableMapping, defaultdict

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
    TYPES = [bool, int, str, dict, list, tuple, float, unicode, tuple, complex, type(None), set]
    _TYPES = {long: int} #Treat the key type as the value type
    TYPE_LEN = int(math.ceil(math.log(len(TYPES), 2)))
    LOC = 'C:/Users/Peter/AppData/Roaming/IndexDataTest'
    
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
        
        try:
            type_id = self.TYPES.index(item_type)
        except ValueError:
            raise ValueError("{} is not supported".format(item_type))
        encoded_string = int_to_bin(type_id, self.TYPE_LEN)
        
        #Get the length of the input
        if item_type == bool:
            item_bin = str(int(bool(x)))
            return encoded_string + '1' + item_bin
        
        elif item_type == type(None):
            return encoded_string + '10'

        if item_type in (int, str, unicode):
            if item_type == int:
                item_bin = int_to_bin(x).replace('-', '')
                
            elif item_type in (str, unicode):
                item_bin = ''.join(int_to_bin(ord(i), 8) for i in x)
                
            item_len = len(item_bin)
            num_bytes_int = (item_len - 1) // 8 + 1
            
        elif item_type in (float, complex):
            num_bytes_int = 2
        
        elif item_type in (list, tuple, dict, set):
            num_bytes_int = len(x)
            
        #Convert input length into number of bytes
        num_bytes_bin = int_to_bin(num_bytes_int)
        num_bytes_len = len(num_bytes_bin)
        if num_bytes_len % 8:
            num_bytes_bin = '0' * (8 - num_bytes_len % 8) + num_bytes_bin
        
        num_bytes_len = (len(num_bytes_bin) - 1) // 8 + 1
        
        encoded_string += '0' * (num_bytes_len - 1) + '1'
        encoded_string += num_bytes_bin
        
        #Convert input to bytes
        if item_type in (int, str):
            
            if item_type == int:
                encoded_string += '0' if x > 0 else '1'
            
            remaining_bits = item_len % 8
            if remaining_bits:
                item_bin = '0' * (8 - item_len % 8) + item_bin
            
            encoded_string += item_bin
            
        elif item_type == float:
            x_split = str(x).split('.')
            encoded_string += '0' if x > 0 else '1'
            encoded_string += self._encode_value(int(x_split[0]))
            encoded_string += self._encode_value(x_split[1])
        
        elif item_type == complex:
            encoded_string += self._encode_value(x.real)
            encoded_string += self._encode_value(x.imag)
        
        elif item_type in (list, tuple, set):
            for i in x:
                encoded_string += self._encode_value(i)
                
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
        if item_type in (int, str, unicode):
            start_offset = end_offset
            
            if item_type == int:
                is_negative = int(x[start_offset])
                start_offset += 1
            
            end_offset = start_offset + num_bytes * 8
            data = x[start_offset:end_offset]
        
            if item_type == int:
                data = int(data, 2) * (-1 if is_negative else 1)
                
            elif item_type in (str, unicode):
                data = ''.join(chr(int(data[i:i + 8], 2)) for i in range(0, len(data), 8))
        
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
            #print x[start_offset:]
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
    def __init__(self, location=None, rotation=None, scale=None, visibility=None):
        self.location = location
        self.rotation = rotation
        self.scale = scale
        self.visibility = visibility
    
    def __repr__(self):
        return '{x.__class__.__name__}(location={x.location}, rotation={x.rotation}, scale={x.scale}, visibility={x.visibility}'.format(x=self)


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
    
    def __init__(self, name=None, start=None, distance=None, random=None, selection=None, origin=None, bounce=0, list_order=None):
        
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
        
        self.start = start
        self.distance = distance
        self.random = random
        
        self.frame = defaultdict(_MovementInfo)
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
                                'FrameStart': self.start,
                                'FrameDistance': self.distance,
                                'FrameRandom': self.random,
                                'ListOrder': self.list_order} #need to fix float('inf')
        pm.fileInfo['AssemblyScript'] = StoreData().save(self.data)

    def load(self):
        self.data = load_data()
    

class UserInterface(object):
    name = 'Assembler'
    
    def __init__(self):
        self._settings = {'GroupObjects': set(),
                          'GroupName': None,
                          'HideSelected': True
                          }
        self.inputs = defaultdict(dict)
        self.reload()
        self._group_new_count = 0
        self._group_unsaved = []
    
    def reload(self):
        self.data = load_data()
        self._original_data = load_data()
        self.reload_objects()
    
    def reload_objects(self):
        """Refresh the list of objects."""
        
        #Get a list of all scene objects (without cameras)
        scene_objects = pm.ls(dag=True, exactType=pm.nodetypes.Transform)
        for cam_name in (i.replace('Shape', '') for i in pm.ls(exactType=pm.nodetypes.Camera)):
            try: 
                del scene_objects[scene_objects.index(pm.nodetypes.Transform(cam_name))]
            except (pm.MayaNodeError, ValueError):
                pass
        self.scene_objects = set(map(str, scene_objects))
        
    def display(self):
        
        self.reload()
        
        if pm.window(self.name, exists=True):
            pm.deleteUI(self.name, window=True)

        win = pm.window(self.name, title=self.name, sizeable=True, resizeToFitChildren=True)

        with pm.rowColumnLayout(numberOfColumns=3):
            with pm.rowColumnLayout(numberOfColumns=1):
                self.inputs[pm.textScrollList]['Groups'] = pm.textScrollList(allowMultiSelection=False, append=['error'], height=100, selectCommand=pm.Callback(self._group_select_new))
                with pm.rowColumnLayout(numberOfColumns=11):
                    self.inputs[pm.button]['GroupRefresh'] = pm.button(label='Reload', command=pm.Callback(self._group_refresh))
                    pm.text(label='')
                    self.inputs[pm.button]['GroupAdd'] = pm.button(label='+', command=pm.Callback(self._group_add))
                    pm.text(label='')
                    self.inputs[pm.button]['GroupRemove'] = pm.button(label='-', command=pm.Callback(self._group_remove))
                    pm.text(label='')
                    self.inputs[pm.button]['GroupMoveUp'] = pm.button(label='^', command=pm.Callback(self._group_up))
                    pm.text(label='')
                    self.inputs[pm.button]['GroupMoveDown'] = pm.button(label='v', command=pm.Callback(self._group_down))
                    pm.text(label='')
                    self.inputs[pm.button]['GroupClean'] = pm.button(label='Remove empty groups', command=pm.Callback(self._group_clean))
                                    
                self.inputs[pm.textScrollList]['AllObjects'] = pm.textScrollList(allowMultiSelection=True, append=['error'], height=200, selectCommand=pm.Callback(self._objects_select))
                with pm.rowColumnLayout(numberOfColumns=5):
                    self.inputs[pm.button]['ObjectRefresh'] = pm.button(label='Refresh', command=pm.Callback(self._objects_refresh))
                    pm.text(label='')
                    self.inputs[pm.button]['ObjectSave'] = pm.button(label='Save All', command=pm.Callback(self._save_all))
                    pm.text(label='')
                    self.inputs[pm.checkBox]['ObjectHide'] = pm.checkBox(label='Hide selected objects', value=self._settings['HideSelected'], changeCommand=pm.Callback(self._objects_hide))
        
            with pm.rowColumnLayout(numberOfColumns=1):
                pm.text(label='')
                
            with pm.rowColumnLayout(numberOfColumns=1):
                with pm.rowColumnLayout(numberOfColumns=3):
                    pm.text(label='Group Name', align='right')
                    pm.text(label='')
                    self.inputs[pm.textField]['GroupName'] = pm.textField(text='error', changeCommand=pm.Callback(self._group_name_save))
                with pm.rowColumnLayout(numberOfColumns=1):
                    self.inputs[pm.button]['GroupUpdate'] = pm.button(label='Update', command=pm.Callback(self._group_save))

                
        print 'finish ui'
        self._objects_select()
        self._redraw_groups()
        self._group_select_new()
        self.save()
        pm.showWindow()
        
    def save(self, original=False):
        if original:
            pm.fileInfo['AssemblyScript'] = StoreData().save(self._original_data)
        else:
            for k, v in self.data.iteritems():
                print k, v
            pm.fileInfo['AssemblyScript'] = StoreData().save(self.data)
            self._group_unsaved = []
            self._visibility_save()
            self.reload()
    
    def _group_name_save(self):
        if self._settings['GroupName']:
            new_name = str(pm.textField(self.inputs[pm.textField]['GroupName'], query=True, text=True))
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
        
            self.data[new_name] = old_data
            self._settings['GroupName'] = new_name
            self._redraw_groups()
        
    def _group_save(self):
        print 'save group info'
        self._group_name_save()
    
    def _group_select_new(self):
        try:
            self._settings['GroupName'] = pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], query=True, selectItem=True)[0].split(' (')[0].replace('*', '')
        except IndexError:
            self._settings['GroupName'] = None
            pm.textField(self.inputs[pm.textField]['GroupName'], edit=True, text='no selection', enable=False)
        else:
            print 'changed group to', self._settings['GroupName']
            
            pm.textField(self.inputs[pm.textField]['GroupName'], edit=True, text=self._settings['GroupName'], enable=True)
            
        self._redraw_selection()
        self._objects_select(_redraw=False)
    
    def _group_refresh(self):
        print 'refresh groups'
        self.reload()
        for k in self._group_unsaved:
            del self._original_data[k]
            del self.data[k]
        self._group_unsaved = []
        self.save(original=True)
        self._redraw_groups()
        self._redraw_selection()
        
    def _group_clean(self):
        print 'remove empty'
        '''
        need to reduce keys as well or errors will happen
        '''
        
        '''
        #if self._settings['GroupName'] and not self.data[self._settings['GroupName']]['ObjectSelection']:
        try:
            current_index = self.data[self._settings['GroupName']]['ListOrder']
        except KeyError:
            current_index = len(self.data) - 1
            
        #Search through original data for the saved selection and not the current one
        invalid_groups = []
        new_keys = set(self.data.keys()) - set(self._original_data.keys())
        for k, v in sorted(self._original_data.iteritems(), key=lambda (x, y): y['ListOrder']):
            if not len(v['ObjectSelection']):
                invalid_groups.append(k)
            else:
                self.data[k]['ListOrder'] -= len(invalid_groups)
        for k in invalid_groups + list(new_keys):
            #del self._original_data[k]
            try:
                del self.data[k]
            except KeyError:
                pass
        print min(len(self.data) - 1, max(0, current_index - 1))
        #self._settings['GroupName'] = [k for k, v in self.data.iteritems() if v['ListOrder'] == min(len(self.data) - 1, max(0, current_index - 1))][0]
            
        self._redraw_selection()
        self._redraw_groups()
        '''
    
    def _group_add(self):
        print 'add group'
        current_index = len(self.data) - 1
        if self._settings['GroupName']:
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
        self._redraw_selection()
        self._redraw_groups()
        self._group_select_new()
            
    def _group_remove(self):
        if self._settings['GroupName']:
            current_index = self.data[self._settings['GroupName']]['ListOrder']
            for k, v in self.data.iteritems():
                if v['ListOrder'] > current_index:
                    self.data[k]['ListOrder'] -= 1
            del self.data[self._settings['GroupName']]
            try:
                del self._original_data[self._settings['GroupName']]
            except KeyError:
                pass
            try:
                self._settings['GroupName'] = [k for k, v in self.data.iteritems() if v['ListOrder'] == max(0, current_index - 1)][0]
            except IndexError:
                self._settings['GroupName'] = None
            self._redraw_selection()
            self._redraw_groups()
            self._group_select_new()
        
        
    def _group_up(self):
        print 'move group up'
        list_order = self.data[self._settings['GroupName']]['ListOrder']
        closest_lower = [None, -float('inf')]
        for k, v in self.data.iteritems():
            if closest_lower[1] < v['ListOrder'] < list_order:
                closest_lower = [k, v['ListOrder']]
        if closest_lower[0] is not None:
            self.data[self._settings['GroupName']]['ListOrder'], self.data[closest_lower[0]]['ListOrder'] = self.data[closest_lower[0]]['ListOrder'], self.data[self._settings['GroupName']]['ListOrder']
        self._redraw_groups()
        
    def _group_down(self):
        print 'move group down'
        list_order = self.data[self._settings['GroupName']]['ListOrder']
        closest_higher = [None, float('inf')]
        for k, v in self.data.iteritems():
            if list_order < v['ListOrder'] < closest_higher[1]:
                closest_higher = [k, v['ListOrder']]
        if closest_higher[0] is not None:
            self.data[self._settings['GroupName']]['ListOrder'], self.data[closest_higher[0]]['ListOrder'] = self.data[closest_higher[0]]['ListOrder'], self.data[self._settings['GroupName']]['ListOrder']
        self._redraw_groups()
    
    def _objects_select(self, _redraw=True):
        print 'select objects, update visibility'
        
        #If nothing is selected disable controls
        if not self._settings['GroupName'] or self._settings['GroupName'] not in self.data:
            pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, enable=False)
            pm.button(self.inputs[pm.button]['ObjectSave'], edit=True, enable=False)
        #Set button visibility if things have changed
        else:
            pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, enable=True)
            self._settings['GroupObjects'] = set(map(str, pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], query=True, selectItem=True)))
            self.data[self._settings['GroupName']]['ObjectSelection'] = self._settings['GroupObjects']
        self._visibility_save()
        if _redraw:
            self._redraw_groups()
    
    def _visibility_save(self):
        print 'update save visibility'
        changed = False
        
        '''
        #Check for new selection
        if self._settings['GroupName'] and self._settings['GroupName'] in self.data:
            changed = self._settings['GroupObjects'] != self.data[self._settings['GroupName']]['ObjectSelection']
        '''
        
        #Check for if empty objects have been removed
        if not changed:
            changed = sorted(self.data.iteritems(), key=lambda (x, y): y['ListOrder']) != sorted(self._original_data.iteritems(), key=lambda (x, y): y['ListOrder'])
        
        #Check for new order
        if not changed:
            changed = sorted(self.data.keys()) != sorted(self._original_data.keys())
            if changed:
                print 'maybe this'

        pm.button(self.inputs[pm.button]['ObjectSave'], edit=True, enable=changed)
    
    def _objects_refresh(self):
        print 'refresh objects'
        self.reload()
        self._redraw_selection()
        
    def _save_all(self):
        print 'save objects'
        #self.data[self._settings['GroupName']]['ObjectSelection'] = set(self._settings['GroupObjects'])
        self.save()
        self._redraw_groups()
    
    def _objects_hide(self):
        print 'hide objects'
        self._settings['HideSelected'] = pm.checkBox(self.inputs[pm.checkBox]['ObjectHide'], query=True, value=True)
        self._redraw_selection()
        
    def _redraw_selection(self):
        print 'redraw selection'
        pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, removeAll=True)
        object_list = set(self.scene_objects)
        
        try:
            selected_objects = [i for i in self.data[self._settings['GroupName']]['ObjectSelection'] if i in self.scene_objects]
        except KeyError:
            selected_objects = []
        else:
            self._selection_clean(self._settings['GroupName'])
            if self._settings['HideSelected']:
                for k, v in self._original_data.iteritems():
                    if k != self._settings['GroupName']:
                        object_list.difference_update(v['ObjectSelection'])
            object_list.update(selected_objects)
        object_list = sorted(object_list)
        pm.textScrollList(self.inputs[pm.textScrollList]['AllObjects'], edit=True, append=object_list, selectItem=selected_objects)
    
    def _redraw_groups(self):
        """Redraw list of groups."""
        print 'redraw groups'
        
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
            
            self._selection_clean(k)
            group_names.append(self._group_name_format(k))
        
        pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], edit=True, append=group_names)
        if self._settings['GroupName']:
            pm.textScrollList(self.inputs[pm.textScrollList]['Groups'], edit=True, selectItem=self._group_name_format(self._settings['GroupName']))
        self._objects_select(_redraw=False)
    
    def _group_name_format(self, k):
        try:
            num_items = len(self._original_data[k]['ObjectSelection'])
        except KeyError:
            num_items = 0
            difference = False
        try:
            difference = self._original_data[k]['ObjectSelection'] != self.data[k]['ObjectSelection']
        except KeyError:
            difference = True
        return '{a}{k} ({n})'.format(k=k, n=num_items if num_items else 'empty', a='*' if difference else '')
    
    def _selection_clean(self, group):
        """Remove any items not in the scene."""
        original_group = set(self.data[group]['ObjectSelection'])
        self.data[group]['ObjectSelection'] = set(i for i in self.data[group]['ObjectSelection'] if i in self.scene_objects)
        return len(self.data[group]['ObjectSelection']) == len(original_group)
    

'''
a = SetGroup('test')
a.frame[5].location = (5, 5)
print a.frame[5].scale
a.save()
'''
pm.fileInfo['AssemblyScript'] = StoreData().save({})
a = SetGroup('test')
a.selection=['pCube1', 'pCone1']
a.save()
for i in range(2):
    a = SetGroup('test'+str(i))
    a.save()
UserInterface().display()
