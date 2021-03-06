from __future__ import division
from collections import defaultdict
from operator import itemgetter
import pymel.core as pm
import random

def select_object(object_name):
    """Make sure an object is selected and isn't just text"""
    if isinstance(object_name, pm.nodetypes.Transform):
        return object_name
    try:
        return pm.ls(object_name)[0]
    except IndexError:
        raise IndexError("you need to select an object")

def find_distance(self, *args):
    return pow(sum(pow(i, 2) for i in args), 0.5)

def BOUNCE(RevealClass, start_frame, end_frame, start_location, start_rotation, start_scale, absolute_location=True, absolute_rotation=True, absolute_scale=True, distance_bounce=0, extra_keyframes=None, start_visibility=None):
    
    object_name = RevealClass.object_name
    
    if start_location is None:
        start_location = object_name.getTranslation()
    elif not absolute_location:
        start_location = tuple(i - j for i, j in zip(RevealClass.end_location, start_location))
    
    if start_rotation is None:
        start_rotation = object_name.getRotation()
    elif not absolute_rotation:
        start_rotation = tuple(i - j for i, j in zip(RevealClass.end_rotation, start_rotation))
    rotation_total = tuple(i - j for i, j in zip(RevealClass.end_rotation, start_rotation))
    
    if start_scale is None:
        start_scale = object_name.getScale()
    elif not absolute_scale:
        start_scale = tuple(i * j for i, j in zip(start_scale, RevealClass.end_scale))
    
    if start_visibility is None:
        start_visibility = pm.getAttr('{}.v'.format(object_name))
    
    distance_total = find_distance(*(i - j for i, j in zip(RevealClass.end_location, start_location)))
    if distance_bounce:
        distance_ratio = distance_total / (distance_total + distance_bounce)
        
        frame_total = end_frame - start_frame
        
        #Calculate the bounce ratio with a weighting of 2:1 (distance of 1 and bounce of 1 will result in 0.666:0.333)
        bounce_ratio = distance_ratio / (distance_ratio + 1) * 2
        frame_bounce = start_frame + frame_total * bounce_ratio
        
        #Calculate the bounce location
        bounce_ratio = (distance_bounce / distance_total)
        end_bounce = tuple(i + (i - j) * bounce_ratio for i, j in zip(RevealClass.end_location, start_location))
        
        RevealClass.set_position(frame_bounce, end_bounce, None, RevealClass.end_scale, None)
    
    #Set the keyframes
    RevealClass.set_position(start_frame, start_location, start_rotation, start_scale, start_visibility)
    RevealClass.set_position(end_frame, RevealClass.end_location, RevealClass.end_rotation, RevealClass.end_scale, RevealClass.end_visibility)
    
    #Set extra keyframes relative to the current position
    if extra_keyframes:
        for frame, new_position in extra_keyframes.iteritems():
            current_frame = start_frame + frame
            location, rotation, scale, absolute_location, absolute_rotation, absolute_scale = new_position
            
            new_location = None
            new_rotation = None
            new_scale = None
            
            if location is not None:
                if not absolute_location:
                    new_location = location
                elif absolute_location == 1:
                    location_at_frame = list(pm.getAttr(object_name + '.translate', time=current_frame))
                    new_location = tuple(i + j for i, j in zip(location_at_frame, location))
                elif absolute_location == 2:
                    new_location = tuple(i + j for i, j in zip(start_location, location))
                elif absolute_location == 3:
                    new_location = tuple(i + j for i, j in zip(RevealClass.end_location, location))
                else:
                    raise ValueError("incorrect location type")
            if rotation is not None:
                if not absolute_rotation:
                    new_rotation = rotation
                elif absolute_rotation == 1:
                    rotation_at_frame = list(pm.getAttr(object_name + '.rotate', time=current_frame))
                    new_rotation = tuple(i + j for i, j in zip(rotation_at_frame, rotation))
                elif absolute_rotation == 2:
                    new_rotation = tuple(i + j for i, j in zip(start_rotation, rotation))
                elif absolute_rotation == 3:
                    new_rotation = tuple(i + j for i, j in zip(RevealClass.end_rotation, rotation))
                else:
                    raise ValueError("incorrect rotation type")
            if scale is not None:
                if not absolute_scale:
                    new_scale = scale
                elif absolute_scale == 1:
                    scale_at_frame = list(pm.getAttr(object_name + '.scale', time=current_frame))
                    new_scale = tuple(i + j for i, j in zip(scale_at_frame, scale))
                elif absolute_scale == 2:
                    new_scale = tuple(i + j for i, j in zip(start_scale, scale))
                elif absolute_scale == 3:
                    new_scale = tuple(i + j for i, j in zip(RevealClass.end_scale, scale))
                else:
                    raise ValueError("incorrect scale type")
            
            RevealClass.set_position(current_frame, new_location, new_rotation, new_scale, None)
            

    #Adjust tangents at end of animation
    #DISABLED FOR NOW
    if distance_bounce and False:
        key_values = list(start_location) + list(rotation_total)
        key_names = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
        
        for i, value in enumerate(key_values):
            if value:
                attribute = '{}.{}'.format(object_name, key_names[i])
                if value > 0:
                    angle_amount = 90
                else:
                    angle_amount = -90
        
                pm.keyTangent(attribute, weightedTangents=True, edit=True)
                in_weight = pm.keyTangent(attribute, time=end_frame, inWeight=True, query=True)[0]
                out_weight = pm.keyTangent(attribute, time=end_frame, outWeight=True, query=True)[0]
                pm.keyTangent(attribute, edit=True, time=end_frame, inAngle=angle_amount, inWeight=in_weight, outAngle=angle_amount, outWeight=out_weight)
    
    

