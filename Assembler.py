from __future__ import division
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

def BOUNCE(RevealClass, start_frame, end_frame, position, distance_bounce=0, extra_keyframes=None):
    
    object_name = RevealClass.object_name
    distance_main, start_rotation, start_scale = position
    
    if start_rotation is None:
        start_rotation = object_name.getRotation()
    if start_scale is None:
        start_scale = object_name.getScale()
    
    rotation_total = tuple(i - j for i, j in zip(RevealClass.end_rotation, start_rotation))
    
    distance_total = find_distance(*distance_main)
    distance_ratio = distance_total / (distance_total + distance_bounce)
    
    #Use the ratio to find the frame
    frame_total = end_frame - start_frame
    frame_bounce = start_frame + frame_total * distance_ratio
    
    #Calculate the start location
    start_location = list(RevealClass.end_location)
    start_location[0] += distance_main[0]
    start_location[1] += distance_main[1]
    start_location[2] += distance_main[2]
    
    #Calculate the bounce location
    end_bounce = list(RevealClass.end_location)
    end_bounce[0] -= distance_main[0] * (distance_bounce / distance_total)
    end_bounce[1] -= distance_main[1] * (distance_bounce / distance_total)
    end_bounce[2] -= distance_main[2] * (distance_bounce / distance_total)
    
    #Set the end location
    RevealClass.set_position(start_location, start_rotation, start_scale, start_frame)
    RevealClass.set_position(end_bounce, RevealClass.end_rotation, RevealClass.end_scale, frame_bounce)
    RevealClass.set_position(RevealClass.end_location, RevealClass.end_rotation, RevealClass.end_scale, end_frame)
    
    #Set extra keyframes relative to the current position
    if extra_keyframes is not None:
        for frame, new_position in extra_keyframes.iteritems():
            current_frame = start_frame + frame
            location, rotation, scale = new_position
            
            new_location = None
            new_rotation = None
            new_scale = None
            
            if any(location):
                location_at_frame = list(pm.getAttr(object_name + '.translate', time=current_frame))
                new_location = tuple(i + j for i, j in zip(location_at_frame, location))
            if any(rotation):
                rotation_at_frame = list(pm.getAttr(object_name + '.rotate', time=current_frame))
                new_rotation = tuple(i + j for i, j in zip(rotation_at_frame, location))
            if any(scale):
                scale_at_frame = list(pm.getAttr(object_name + '.scale', time=current_frame))
                new_scale = tuple(i + j for i, j in zip(scale_at_frame, location))
            
            RevealClass.set_position(new_location, new_rotation, new_scale, current_frame)
            

    #Adjust tangents at end of animation
    key_values = list(distance_main) + list(rotation_total)
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
    def __init__(self, object_name, movement_type, end_location=None, end_rotation=None, end_scale=None):
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
            self.end_scale = end_rotation
        else:
            self.end_scale = self.object_name.getScale()
        
        
    def set_position(self, location, rotation, scale, key_frame):
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
    
    def set(self, start_frame, end_frame):
    
        start_location = self.object_name.getTranslation()
        start_rotation = self.object_name.getRotation()
        
        #Run the custom movement code
        movement_args = [self, start_frame, end_frame] + list(self.movement_type[1:])
        self.movement_type[0](*movement_args)


start_frame = 0
end_frame = 10
frame_gap = 2

extra_frames = {5: [(0, 5, 0), 
                    (0, 0, 0), 
                    (0, 0, 0)]}
movement = (BOUNCE, [(6, 15, 2), (0, 90, 90), (2, 2, 2)], 1, extra_frames)

object_names = ['pCube' + str(i + 1) for i in range(12)]  #This just selects pCube1 to pCube12


for i, object_name in enumerate(object_names):
    reveal = RevealAnim(object_name, movement)
    offset = frame_gap * i
    reveal.set(start_frame + offset, end_frame + offset)
