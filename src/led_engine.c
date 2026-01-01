// led_engine.c
#include <math.h>
#include <stdint.h>
#include "day_tex.h"
#include "night_tex.h"

#define NUM_LEDS 1000
#define PI 3.14159265358979323846f
#define AXIAL_TILT (23.44f * PI / 180.0f)

// ================= types =================
typedef struct { float x,y,z; } vec3;
typedef struct { float w,x,y,z; } quat;

// ================= state =================
static vec3 leds[NUM_LEDS];
static int inited = 0;

static uint8_t *tex_day, *tex_night;
static int day_w, day_h, night_w, night_h;

// ================= math =================
static quat quat_inv(quat q){ return (quat){q.w,-q.x,-q.y,-q.z}; }

static quat quat_mul(quat a, quat b){
    return (quat){
        a.w*b.w - a.x*b.x - a.y*b.y - a.z*b.z,
        a.w*b.x + a.x*b.w + a.y*b.z - a.z*b.y,
        a.w*b.y - a.x*b.z + a.y*b.w + a.z*b.x,
        a.w*b.z + a.x*b.y - a.y*b.x + a.z*b.w
    };
}

static vec3 quat_rotate(quat q, vec3 v){
    quat p={0,v.x,v.y,v.z};
    quat r=quat_mul(quat_mul(q,p),quat_inv(q));
    return (vec3){r.x,r.y,r.z};
}

static vec3 rot_x(vec3 p,float a){
    float c=cosf(a),s=sinf(a);
    return (vec3){p.x,c*p.y-s*p.z,s*p.y+c*p.z};
}

static vec3 rot_y(vec3 p,float a){
    float c=cosf(a),s=sinf(a);
    return (vec3){c*p.x+s*p.z,p.y,-s*p.x+c*p.z};
}

static float clamp(float v,float a,float b){
    return v<a?a:v>b?b:v;
}

// ================= init =================
static void init_leds(void){
    const float g = PI*(3.0f-sqrtf(5.0f));
    for(int i=0;i<NUM_LEDS;i++){
        float y=1-2.0f*i/(NUM_LEDS-1);
        float r=sqrtf(fmaxf(0,1-y*y));
        float t=g*i;
        leds[i]=(vec3){cosf(t)*r,y,sinf(t)*r};
    }
    inited=1;
}

// ================= UV =================
static void xyz_to_uv(vec3 p,float* u,float* v){
    float lon=atan2f(p.z,p.x);
    float lat=asinf(p.y);

    *u = 1.0f - ((lon + PI) / (2.0f * PI)); // mirror X
    *v = (PI/2.0f - lat) / PI;

    *u = clamp(*u,0,0.9999f);
    *v = clamp(*v,0,0.9999f);
}

// ================= area sample =================
static void sample_area(uint8_t* tex,int w,int h,
                        float u,float v,int r,float* out){
    int cx=(int)(u*(w-1));
    int cy=(int)(v*(h-1));
    float acc[3]={0,0,0};
    int n=0;

    for(int dy=-r;dy<=r;dy++)
    for(int dx=-r;dx<=r;dx++){
        if(dx*dx+dy*dy>r*r) continue;
        int x=clamp(cx+dx,0,w-1);
        int y=clamp(cy+dy,0,h-1);
        int i=(y*w+x)*3;
        acc[0]+=tex[i];
        acc[1]+=tex[i+1];
        acc[2]+=tex[i+2];
        n++;
    }
    out[0]=acc[0]/n;
    out[1]=acc[1]/n;
    out[2]=acc[2]/n;
}

// ================= public API =================
void led_set_textures(uint8_t* d,int dw,int dh,
                      uint8_t* n,int nw,int nh){
    tex_day=d; day_w=dw; day_h=dh;
    tex_night=n; night_w=nw; night_h=nh;
}

void led_render_quat(float qw,float qx,float qy,float qz,
                     float earth_rot,float sun_rot,
                     uint8_t* out){
    if(!inited) init_leds();

    quat q_cam={qw,qx,qy,qz};
    vec3 sun={
        cosf(sun_rot),
        sinf(sun_rot)*sinf(AXIAL_TILT),
        sinf(sun_rot)
    };

    for(int i=0;i<NUM_LEDS;i++){
        vec3 p=leds[i];

        // camera (IMU)
        p=quat_rotate(q_cam,p);

        // earth
        p=rot_x(p,AXIAL_TILT);
        p=rot_y(p,earth_rot);

        // lighting
        float l=p.x*sun.x+p.y*sun.y+p.z*sun.z;
        l=clamp((l-0.1f)/0.9f,0,1);

        float u,v,d[3],n[3];
        xyz_to_uv(p,&u,&v);
        sample_area(tex_day,day_w,day_h,u,v,1,d);
        sample_area(tex_night,night_w,night_h,u,v,1,n);

        out[i*3+0]=(uint8_t)(d[0]*l+n[0]*(1-l));
        out[i*3+1]=(uint8_t)(d[1]*l+n[1]*(1-l));
        out[i*3+2]=(uint8_t)(d[2]*l+n[2]*(1-l));
    }
}
