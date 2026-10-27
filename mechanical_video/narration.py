"""Reusable deterministic explanation captions; all claims match the teaching model."""
TEXT={
'overview':['A planetary reducer: one sun, three planets and a fixed ring.','The carrier combines the three planetary paths into one output.','Educational inferred assembly. Nominal tooth-count ratio: 3.67 to 1.'],
'shell':['Remove the four fasteners and lift the front cover.','Separate the housing to reveal the carrier and gear train.','Hidden product details are inferred, not measurements from a photograph.'],
'internals':['The housing is hidden so each internal part can be inspected.','Sun, three planets, pins, carrier and shafts separate independently.','Each visible part has its own reusable STEP and STL file.'],
'explode':['Start with the assembled planetary reducer.','Separate housing, sun, planets, pins, carrier and shafts.','Seventeen independently modeled parts form this exploded assembly.'],
'gears':['The central sun gear drives three surrounding planet gears.','With the ring fixed, each planet spins and orbits with the carrier.','Ideal kinematic relation: carrier speed = sun speed / 3.67.'],
'closeup':['Inspect the sun gear and its central shaft bore.','The sampled involute flanks illustrate a 20-degree pressure angle.','Display clearances are enlarged; this is not a manufacturing drawing.'],
'alternative':['This educational mechanism is based on inferred construction.'],
'assembly':['Start from the fully separated assembly.','Bring each independently modeled part back to its assembled placement.','The same cached parts are reused for reverse assembly.'],
'working':['The input shaft and sun turn together.','The planets orbit while the carrier and output shaft rotate more slowly.','The animation illustrates ideal kinematics, not a dynamic load simulation.'],
'explanation':['First remove the housing and fasteners to expose the mechanism.','Identify the sun, three planets, their pins and the output carrier.','With a fixed ring, nominal reduction is 1 + 48 / 18 = 3.67.'],
 'transparent':['The housing becomes translucent to expose the internal arrangement.','The sun, planets and carrier remain independently modeled objects.','Transparent housing is a visualization, not a material specification.']}

def create(folder,template,seconds):
    def stamp(t):
        ms=round(t*1000); return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    rows=TEXT[template]; path=folder/'narration.srt'
    path.write_text('\n\n'.join(f'{i+1}\n{stamp(seconds*i/len(rows))} --> {stamp(seconds*(i+1)/len(rows))}\n{text}' for i,text in enumerate(rows))+'\n')
    return path

def attach(folder,template,seconds):
    import subprocess
    path=create(folder,template,seconds); video=folder/'video.mp4'; target=folder/'captioned.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(video),'-i',str(path),'-map','0:v:0','-map','1:0','-c:v','copy','-c:s','mov_text','-metadata:s:s:0','language=eng','-movflags','+faststart',str(target)],check=True)
    target.replace(video)
