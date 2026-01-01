import ctypes, pygame, numpy as np, math
from PIL import Image

NUM_LEDS=1000
SCREEN=800

# ---------- load C ----------
lib=ctypes.CDLL("./lib/led_engine.so")
lib.led_set_textures.argtypes=[ctypes.POINTER(ctypes.c_uint8),ctypes.c_int,ctypes.c_int,
                               ctypes.POINTER(ctypes.c_uint8),ctypes.c_int,ctypes.c_int]
lib.led_render_quat.argtypes=[ctypes.c_float]*6+[ctypes.POINTER(ctypes.c_uint8)]

# ---------- textures ----------
def load_tex(p,size):
    img=Image.open(p).convert("RGB").resize(size)
    a=np.array(img,dtype=np.uint8)
    print(f"{p}: {a.shape[1]}×{a.shape[0]} ({a.size/1024:.1f} KB)")
    return a,a.shape[1],a.shape[0]

day,dw,dh=load_tex("world_day.png",(128,64))
night,nw,nh=load_tex("world_night.png",(64,32))

lib.led_set_textures(
    day.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), dw, dh,
    night.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), nw, nh
)


rgb=np.zeros(NUM_LEDS*3,dtype=np.uint8)

# ---------- quaternion helpers ----------
def q_axis(a,ang):
    s=math.sin(ang/2)
    return np.array([math.cos(ang/2),a[0]*s,a[1]*s,a[2]*s],np.float32)

def qmul(a,b):
    return np.array([
        a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],
        a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],
        a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],
        a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]
    ],np.float32)

# ---------- simple draw points ----------
def fibo(n):
    pts=[]
    g=math.pi*(3-math.sqrt(5))
    for i in range(n):
        y=1-2*i/(n-1)
        r=math.sqrt(max(0,1-y*y))
        t=g*i
        pts.append((math.cos(t)*r,y,math.sin(t)*r))
    return pts
pts=fibo(NUM_LEDS)

pygame.init()
screen=pygame.display.set_mode((SCREEN,SCREEN))
pygame.event.set_grab(True)
pygame.mouse.set_visible(False)
clock=pygame.time.Clock()

q=np.array([1,0,0,0],np.float32)
earth=sun=0.0

while True:
    dt=clock.tick(60)/1000
    earth+=0.05*dt
    sun+=0.02*dt

    for e in pygame.event.get():
        if e.type==pygame.QUIT: quit()

    dx,dy=pygame.mouse.get_rel()
    q=qmul(q_axis([0,1,0],-dx*0.002),q)
    q=qmul(q_axis([1,0,0],-dy*0.002),q)

    lib.led_render_quat(
        ctypes.c_float(q[0]), ctypes.c_float(q[1]),
        ctypes.c_float(q[2]), ctypes.c_float(q[3]),
        ctypes.c_float(earth), ctypes.c_float(sun),
        rgb.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    )


    screen.fill((0,0,0))
    for i,(x,y,z) in enumerate(pts):
        px=int(x*300+SCREEN//2)
        py=int(-y*300+SCREEN//2)
        pygame.draw.circle(screen,rgb[i*3:i*3+3].tolist(),(px,py),8)
    pygame.display.flip()