class RevealAnim(object):
    def __init__(self, object_name, movement_type, end_location=None, end_rotation=None, end_scale=None, end_visibility=None):
        """Store the information to be used later.
        
        Parameters:
            end_location: (int, int, int)
            end_rotation: (int, int, int)
            movement_type: (function, param1, param2, etc)
        """
        self.object_name = select_object(object_name)
        self.movement_type = movement_type
        
        #Set end location and rotation
        if end_location is not None:
            self.end_location = end_location
        else:
            self.end_location = self.object_name.getTranslation()
        if end_rotation is not None:
            self.end_rotation = end_rotation
        else:
            self.end_rotation = self.object_name.getRotation()
        if end_scale is not None:
            self.end_scale = end_scale
        else:
            self.end_scale = self.object_name.getScale()
        if end_visibility is not None:
            self.end_visibility = end_visibility
        else:
            self.end_visibility = pm.getAttr('{}.v'.format(self.object_name))
        
        
    def set_position(self,key_frame, location, rotation, scale, visibility):
        if location is not None:
            pm.setKeyframe(self.object_name, attribute='tx', value=location[0], time=key_frame)
            pm.setKeyframe(self.object_name, attribute='ty', value=location[1], time=key_frame)
            pm.setKeyframe(self.object_name, attribute='tz', value=location[2], time=key_frame)
        if rotation is not None:
            pm.setKeyframe(self.object_name, attribute='rx', value=rotation[0], time=key_frame)
            pm.setKeyframe(self.object_name, attribute='ry', value=rotation[1], time=key_frame)
            pm.setKeyframe(self.object_name, attribute='rz', value=rotation[2], time=key_frame)
        if scale is not None:
            pm.setKeyframe(self.object_name, attribute='sx', value=scale[0], time=key_frame)
            pm.setKeyframe(self.object_name, attribute='sy', value=scale[1], time=key_frame)
            pm.setKeyframe(self.object_name, attribute='sz', value=scale[2], time=key_frame)
        if visibility is not None:
            '''
            
keyTangent -itt auto -ott auto;
'''
            pm.setKeyframe(self.object_name, attribute='v', value=visibility, time=key_frame)
            pm.keyTangent('{}.v'.format(self.object_name), edit=True, itt='auto', ott='auto')
            pm.cutKey(self.object_name.getShape(), attribute='v', clear=True)
            pm.setAttr('{}.v'.format(self.object_name.getShape()), True)
            
            objectShape = None
            
    
    def set(self, start_frame, end_frame):
    
        start_location = self.object_name.getTranslation()
        start_rotation = self.object_name.getRotation()
        
        #Run the custom movement code
        movement_args = [self, start_frame, end_frame] + list(self.movement_type[1:])
        self.movement_type[0](*movement_args)


def create_animation(start, end, step, random_offset, object_list, movement, extra_frames):
    
    #If a list in input where each new item is a different step
    if isinstance(object_list, (list, tuple)):
        for i, object_names in enumerate(object_list):
            for object_name in object_names:
                reveal = RevealAnim(object_name, movement)
                offset = step * i + random.uniform(-random_offset, random_offset)
                reveal.set(start + offset, end + offset)
                
    #If a dictionary containing the distance from a point is input
    elif isinstance(object_list, dict):
        
        sorted_distances = sorted(object_list.keys())

        distance_difference = defaultdict(int)
        for i in range(len(sorted_distances) - 1):
            distance_difference[sorted_distances[i + 1] - sorted_distances[i]] += len(object_list[sorted_distances[i]])
        
        highest_value = max(distance_difference.values())
        highest_difference = {k:v for k, v in distance_difference.iteritems() if v == highest_value}
        lowest_key = min(highest_difference.keys())
        distance_multiplier = step / lowest_key
        
        for distance, object_names in object_list.iteritems():
            for object_name in object_names:
                reveal = RevealAnim(object_name, movement)
                offset = distance * distance_multiplier + random.uniform(-random_offset, random_offset)
                reveal.set(start + offset, end + offset)
                
                

def distance_between_points(p1, p2, ignore):
    p1 = [j for i, j in enumerate(p1) if i not in ignore]
    p2 = [j for i, j in enumerate(p2) if i not in ignore]
    point_len = len(p1)
    if point_len != len(p2):
        raise TypeError('the two points have different lengths')
    total = sum(pow(i - j, 2) for i, j in zip(p1, p2))
    return pow(total, 0.5) / point_len

def generate_distance(origin, object_list, ignore=None):
    result = defaultdict(list)
    for object in object_list:
        distance_from_start = distance_between_points(origin, pm.ls(object)[0].getTranslation(), ignore=ignore)
        result[distance_from_start].append(object)
    return result
