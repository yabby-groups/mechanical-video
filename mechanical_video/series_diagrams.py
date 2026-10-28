"""Supplementary animated 3-D teaching diagrams, explicitly separate from CAD."""
def add_diagrams(job,center,size,required,camera,materials,text):
    import bpy
    import math
    from mathutils import Vector
    number=job['episode']
    if number==12: return
    scene=bpy.context.scene; end=scene.frame_end
    root=bpy.data.objects.new('Supplementary schematic, not source CAD',None)
    scene.collection.objects.link(root); root.parent=camera
    root.location=(0,required*.22,-size*3)
    unit=required*.055
    def finish(obj,position,material):
        obj.parent=root; obj.location=Vector(position)*unit
        obj.data.materials.append(materials[material]); obj['schematic']=True
        return obj
    def box(position,scale,material='gantry'):
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj=finish(bpy.context.object,position,material); obj.scale=Vector(scale)*unit
        return obj
    def disk(position,radius,material='gantry'):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius*unit,depth=unit*.16)
        return finish(bpy.context.object,position,material)
    def arrow(position,direction=(0,-1,0),material='toolhead'):
        bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=unit*.11,radius2=0,depth=unit*.35)
        obj=finish(bpy.context.object,position,material)
        obj.rotation_euler=Vector(direction).to_track_quat('Z','Y').to_euler()
        return obj
    def translate(obj,start,end_position):
        for frame,position in [(1,start),(end,end_position)]:
            obj.location=Vector(position)*unit; obj.keyframe_insert(data_path='location',frame=frame)
    def rotate(obj,turns=3):
        obj.rotation_euler.z=0; obj.keyframe_insert(data_path='rotation_euler',frame=1)
        obj.rotation_euler.z=math.tau*turns; obj.keyframe_insert(data_path='rotation_euler',frame=end)
    titles={4:'电磁驱动原理示意',5:'皮带传力原理示意',6:'夹持与送料方向示意',7:'冷热分区与流动示意',
        8:'加热与表面基准示意',9:'指令与反馈关系示意',10:'风扇与气流功能示意',11:'分层沉积示意 · 层高夸张显示'}
    text(titles[number],0,required*.135,required*.016)
    if number==4:
        for i in range(8):
            angle=math.tau*i/8
            disk((math.cos(angle)*.95,math.sin(angle)*.95,0),.21)
        rotor=disk((0,0,.1),.48,'toolhead'); rotate(rotor,2)
        pointer=arrow((0,.5,.2),(1,0,0)); pointer.parent=rotor
        pointer.location=(0,unit*.5,unit*.2)
    elif number in (5,6):
        for x,turns in [(-.75,-3 if number==6 else 3),(.75,3)]:
            wheel=disk((x,0,0),.43,'toolhead'); rotate(wheel,turns)
            for i in range(8):
                angle=math.tau*i/8
                tooth=box((0,0,0),(.13,.13,.2),'frame'); tooth.parent=wheel
                tooth.location=(math.cos(angle)*unit*.43,math.sin(angle)*unit*.43,unit*.12)
        if number==5:
            for y in [-.43,.43]: box((0,y,0),(1.5,.035,.05),'motion')
            marker=arrow((-.5,.43,.2),(1,0,0)); translate(marker,(-.5,.43,.2),(.5,.43,.2))
        else:
            box((0,0,.3),(.035,2.1,.04),'bed')
            marker=arrow((0,.9,.4)); translate(marker,(0,.9,.4),(0,-.9,.4))
    elif number==7:
        box((0,.65,0),(.8,.55,.25),'gantry')
        box((0,-.1,0),(.8,.55,.25),'toolhead')
        bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=unit*.1,radius2=unit*.3,depth=unit*.45)
        finish(bpy.context.object,(0,-.6,0),'bed').rotation_euler.x=math.pi/2
        marker=arrow((0,1,.3)); translate(marker,(0,1,.3),(0,-1,.3))
    elif number==8:
        for y in [-.6,0,.6]: box((0,y,0),(2.1,.08,.08),'toolhead')
        box((0,0,-.1),(2.4,1.9,.12),'bed')
        for x in [-.7,0,.7]:
            marker=arrow((x,-.6,.3),(0,1,0)); translate(marker,(x,-.6,.3),(x,.6,.3))
    elif number==9:
        for x,material in [(-1.5,'gantry'),(0,'toolhead'),(1.5,'bed')]: box((x,0,0),(.8,.7,.15),material)
        for x in [-.75,.75]: box((x,0,0),(.7,.035,.06),'frame')
        marker=arrow((-1.2,0,.3),(1,0,0)); translate(marker,(-1.2,0,.3),(1.2,0,.3))
        feedback=arrow((1,-.65,.3),(-1,0,0),'gantry'); translate(feedback,(1,-.65,.3),(-1,-.65,.3))
        text('指令 → 控制 → 执行',0,required*.30,required*.016)
    elif number==10:
        rotor=disk((-.7,0,0),.12,'toolhead'); rotate(rotor,6)
        for i in range(5):
            angle=math.tau*i/5
            blade=box((0,0,0),(.5,.17,.06),'gantry'); blade.parent=rotor
            blade.location=(math.cos(angle)*unit*.4,math.sin(angle)*unit*.4,0); blade.rotation_euler.z=angle+.4
        for y in [-.5,0,.5]:
            marker=arrow((.2,y,.1),(1,0,0),'gantry'); translate(marker,(.2,y,.1),(1.3,y,.1))
    elif number==11:
        # A separate camera-facing schematic avoids asserting real layer height
        # or pretending a generated path came from a slicer or physical printer.
        head=arrow((-.9,-.65,.2),(0,1,0),'gantry')
        begin=round(job['timeline']['chapters'][16]['start']*30)+1
        finish_frame=round(job['timeline']['chapters'][34]['speech_end']*30)
        for layer in range(12):
            y=-.8+layer*.13
            bead=box((0,y,0),(1.8,.08,.1),'toolhead')
            start=begin+round((finish_frame-begin)*layer/12); stop=start+round((finish_frame-begin)*.65/12)
            bead.scale.x=0; bead.keyframe_insert(data_path='scale',frame=1)
            bead.keyframe_insert(data_path='scale',frame=start)
            bead.location.x=-unit*.9; bead.keyframe_insert(data_path='location',frame=1); bead.keyframe_insert(data_path='location',frame=start)
            bead.scale.x=unit*1.8; bead.keyframe_insert(data_path='scale',frame=stop)
            bead.location.x=0; bead.keyframe_insert(data_path='location',frame=stop)
            for frame,x in [(start,-.9),(stop,.9)]:
                head.location=Vector((x,y+.15,.2))*unit; head.keyframe_insert(data_path='location',frame=frame)
