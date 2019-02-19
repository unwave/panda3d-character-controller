#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# PYTHON IMPORTS
#
import math

#
# PANDA3D ENGINE IMPORTS
#
from panda3d.core import (
    CollisionTraverser,
    CollisionHandlerEvent,
    CollisionHandlerQueue,
    CollisionHandlerPusher,
    CollisionNode,
    CollisionSphere,
    CollisionSegment,
    CollisionRay,
    Point3,
    Vec3,
    NodePath,
    BitMask32,
    ModelRoot,
    )
from panda3d.physics import (
    PhysicsCollisionHandler,
    ActorNode)

__author__ = "Fireclaw the Fox"
__license__ = """
Simplified BSD (BSD 2-Clause) License.
See License.txt or http://opensource.org/licenses/BSD-2-Clause for more info
"""


#
# PHYSICS FUNCTIONS
#
class Physics:
    class Ray:
        def __init__(self, np, segment,  queue=None, last_entry=None):
            self.ray_np = np
            self.solid = segment
            self.last_entry = last_entry
            if queue is None:
                self.queue = CollisionHandlerQueue()
            else:
                self.queue = queue

    def __init__(self):

        if self.show_collisions:
            base.cTrav.showCollisions(render)
        self.rayCTrav = CollisionTraverser("collision traverser for ray tests")
        if self.show_collisions:
            self.rayCTrav.showCollisions(render)
        self.futureCTrav = CollisionTraverser("collision traverser for future position tests")
        if self.show_collisions:
            self.futureCTrav.showCollisions(render)
        self.physics_pusher = PhysicsCollisionHandler()

        self.collisionevent_handler = CollisionHandlerEvent()
        self.collisionevent_handler.addInPattern('%fn-in-%in')
        self.collisionevent_handler.addOutPattern('%fn-out-%in')
        self.collisionevent_handler.addInPattern('%fn-in')
        self.collisionevent_handler.addOutPattern('%fn-out')

        self.event_mask = BitMask32(0x80)  #1000 0000
        self.body_mask = BitMask32(0x70)  #0111 0000
        self.ray_mask = BitMask32(0x0f)  #0000 1111

        self.ignore_step = False
        self.anRemoved = False
        self.customP = False

        self.pre_set_platform = False

        self.landing_force = None

        self.actorNode = ActorNode("playerPhysicsController")
        self.mainNode = render.attachNewNode(self.actorNode)

        self.raylist = {}
        self.ray_ids = []
        self.ignore_ray_cycle = []
        point_a = Point3(0, 0, self.player_height/1.8)
        point_b = Point3(0, 0, -self.stepheight)
        self.foot_ray_id = "foot_ray_check"
        self.registerRayCheck(self.foot_ray_id, point_a, point_b, self.mainNode, True)


    def startPhysics(self):
        """Start and set up the remaining physics parts of the character
        Should be called at the character setup and base start method"""
        base.physicsMgr.attachPhysicalNode(self.actorNode)
        self.actorNode.getPhysicsObject().setMass(self.player_mass)
        self.reparentTo(self.mainNode)

        # main character cylinder/spheres
        self.charCollisions = self.mainNode.attachNewNode(CollisionNode("charBody"))
        self.charCollisions.node().addSolid(CollisionSphere(0, 0, self.player_height/4.0, self.player_height/4.0))
        self.charCollisions.node().addSolid(CollisionSphere(0, 0, self.player_height/4.0*3.05, self.player_height/4.0))
        self.charCollisions.node().setIntoCollideMask(self.body_mask)
        self.charCollisions.node().setFromCollideMask(self.body_mask)
        if self.show_collisions:
            self.charCollisions.show()
        self.physics_pusher.addCollider(self.charCollisions, self.mainNode)
        base.cTrav.addCollider(self.charCollisions, self.physics_pusher)

        self.eventCollider = self.mainNode.attachNewNode(CollisionNode(self.char_collision_name))
        self.eventCollider.node().addSolid(CollisionSphere(0, 0, self.player_height/2.0, self.player_height/2.0))
        self.eventCollider.node().setIntoCollideMask(self.event_mask)
        self.eventCollider.node().setFromCollideMask(self.event_mask)
        if self.show_collisions:
            self.eventCollider.show()
        base.cTrav.addCollider(self.eventCollider, self.collisionevent_handler)

        self.accept("{}-in".format(self.char_collision_name), self.checkCharCollisions)

        if self.use_simple_shadow:
            # shadow ray
            ray = CollisionRay(
                0, 0, 0.5,
                0, 0, -1)
            self.shadowRay = self.mainNode.attachNewNode(CollisionNode("CharShadowRay"))
            self.shadowRay.node().addSolid(ray)
            self.shadowRay.node().setIntoCollideMask(BitMask32.allOff())
            self.shadowRay.node().setFromCollideMask(self.ray_mask)
            self.shadowRayQueue = CollisionHandlerQueue()
            base.cTrav.addCollider(self.shadowRay, self.shadowRayQueue)

        self.charFutureCollisions = render.attachNewNode(CollisionNode("charFutureBody"))
        self.charFutureCollisions.node().addSolid(CollisionSphere(0, 0, self.player_height/2.0, self.player_height/4.0))
        #self.charFutureCollisions.node().addSolid(CollisionSphere(0, 0, self.player_height/4.0*3.05, self.player_height/4.0))
        self.charFutureCollisions.node().setIntoCollideMask(BitMask32.allOff())
        self.charFutureCollisions.node().setFromCollideMask(self.body_mask)
        if self.show_collisions:
            self.charFutureCollisions.show()
        self.charFutureCollisionsQueue = CollisionHandlerQueue()
        self.futureCTrav.addCollider(self.charFutureCollisions, self.charFutureCollisionsQueue)

    def registerRayCheck(self, ray_id, pos_a, pos_b, parent, ignore_ray_cycle=False):
        """This function will create a ray segment at the given position
        and attaches it to the given parent node. This has to be done
        for any ray check you want to do in the application."""
        # a new ray check ray
        raytest_segment = CollisionSegment(pos_a, pos_b)
        raytest_np = parent.attachNewNode(CollisionNode(ray_id))
        raytest_np.node().addSolid(raytest_segment)
        raytest_np.node().setIntoCollideMask(BitMask32.allOff())
        raytest_np.node().setFromCollideMask(self.ray_mask)
        if self.show_collisions:
            raytest_np.show()
        r = self.Ray(raytest_np, raytest_segment)
        self.rayCTrav.addCollider(r.ray_np, r.queue)
        # store the ray for later usage
        self.raylist[ray_id] = r
        if ignore_ray_cycle:
            self.ignore_ray_cycle.append(ray_id)
        if ray_id not in self.ignore_ray_cycle:
            self.ray_ids.append(ray_id)

    def stopPhysics(self):
        """Stops the characters physics elements. Should be called at
        character cleanup"""
        for ray_id, ray in self.raylist.items():
            ray.ray_np.removeNode()
        self.raylist = None
        self.ray_ids = None
        self.physics_pusher.clearColliders()
        self.rayCTrav.clearColliders()
        del self.rayCTrav

    def updatePhysics(self):
        """This method must be called every frame to update the ray
        traversal. So it should be called before any checks to
        ray segments will be made."""

        #cycle through all rays, only update one per frame
        self.ray_ids = self.ray_ids[1:] + self.ray_ids[:1]
        for ray_id, ray in self.raylist.items():
            if ray_id == self.ray_ids[0]:
                ray.ray_np.node().setFromCollideMask(self.ray_mask)
            elif ray_id not in self.ignore_ray_cycle:
                ray.ray_np.node().setFromCollideMask(BitMask32.allOff())

        self.rayCTrav.traverse(render)
        for ray_id, ray in self.raylist.items():
            if ray_id in self.ray_ids:
                if ray_id != self.ray_ids[0]: continue
            if ray.queue.getNumEntries() > 0:
                #try:
                #TODO: IF THIS ERROR EVER HAPPEN AGAIN, REPORT TO rdb
                ray.queue.sortEntries()
                entry = None
                entry = ray.queue.getEntry(0)
                self.raylist[ray_id].last_entry = entry
                #except:
                #    pass
            else:
                self.raylist[ray_id].last_entry = None

    def updateRayPositions(self, ray_id, point_a, point_b):
        """This method can be used to update the start and end position
        of the ray with the given ID"""
        self.raylist[ray_id].solid.setPointA(point_a)
        self.raylist[ray_id].solid.setPointB(point_b)

    def updatePlayerPos(self, speed, heading):
        """This function should be called to set the players new
        position and heading.
        speed determines the new position of the character.
        heading sets the new direction the player will face as seen from
        the camera and can be None.
        This function will process the stepping and dependend on that
        requests fall and landing states"""
        if heading is not None:
            curH = self.mainNode.getH()
            self.mainNode.setH(camera, heading)
            newH = self.mainNode.getH()
            self.mainNode.setH(curH)
            rotatetoH = self.mainNode.quatInterval(0.1, Point3(newH, 0, 0))
            rotatetoH.start()
            if not self.customP:
                self.mainNode.setP(0)
            self.mainNode.setR(0)
            self.customP = False
        self.mainNode.setFluidPos(self.mainNode, speed)
        if self.state not in self.ignore_step_states:
            if self.doStep():
                self.landing_force = self.actorNode.getPhysicsObject().getVelocity()
                if self.state not in self.on_ground_states:
                    self.actorNode.getPhysicsObject().setVelocity(0, 0, 0)
                    self.plugin_requestNewState(self.STATE_LAND)
            elif self.state != self.STATE_JUMP and self.state != self.STATE_FALL:
                self.plugin_requestNewState(self.STATE_FALL)

        self.updateCharSimpleShadow()

    def updatePlayerPosFloating(self, speed):
        """This method will update the position of the player respecting
        the global directions rather then the players local direction,
        which is useful for example if the player gets moved by a
        platform he stands on or wind or whatever external force may
        move the player around."""
        newPos = self.mainNode.getPos() + speed
        self.mainNode.setFluidPos(newPos)
        self.updateCharSimpleShadow()

    def updatePlayerPosFix(self, position, relativeTo=None):
        """This method will place the character at the given position."""
        if relativeTo is not None:
            self.mainNode.setPos(relativeTo, position)
        else:
            self.mainNode.setPos(position)
        self.updateCharSimpleShadow()

    def updatePlayerPosFloatingFlyign(self, speed):
        """This method will update the position of the player respecting
        the global directions rather then the players local direction,
        which is useful for example if the player gets moved by a
        platform he stands on or wind or whatever external force may
        move the player around.
        Note: this function will use the not physic related position
        update function and should only be used on flying modes if
        physics are disabled"""
        newPos = self.mainNode.getPos() + speed
        self.mainNode.setPos(newPos)
        self.updateCharSimpleShadow()

    def updatePlayerHpr(self, hpr):
        """Update the HPR value of the main player node"""
        if hpr[1] != 0:
            self.customP = True
        self.mainNode.setHpr(hpr)

    def __getHprFloatingNewPos(self, rotation, parent):
        """This function calculates the new position the character will
        get when he will be rotated around the given parent node"""
        center = parent.getPos(render)

        posvec = parent.getPos(render) - self.mainNode.getPos(render)
        posvec.setZ(0)
        circle_radius = posvec.length()

        # calculate the current angle of the player to the platform
        xdiff = self.mainNode.getX() - parent.getX()
        ydiff = self.mainNode.getY() - parent.getY()
        cur_angle_rad = math.atan2(ydiff, xdiff)
        # calculate the amount of radians that we will move the player
        rotation_rad = math.radians(rotation)
        # the new angle to which we will move the player to
        new_angle_rad = cur_angle_rad + rotation_rad

        # calculate the new position in the circle asuming the parent as
        # the center and using the previously calculated circle radius
        # and angle.
        x = parent.getX() + circle_radius * math.cos(new_angle_rad)
        y = parent.getY() + circle_radius * math.sin(new_angle_rad)

        # finally set the new position of the player
        new_pos = self.mainNode.getPos()
        new_pos.setX(x)
        new_pos.setY(y)

        return new_pos

    def updatePlayerHprFloating(self, rotation, parent):
        """This method will update the player position according to the
        rotation around the given parent node.
        NOTE: this will currently only work with rotations around the
        Z-Axis"""

        self.mainNode.setFluidPos(self.__getHprFloatingNewPos(rotation, parent))
        self.mainNode.setH(self.mainNode.getH() + rotation)

    def updatePlayerHprFloatingFlying(self, rotation, parent):
        """This method will update the player position according to the
        rotation around the given parent node.
        NOTE: this will currently only work with rotations around the
        Z-Axis"""

        self.mainNode.setPos(self.__getHprFloatingNewPos(rotation, parent))
        self.mainNode.setH(self.mainNode.getH() + rotation)

    def checkCharCollisions(self, collision):
        """This method will be called each time a collision occures with
        the characters main collision solids. It will check stepping as
        well as check if the character should fall or just landed
        somewhere."""
        if self.state in self.ignore_step_states:
            pass
        elif self.doStep():
            if self.state == self.STATE_JUMP or self.state == self.STATE_FALL:
                self.landing_force = self.actorNode.getPhysicsObject().getVelocity()
                self.actorNode.getPhysicsObject().setVelocity(0, 0, 0)
                self.plugin_requestNewState(self.STATE_LAND)
        elif self.state != self.STATE_JUMP and self.state != self.STATE_FALL:
            self.plugin_requestNewState(self.STATE_FALL)
        self.enterNewState()
        base.messenger.send("plugin-character-in-collision", [collision])

    def checkFloatingPlatform(self, entry):
        if entry is not None:
            if entry.getName().startswith(self.platform_collision_prefix):
                # we landed on a moving platform
                p = render.find("**/%s"%entry.getName())
                self.active_platform = self.__findPlatformRoot(p)
                self.pre_set_platform = True

    def cleanFloatingPlatform(self):
        if not self.pre_set_platform:
            self.active_platform = None

    def __findPlatformRoot(self, platform):
        """This method will find the root node of a floating platform
        which then may be used to update the characters position on that
        specific platform. This function will be called recursively."""
        if platform.hasParent():
            if platform.node().getType() == ModelRoot:
                return platform
            return self.__findPlatformRoot(platform.getParent())
        return platform

    def doStep(self):
        """This method will process the characters downward stepping to
        prevent it from floating. It will also check if the character
        landed on a movable platform and set it as active platform.
        This function will return True whenever the character has been
        stepped on the ground and Fals if there was no step"""
        if self.state not in self.ignore_step_states:
            # do the step height check
            char_step_collision = self.getFirstCollisionEntryInLine(self.foot_ray_id)

            # Check if we land on a movable platform
            groundNode = self.getFirstCollisionIntoNodeInLine(self.foot_ray_id)
            self.clearFirstCollisionEntryOfRay(self.foot_ray_id)
            self.cleanFloatingPlatform()
            self.pre_set_platform = False
            if groundNode is not None:
                if groundNode.getName().startswith(self.platform_collision_prefix):
                    # we landed on a moving platform
                    p = render.find("**/%s"%groundNode.getName())
                    self.active_platform = self.__findPlatformRoot(p)

            # prevent slipping
            if self.state in self.prevent_slip_states and char_step_collision is not None:
                # get the angle of the part of the ground we currently
                # stand on
                floor_normal = char_step_collision.getSurfaceNormal(render)
                zx = math.atan2(floor_normal.getZ(), floor_normal.getX())*180/math.pi
                zy = math.atan2(floor_normal.getZ(), floor_normal.getY())*180/math.pi
                zx = abs(zx-90)
                zy = abs(zy-90)
                # if the angle is within a specific range
                if zy <= self.slip_free_angle and zx <= self.slip_free_angle:
                    # prevent slipping
                    if zy > 0 or zx > 0:
                        self.toggleFlyMode(True)
                    return True
            self.toggleFlyMode(False)

            if char_step_collision is not None:
                if char_step_collision.hasSurfacePoint():
                    # place the character on the ground
                    pos = char_step_collision.getSurfacePoint(render)
                    self.mainNode.setFluidZ(pos.getZ())
                    return True
            return False
        elif self.anRemoved and self.state not in self.flying_states:
            self.toggleFlyMode(False)
        self.active_platform = None
        return False

    def toggleFlyMode(self, flyActive):
        """Dis- and Enable the physic effects on the character to give
        him the possibility to fly."""
        if flyActive:
            if not self.anRemoved:
                self.anRemoved = True
                self.actorNode.getPhysicsObject().setVelocity(0,0,0)
                base.physicsMgr.removePhysicalNode(self.actorNode)
        else:
            if self.anRemoved:
                self.anRemoved = False
                base.physicsMgr.attachPhysicalNode(self.actorNode)

    def hasSurfacePoint(self, entry):
        return entry.hasSurfacePoint()

    def getSurfacePoint(self, entry, np):
        return entry.getSurfacePoint(np)

    def hasSurfaceNormal(self, entry):
        return entry.hasSurfaceNormal()

    def getSurfaceNormal(self, entry, np):
        return entry.getSurfaceNormal(np)

    def getFallForce(self):
        return self.actorNode.getPhysicsObject().getVelocity().getZ()

    def getFirstCollisionEntryInLine(self, ray_id):
        """A simple raycast check which will return the collision entry
        of the first collision point as seen from the previously
        registred ray with the given ID"""
        return self.raylist[ray_id].last_entry

    def clearFirstCollisionEntryOfRay(self, ray_id):
        """sets the entry stored for that ray to None to make sure it
        won't store an entry for a couple of frames until the ray is
        querried again"""
        self.raylist[ray_id].last_entry = None

    def getFirstCollisionIntoNodeInLine(self, ray_id):
        """A simple raycast check which will return the into node of the
        first collision point as seen from the previously registred ray
        with the given ID"""
        entry = self.getFirstCollisionEntryInLine(ray_id)
        if entry is None: return None
        node = None
        node = entry.getIntoNode()
        return node

    def getFirstCollisionInLine(self, ray_id):
        """A simple raycast check which will return the first collision
        point as seen from the previously registred ray with the given
        ID"""
        entry = self.getFirstCollisionEntryInLine(ray_id)
        if entry is None: return None
        pos = None
        if entry.hasSurfacePoint():
            pos = entry.getSurfacePoint(render)
        return pos

    def checkFutureCharSpace(self, new_position):
        """Check if there is enough space at the new position to place
        the character on. If so, this function will return True
        otherwise it will return False"""
        if new_position is None: return False
        self.charFutureCollisions.setPos(new_position)
        self.futureCTrav.traverse(render)
        if self.charFutureCollisionsQueue.getNumEntries() > 0:
            return False
        else:
            return True

    def getBaseZOffset(self):
        """This function will return the offset which the physical body
        is off from the lower end of the character.
        There is no z-offset when using the internal physics engine.
        Hence this function will always return 0. Other engines like
        bullet will have a different setup and may return another value
        """
        return 0.0

    def updateCharSimpleShadow(self):
        """This function will update the simple shadow image below the
        character. It will synch it's position with the player as well
        as calculate it's size when the player is further away from the
        shadow/ground"""
        if not self.use_simple_shadow: return
        self.shadowRayQueue.sortEntries()
        pos = None
        if self.shadowRayQueue.getNumEntries() > 0:
            pos = self.shadowRayQueue.getEntry(0).getSurfacePoint(render)
            #normal = self.shadowRayQueue.getEntry(0).getSurfaceNormal(render)
        if pos is not None:
            self.shadow.setPos(pos.getX(), pos.getY(), pos.getZ() + self.shadow_z_offset)
            z_a = pos.getZ()
            z_b = self.mainNode.getZ()
            dist = z_b - z_a
            # check if we should scale the shadow below the character
            if dist <= 0:
                self.shadow.setScale(self.max_shadow_scale)
            else:
                # calculate the shadows scale from its current distance
                # to the player
                scale = self.shadow_min_scale_dist - dist / self.shadow_scale_factor
                if scale < self.min_shadow_scale:
                    scale = self.min_shadow_scale
                elif scale > self.max_shadow_scale:
                    scale = self.max_shadow_scale
                self.shadow.setScale(scale)

    def doJump(self, forwardSpeed, jump_direction=Vec3(0,0,0), extraSpeedVec=Vec3()):
        """This will let the actor node jump forward on the local y-axis
        with the upward speed given in jumpForce and forward given in speed.
        Note, if the actorNode shouldn't slide after landing call the
        physics.land function with the same actorNode"""
        # as we leave the ground set the active platform, if any, to None

        # OLD VERSION
        '''
        self.active_platform = None
        jumpVec = Vec3(0, -forwardSpeed/self.current_max_accleration*self.jump_forward_force_mult, 1)
        jumpVec *= self.jump_strength

        # rotate the extraSpeedVector to face the same direction the mainNode vector
        charVec = self.mainNode.getRelativeVector(render, extraSpeedVec)
        charVec.normalize()
        rotatedExtraSpeedVec = charVec * extraSpeedVec.length()

        jumpVec += rotatedExtraSpeedVec
        self.actorNode.getPhysicsObject().addLocalImpulse(jumpVec)
        '''


        # NEW VERSION
        self.active_platform = None

        dt = globalClock.getDt()
        jumpVec = Vec3(
            jump_direction.getX()*dt,
            -((forwardSpeed*self.jump_forward_force_mult)+jump_direction.getY())*dt,
            (self.phys_jump_strength+jump_direction.getZ())*dt)
        jumpVec *= self.jump_strength

        # rotate the extraSpeedVector to face the same direction the mainNode vector
        charVec = self.mainNode.getRelativeVector(render, extraSpeedVec)
        charVec.normalize()
        rotatedExtraSpeedVec = charVec * extraSpeedVec.length()

        jumpVec += rotatedExtraSpeedVec*dt

        self.actorNode.getPhysicsObject().addLocalImpulse(jumpVec)

        vel = self.actorNode.getPhysicsObject().getVelocity()
        velX = vel.getX()
        velY = vel.getY()
        velZ = vel.getZ()

        # Make sure we don't jump/move faster than we are alowed to
        #if abs(velX) > self.max_jump_force_internal_X \
        #or abs(velY) > self.max_jump_force_internal_Y:
        #    # we need to make sure X and Y are at the same distance
        #    # as before otherwise jump direction will be shifted
        #    if abs(velX) > abs(velY):
        #        pass
        #        #TODO: Calculate diff between x and y and subtract/add to respective other
        #    if velX < 0:
        #        velX = -self.max_jump_force_internal_X
        #    else:
        #        velX = self.max_jump_force_internal_X
        #if abs(velY) > self.max_jump_force_internal_Y:
        #    if velY < 0:
        #        velY = -self.max_jump_force_internal_Y
        #    else:
        #        velY = self.max_jump_force_internal_Y
        if abs(velZ) > self.max_jump_force_internal_Z:
            if velZ < 0:
                velZ = -self.max_jump_force_internal_Z
            else:
                velZ = self.max_jump_force_internal_Z

        self.actorNode.getPhysicsObject().setVelocity(velX, velY, velZ)

    def land(self):
        self.actorNode.getPhysicsObject().setVelocity(0,0,0)