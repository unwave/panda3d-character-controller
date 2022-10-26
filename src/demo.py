#!/usr/bin/python
# -*- coding: utf-8 -*-

import typing

import logging
from direct.showbase.ShowBase import ShowBase

from panda3d import core, bullet

from panda3d.physics import ForceNode, LinearVectorForce
from direct.interval.IntervalGlobal import Sequence, Wait

loader: typing.Any
base: typing.Any
taskMgr: typing.Any
render: typing.Any
globalClock: typing.Any

import model

# trigger the lazy evaluation, as further the paths are read from config.json
model.fox.path

# The necessary import to run the Extended Character Controller
from characterController.PlayerController import PlayerController

# only necessary to check whether bullet or the internal physics engine
# should be used
from characterController.Config import USEBULLET, USEINTERNAL

__author__ = "Fireclaw the Fox"
__license__ = """
Simplified BSD (BSD 2-Clause) License.
See License.txt or http://opensource.org/licenses/BSD-2-Clause for more info
"""

# setup Logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
    filename="./demo.log",
    datefmt="%d-%m-%Y %H:%M:%S",
    filemode="w")


core.loadPrcFileData("","""
show-frame-rate-meter #t
model-path $MAIN_DIR/testmodel
cursor-hidden 1
on-screen-debug-enabled #f
# want-pstats true
want-tk #f
fullscreen #f
#win-size 1920 1080
win-size 1080 720
#win-size 840 720
# sync-video false
""")

