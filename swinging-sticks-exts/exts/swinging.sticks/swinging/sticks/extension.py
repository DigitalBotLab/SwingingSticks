import omni
import omni.ext
import omni.ui as ui
from omni.debugdraw import get_debug_draw_interface

from pxr import UsdGeom, Gf, UsdPhysics, PhysxSchema, Vt

import carb




# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class SwingingSticksExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        print("[swinging.sticks] swinging sticks startup")

        self._window = ui.Window("swinging sticks ", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                with ui.HStack(height = 20):
                    ui.Button("Set Trigger", clicked_fn=self.set_trigger)

        self._update_sub = None

    def set_trigger(self):
        print("set trigger")

        self.stage = omni.usd.get_context().get_stage()
        defaultPrimPath = str(self.stage.GetDefaultPrim().GetPath())

        # set actor 
        actorPath = defaultPrimPath + "/swing/swing/stick0"
        self.actorPrim = self.stage.GetPrimAtPath(actorPath)
        self.actorRigidBodyAPI = UsdPhysics.RigidBodyAPI(self.actorPrim)


        # Force
        forcePrimPath = defaultPrimPath + "/swing/swing/stick0" + "/swingForce"
        forcePrim = self.stage.GetPrimAtPath(forcePrimPath)

        if forcePrim.IsValid(): # delete existing one
            omni.kit.commands.execute("DeletePrims", paths=[forcePrimPath])
            
        forceXform = UsdGeom.Xform.Define(self.stage, forcePrimPath)
        forceXform.AddTranslateOp().Set(Gf.Vec3f(0.0, 0.0, -1.0))
        self.forceApi = PhysxSchema.PhysxForceAPI.Apply(forceXform.GetPrim())    

        # Trigger
        triggerPath = defaultPrimPath + "/boxTrigger"
        triggerPrim = self.stage.GetPrimAtPath(triggerPath)

        if triggerPrim.IsValid(): # delete existing one
            omni.kit.commands.execute("DeletePrims", paths=[triggerPath])

        triggerBox = UsdGeom.Cube.Define(self.stage, triggerPath)
        triggerBox.CreateSizeAttr(100)
        triggerBox.AddTranslateOp().Set(Gf.Vec3f(0.0, 0.0, 0.0))
        triggerBox.AddScaleOp().Set(Gf.Vec3f(1.0, 1.0, 1.0))
        triggerBox.CreatePurposeAttr(UsdGeom.Tokens.guide)
        triggerUsdPrim = self.stage.GetPrimAtPath(triggerPath)
        UsdPhysics.CollisionAPI.Apply(triggerUsdPrim)
        PhysxSchema.PhysxTriggerAPI.Apply(triggerUsdPrim)
        self.triggerStateAPI = PhysxSchema.PhysxTriggerStateAPI.Apply(triggerUsdPrim)
        self.triggerCollisions = []
   
        # timeline
        stream = omni.timeline.get_timeline_interface().get_timeline_event_stream()
        self._timeline_sub = stream.create_subscription_to_pop(self._on_timeline_event)


    def _on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.PLAY):
            self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                self._on_update, name="omni.physx demo update"
            )
        elif event.type == int(omni.timeline.TimelineEventType.STOP):
            self._update_sub = None
            self._timeline_sub = None
        

    def _on_update(self, e):
        # print("updating......")
        dt = e.payload["dt"]
        
        # box_color = 0xffffff00
        # get_debug_draw_interface().draw_box(carb.Float3(0.0, 0.0, 0.0), carb.Float4(0.0, 0.0, 0.0, 1.0), carb.Float3(100.0, 100.0, 100.0), box_color, 3.0)
       
        
        triggerColliders = self.triggerStateAPI.GetTriggeredCollisionsRel().GetTargets()
        set_difference = set(triggerColliders).symmetric_difference(set(self.triggerCollisions))
        list_difference = list(set_difference)
        self.triggerCollisions = triggerColliders
        
        if len(triggerColliders) > 0:

            for collision in triggerColliders:
                # usdGeom = UsdGeom.Mesh.Get(self.stage, collision)
                # color = Vt.Vec3fArray([Gf.Vec3f(180.0 / 255.0, 16.0 / 255.0, 0.0)])
                # usdGeom.GetDisplayColorAttr().Set(color)  

                if "stick0" in collision.pathString:
                    angularVelocityAttribute = self.actorRigidBodyAPI.GetAngularVelocityAttr()   
                    # print("trigger len velocity", len(triggerColliders), angularVelocityAttribute.Get()) 

                    xSpeed = angularVelocityAttribute.Get()[0]
                    if abs(xSpeed) > 92:
                        self.forceApi.GetForceEnabledAttr().Set(False)
                    else:
                        self.forceApi.GetForceEnabledAttr().Set(True)
                        forceAttr = self.forceApi.GetForceAttr()
                        xForce = -1000 if xSpeed > 0 else 1000
                        forceAttr.Set(value=Gf.Vec3f(xForce, 0, 0))      
               
        # for collision in list_difference:
        #     usdGeom = UsdGeom.Mesh.Get(self.stage, collision)
        #     color = Vt.Vec3fArray([Gf.Vec3f(71.0 / 255.0, 165.0 / 255.0, 1.0)])
        #     usdGeom.GetDisplayColorAttr().Set(color)
      

    def on_shutdown(self):
        print("[swinging.sticks] swinging sticks shutdown")