class Main(ShowBase):
    def __init__(self):
        """initialise and start the Game"""
        ShowBase.__init__(self)

        self.accept("escape", exit)
        self.accept("gamepad-start", exit)
        self.accept("f1", self.toggleDebug)
        self.accept("r", self.resetPlayer)
        self.accept("p", self.togglePause)
        self.accept("f2", self.toggleCamera)
        self.accept("f3", self.toggleOSD)
        # automatically pause if the player is idling for to long
        self.accept("playerIdling", self.pause)
        self.accept("reset-Avatar", self.resetPlayer)
        self.disableMouse()

        base.win.movePointer(0, base.win.getXSize() // 2, base.win.getYSize() // 2)

        self.useBullet = USEBULLET
        self.useInternal = USEINTERNAL
        self.debugactive = True

        try:
            import simplepbr

            sky_color = core.Vec4F(135/255 * 1.2, 206/255, 235/255, 1) 
            self.setBackgroundColor(sky_color * 2)

            pipeline = simplepbr.init()
            pipeline.use_emission_maps = False
            pipeline.enable_shadows = True
            pipeline.use_normal_maps = True
            pipeline.use_occlusion_maps = True
            pipeline.exposure = 0.5

            sun = core.DirectionalLight("directionalLight")
            sun.setColor(core.Vec4F(1, 1, 1, 1) * 11)
            sun.get_lens().set_near_far(-50, 50)
            sun.get_lens().set_film_size(50, 50)
            sun.setScene(self.render)
            sun.set_shadow_caster(True, 4096, 4096)

            self.sun_light = self.render.attachNewNode(sun)
            self.render.setLight(self.sun_light)
            self.sun_light.set_hpr(45, -45, 0)

            sky_light = core.AmbientLight("Ambient")
            sky_light.setColor(sky_color * 0.4)

            self.sky_light = self.render.attachNewNode(sky_light)
            self.render.setLight(self.sky_light)

        except:
            print('No simplepbr')

            alight = core.AmbientLight("Ambient")
            alight.setColor(core.VBase4(0.5, 0.5, 0.5, 1))
            alnp = render.attachNewNode(alight)
            render.setLight(alnp)

            sun = core.DirectionalLight("Sun")
            sun.setColor(core.VBase4(1.5, 1.5, 1.0, 1))
            sunnp = render.attachNewNode(sun)
            sunnp.setHpr(10, -60, 0)
            render.setLight(sunnp)

            # Comment this line out if the demo runs slow on your system
            self.render.set_shader_auto()

        #
        # SIMPLE LEVEL SETUP
        #

        self.level: core.NodePath = loader.loadModel(model.level.path)
        self.level.reparentTo(render)

        #
        # LEVEL SETUP END
        #

        #
        # SIMPLE PHYSICS SETUP
        #
        #
        # BULLET
        #
        if self.useBullet:
            self.world = bullet.BulletWorld()
            self.world.setGravity(core.Vec3(0, 0, -9.81))

            shape = bullet.BulletPlaneShape(core.Vec3(0, 0, 1), 1)
            node = bullet.BulletRigidBodyNode("Ground")
            node.addShape(shape)
            node.setIntoCollideMask(core.BitMask32.allOn())
            np = render.attachNewNode(node)
            np.setPos(0, 0, -4)
            self.world.attachRigidBody(node)

            self.levelSolids = bullet.BulletHelper.fromCollisionSolids(self.level, True)
            for bodyNP in self.levelSolids:
                bodyNP.reparentTo(self.level)
                bodyNP.node().setDebugEnabled(False)
                if isinstance(bodyNP.node(), bullet.BulletRigidBodyNode):
                    bodyNP.node().setMass(0.0)
                    self.world.attachRigidBody(bodyNP.node())
                elif isinstance(bodyNP.node(), bullet.BulletGhostNode):
                    self.world.attachGhost(bodyNP.node())


            # Intangible blocks (as used for example for collectible or event spheres)
            self.moveThroughBoxes = render.attachNewNode(bullet.BulletGhostNode("Ghosts"))
            self.moveThroughBoxes.setPos(0, 0, 1)
            box = bullet.BulletBoxShape((1, 1, 1))
            self.moveThroughBoxes.node().addShape(box)
            # should only collide with the event sphere of the character
            self.moveThroughBoxes.node().setIntoCollideMask(core.BitMask32(0x80))  # 1000 0000
            self.world.attachGhost(self.moveThroughBoxes.node())



            # Intangible blocks (as used for example for collectible or event spheres)
            self.collideBox = render.attachNewNode(bullet.BulletRigidBodyNode("Ghosts"))
            self.collideBox.setPos(0, 2.5, 1)
            box = bullet.BulletBoxShape((1, 1, 1))
            self.collideBox.node().addShape(box)
            # should only collide with the event sphere of the character
            #self.collideBox.node().setIntoCollideMask(core.BitMask32(0x80))  # 1000 0000
            self.world.attachRigidBody(self.collideBox.node())


            self.accept("CharacterCollisions-in-Ghosts", print, ["ENTER"])
            self.accept("CharacterCollisions-out-Ghosts", print, ["EXIT"])


            # show the debug geometry for bullet collisions
            self.debugactive = True
            debugNode = bullet.BulletDebugNode("Debug")
            debugNode.showWireframe(True)
            debugNode.showConstraints(True)
            debugNode.showBoundingBoxes(False)
            debugNode.showNormals(True)
            self.debugNP = render.attachNewNode(debugNode)
            self.debugNP.show()

            self.world.setDebugNode(debugNode)
            self.__taskName = "task_physicsUpdater_Bullet"
            taskMgr.add(self.updatePhysicsBullet, self.__taskName, priority=-20)
        #
        # INTERNAL
        #
        if self.useInternal:
            # enable physics
            base.enableParticles()
            base.cTrav = core.CollisionTraverser("base collision traverser")
            base.cTrav.setRespectPrevTransform(True)

            # setup default gravity
            gravityFN = ForceNode("world-forces")
            gravityFNP = render.attachNewNode(gravityFN)
            gravityForce = LinearVectorForce(0, 0, -9.81)  # gravity acceleration
            gravityFN.addForce(gravityForce)
            base.physicsMgr.addLinearForce(gravityForce)

            # Ground Plane
            plane = core.CollisionPlane(core.Plane(core.Vec3(0, 0, 1), core.Point3(0, 0, -4)))
            self.ground = render.attachNewNode(core.CollisionNode("Ground"))
            self.ground.node().addSolid(plane)
            self.ground.show()

            # Add moving platforms
            self.platformIntervals = []
            self.platforms = []
            self.addFloatingPlatform(0, 8.0, self.level.find("**/PlatformPos.000").getPos(), self.level.find("**/PlatformPos.001").getPos())
            self.addFloatingPlatform(1, 8.0, self.level.find("**/PlatformPos.002").getPos(), self.level.find("**/PlatformPos.003").getPos())
            self.addFloatingPlatform(2, 8.0, self.level.find("**/PlatformPos.004").getPos(), self.level.find("**/PlatformPos.005").getPos())
            self.addFloatingPlatform(3, 8.0, self.level.find("**/PlatformPos.006").getPos(), self.level.find("**/PlatformPos.007").getPos())
            # add a rotating platform that doesn't has a node in the level file
            self.addFloatingPlatform(4, 10.0, (0, -15, 0), (0, -15, 0), 0, (360, 0, 0))

            # start the intervals
            for ival in self.platformIntervals:
                ival.loop()

            # Intangible blocks (as used for example for collectible or event spheres)
            self.moveThroughBoxes = render.attachNewNode(core.CollisionNode("Ghosts"))
            box = core.CollisionBox((0, 0, 0.5), 1, 1, 1)
            box.setTangible(False)
            self.moveThroughBoxes.node().addSolid(box)
            # should only collide with the event sphere of the character
            self.moveThroughBoxes.node().setFromCollideMask(core.BitMask32.allOff())
            self.moveThroughBoxes.node().setIntoCollideMask(core.BitMask32(0x80))  # 1000 0000
            self.moveThroughBoxes.show()

            self.accept("CharacterCollisions-in-Ghosts", print, ["ENTER"])
            self.accept("CharacterCollisions-out-Ghosts", print, ["EXIT"])

            # Set the world
            self.world = base.cTrav
        #
        # PHYSICS SETUP END
        #

        #
        # DEBUGGING
        #
        # NOTE: To add output to the OSD, see debugOSDUpdater below
        #       also make sure to set on-screen-debug-enabled to #t in
        #       the loadPrcFileData call given in the upper part of
        #       this file
        from direct.showbase.OnScreenDebug import OnScreenDebug
        self.osd = OnScreenDebug()
        self.osd.enabled = True
        self.osd.append("Debug OSD\n")
        self.osd.append("Keys:\n")
        self.osd.append("escape        - Quit\n")
        self.osd.append("gamepad start - Quit\n")
        self.osd.append("F1            - Toggle Debug Mode\n")
        self.osd.append("F2            - Toggle Camera Mode\n")
        self.osd.append("R             - Reset Player\n")
        self.osd.append("P             - Toggle Pause\n")
        self.osd.load()
        self.osd.render()
        taskMgr.add(self.debugOSDUpdater, "update OSD")

        #
        # THE CHARACTER
        #
        self.playerController = PlayerController(self.world, model.get_path("../data/config.json"))
        self.playerController.startPlayer()
        # find the start position for the character
        startpos = self.level.find("**/StartPos").getPos()
        if USEBULLET:
            # Due to the setup and limitation of bullets collision shape
            # placement, we need to shift the character up by half its
            # height.
            startpos.setZ(startpos.getZ() + self.playerController.getConfig("player_height")/2.0)
            startpos = (0,0,3)
        self.playerController.setStartPos(startpos)
        self.playerController.setStartHpr(self.level.find("**/StartPos").getHpr())

        self.pause = False

        self.playerController.camera_handler.centerCamera()

        self.render.subdivideCollisions(4)

        if hasattr(self, 'sun_light'):
            self.sun_light.reparent_to(self.playerController)
            self.sun_light.set_compass(self.render)

        # This function should be called whenever the player isn't
        # needed anymore like at an application quit method.
        #self.playerController.stopPlayer()

    def toggleDebug(self):
        """dis- and enable the collision debug visualization"""
        if not self.debugactive:
            if self.useBullet:
                # activate phyiscs debugging
                self.debugNP.show()
            if self.useInternal:
                self.moveThroughBoxes.show()
                self.playerController.charCollisions.show()
                self.playerController.shadowRay.show()
                self.playerController.charFutureCollisions.show()
                self.playerController.eventCollider.show()
                for rayID, ray in self.playerController.raylist.items():
                    ray.ray_np.show()
                base.cTrav.showCollisions(render)
            self.debugactive = True
        else:
            if self.useBullet:
                # deactivate phyiscs debugging
                self.debugNP.hide()
            if self.useInternal:
                self.moveThroughBoxes.hide()
                self.playerController.charCollisions.hide()
                self.playerController.shadowRay.hide()
                self.playerController.charFutureCollisions.hide()
                self.playerController.eventCollider.hide()
                for rayID, ray in self.playerController.raylist.items():
                    ray.ray_np.hide()
                base.cTrav.hideCollisions()
            self.debugactive = False

    def resetPlayer(self):
        """This function simply resets the player to the start position
        and centers the camera behind him."""
        self.playerController.setStartPos(self.level.find("**/StartPos").getPos())
        self.playerController.setStartHpr(self.level.find("**/StartPos").getHpr())
        self.playerController.camera_handler.centerCamera()

    def pause(self):
        print("PAUSE")
        if not self.pause:
            self.togglePause()

    def togglePause(self):
        """This function shows how the app can pause and resume the
        player"""
        if self.pause:
            # to respect window size changes we reset the necessary variables
            self.playerController.win_width_half = base.win.getXSize() // 2
            self.playerController.win_height_half = base.win.getYSize() // 2

            self.playerController.resumePlayer()
        else:
            self.playerController.pausePlayer()
        self.pause = not self.pause

    def toggleCamera(self):
        """This function shows how the app can toggle the camera system
        between first and third person mode"""
        if self.playerController.plugin_isFirstPersonMode():
            self.playerController.changeCameraSystem("thirdperson")
        else:
            self.playerController.changeCameraSystem("firstperson")

    def toggleOSD(self):
        self.osd.enabled = not self.osd.enabled
        if self.osd.onScreenText:
            if self.osd.enabled:
                self.osd.onScreenText.show()
            else:
                self.osd.onScreenText.hide()

    def debugOSDUpdater(self, task):
        """Update the OSD with constantly changing values"""
        # use self.osd.add("key", value) to add a data pair which will
        # be updated every frame
        #self.osd.add("Rotation", str(self.platforms[4].getH()))
        #self.osd.add("Speed", str(self.playerController.update_speed))


        #
        # GAMEPAD DEBUGGING
        #
        #gamepads = self.playerController.gamepad.gamepads


        #from panda3d.core import ButtonHandle
        #self.osd.add("0 - GAMEPAD:", gamepads[0].name)
        #self.osd.add("TEST STATE:", str(ButtonHandle("action_a")))
        #self.osd.add("HANDLE INDEX:", str(ButtonHandle("action_a").get_index()) + " " + str(gamepads[1].get_button_map(6).get_index()))
        #self.osd.add("STATE BY HANDLE:", str(gamepads[0].findButton(ButtonHandle("action_b")).state))
        #self.osd.add("MAP at 6:", str(gamepads[1].get_button_map(6)))
        #self.osd.add("MY MAP:", str(self.playerController.gamepad.deviceMap["sprint"]))
        #self.osd.add("BUTTON STATE 6:", str(gamepads[0].get_button(6).state))
        self.osd.add("stamina", "{:0.2f}".format(self.playerController.stamina))
        if USEINTERNAL:
            self.osd.add("velocity", "{X:0.4f}/{Y:0.4f}/{Z:0.4f}".format(
                X=self.playerController.actorNode.getPhysicsObject().getVelocity().getX(),
                Y=self.playerController.actorNode.getPhysicsObject().getVelocity().getY(),
                Z=self.playerController.actorNode.getPhysicsObject().getVelocity().getZ()))
        elif USEBULLET:
            self.osd.add("velocity", "{X:0.4f}/{Y:0.4f}/{Z:0.4f}".format(
                X=self.playerController.charCollisions.getLinearVelocity().getX(),
                Y=self.playerController.charCollisions.getLinearVelocity().getY(),
                Z=self.playerController.charCollisions.getLinearVelocity().getZ()))
        if taskMgr.hasTaskNamed(self.playerController.getConfig("idle_to_pause_task_name")):
            pause_task = taskMgr.getTasksNamed(self.playerController.getConfig("idle_to_pause_task_name"))[0]
            self.osd.add("pause in", "{:0.0f}".format(-pause_task.time))
        self.osd.add("state", "{}".format(self.playerController.state))
        self.osd.add("move vec", "{}".format(self.playerController.plugin_getMoveDirection()))

        self.osd.render()
        return task.cont

    def updatePhysicsBullet(self, task):
        """This task will handle the actualisation of
        the physic calculations each frame for the
        Bullet engine"""
        dt = globalClock.getDt()
        self.world.doPhysics(dt, 10, 1.0/180.0)
        return task.cont

    def addFloatingPlatform(self, platformID, time, platformStartPos, platformEndPos, platformStartHpr=0, platformEndHpr=0, model_path = model.floating_platform.path):
        # load and place the platform
        # "../data/level/FloatingPlatform"
        floatingPlatform = loader.loadModel(model_path)
        floatingPlatform.setName(floatingPlatform.getName()+str(platformID))
        floatingPlatform.setPos(platformStartPos)
        floatingPlatform.setH(platformStartHpr)
        # rename the collision object so we can determine on which platform the character landed
        fpSub = floatingPlatform.find("**/FloatingPlatform")
        fpSub.setName(fpSub.getName()+str(platformID))
        floatingPlatform.reparentTo(self.level)


        # create the platforms movement using an interval sequence
        platformIval = Sequence(
            floatingPlatform.posInterval(time, platformEndPos, name="Platform%dTo"%platformID),
            Wait(3.0),
            floatingPlatform.posInterval(time, platformStartPos, name="Platform%dFrom"%platformID),
            Wait(3.0),
            name="platform-move-interval-%d"%platformID)

        platformHprInterval = None
        if platformEndHpr != 0:
            platformHprInterval = Sequence(
                floatingPlatform.hprInterval(time, platformEndHpr, name="Platform%dRotate"%platformID),
                name="platform-hpr-interval-%d"%platformID)

        # store the platform and its interval
        self.platforms.append(floatingPlatform)
        self.platformIntervals.append(platformIval)
        if platformHprInterval is not None:
            self.platformIntervals.append(platformHprInterval)

if __name__ == '__main__':
    APP = Main()
    APP.run()
