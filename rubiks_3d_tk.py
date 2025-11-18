import tkinter as tk
import math
import random
from functools import partial

COL = {
    'U': '#FFFFFF', 
    'D': '#FFD700', 
    'F': '#EF3B36', 
    'B': '#FF8C00', 
    'L': '#0033FF',
    'R': '#00AA00', 
    'X': '#222222' 
}

def mat_mul_vec(m, v):
    return (
        m[0][0]*v[0] + m[0][1]*v[1] + m[0][2]*v[2],
        m[1][0]*v[0] + m[1][1]*v[1] + m[1][2]*v[2],
        m[2][0]*v[0] + m[2][1]*v[1] + m[2][2]*v[2],
    )

def rot_x(t):
    c = math.cos(t); s = math.sin(t)
    return [[1,0,0],[0,c,-s],[0,s,c]]

def rot_y(t):
    c = math.cos(t); s = math.sin(t)
    return [[c,0,s],[0,1,0],[-s,0,c]]

def rot_z(t):
    c = math.cos(t); s = math.sin(t)
    return [[c,-s,0],[s,c,0],[0,0,1]]

def mul_mat(a, b):
    r = [[0]*3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                r[i][j] += a[i][k]*b[k][j]
    return r

def project(pt, view_rot, scale=240, camera_z=4, cx=450, cy=300):
    x,y,z = mat_mul_vec(view_rot, pt)
    zc = z + camera_z
    if zc == 0: zc = 0.0001
    factor = scale / zc
    sx = cx + x * factor
    sy = cy - y * factor
    return (sx, sy, zc)

class Cubie:
    def __init__(self, x,y,z, size=0.88):
        self.center = (x,y,z)
        self.size = size  
        self.ori = [[1,0,0],[0,1,0],[0,0,1]]
        self.colors = {'px':'X','nx':'X','py':'X','ny':'X','pz':'X','nz':'X'}
        if y==1:  self.colors['py']='U'
        if y==-1: self.colors['ny']='D'
        if z==1:  self.colors['pz']='F'
        if z==-1: self.colors['nz']='B'
        if x==-1: self.colors['nx']='L'
        if x==1:  self.colors['px']='R'

    def vertices(self):
        cx,cy,cz = self.center
        s = self.size/2
        offs = [
            (-s, -s, -s), 
            ( s, -s, -s),  
            ( s,  s, -s),
            (-s,  s, -s),
            (-s, -s,  s), 
            ( s, -s,  s), 
            ( s,  s,  s),
            (-s,  s,  s),
        ]
        v = []
        for ox,oy,oz in offs:
            rx,ry,rz = mat_mul_vec(self.ori, (ox,oy,oz))
            v.append((cx+rx, cy+ry, cz+rz))
        return v

    def quads(self):
        v = self.vertices()
        faces = {
            'F': (4, 5, 6, 7), 
            'B': (1, 0, 3, 2), 
            'U': (7, 6, 2, 3), 
            'D': (0, 1, 5, 4), 
            'L': (0, 4, 7, 3),
            'R': (5, 1, 2, 6),
        }
        return [(face, [v[i] for i in idx]) for face, idx in faces.items()]

class Rubiks3D:
    def __init__(self, canvas):
        self.canvas = canvas
        self.cubies = [Cubie(x,y,z) for x in (-1,0,1)
                                     for y in (-1,0,1)
                                     for z in (-1,0,1)]
        self.rx = math.radians(25)
        self.ry = math.radians(-30)
        self.rz = 0

        self.update_view_rot()
        self.animating = False
        self.anim_steps = 12

        self.draw()

    def update_view_rot(self):
        self.view_rot = mul_mat(rot_z(self.rz), mul_mat(rot_y(self.ry), rot_x(self.rx)))

    def draw(self):
        self.canvas.delete('all')
        drawlist = []

        for c in self.cubies:
            is_surface = any(col != 'X' for col in c.colors.values())
            if not is_surface:
                continue
            
            for face, quad in c.quads():
                v0, v1, v2 = quad[0], quad[1], quad[2]
                edge1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
                edge2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
                normal_world = (
                    edge1[1]*edge2[2] - edge1[2]*edge2[1],
                    edge1[2]*edge2[0] - edge1[0]*edge2[2],
                    edge1[0]*edge2[1] - edge1[1]*edge2[0]
                )
                normal_view = mat_mul_vec(self.view_rot, normal_world)
                if normal_view[2] >= 0:
                    continue

                ori_t = [[c.ori[j][i] for j in range(3)] for i in range(3)]
                normal_local = mat_mul_vec(ori_t, normal_world)

                ax = normal_local[0]
                ay = normal_local[1]
                az = normal_local[2]
                key = None
                m = max(abs(ax), abs(ay), abs(az))
                if m == abs(ax):
                    key = 'px' if ax > 0 else 'nx'
                elif m == abs(ay):
                    key = 'py' if ay > 0 else 'ny'
                else:
                    key = 'pz' if az > 0 else 'nz'

                sticker = c.colors.get(key, 'X')
                if sticker == 'X':
                    continue
                color = COL[sticker]

                proj_pts = [project(p, self.view_rot) for p in quad]
                screen_pts = [(p[0], p[1]) for p in proj_pts]
                center_depth = sum(p[2] for p in proj_pts) / 4

                drawlist.append((center_depth, screen_pts, color))

        drawlist.sort(key=lambda x: x[0], reverse=True)

        for depth, pts, color in drawlist:
            self.canvas.create_polygon(pts, fill=color, outline="#1a1a1a", width=3)


    def _layer(self, axis, val):
        idx = {'x':0,'y':1,'z':2}[axis]
        return [c for c in self.cubies if round(c.center[idx]) == val]

    def rotate_layer(self, axis, val, angle, clockwise=True):
        if self.animating:
            return

        self.animating = True
        layer = self._layer(axis, val)
        total = angle if clockwise else -angle
        step_angle = total / self.anim_steps
        step = 0

        idx = {'x':0, 'y':1, 'z':2}[axis]

        center_val = sum(c.center[idx] for c in layer)/len(layer)

        def animate():
            nonlocal step
            if axis=='x': R = rot_x(step_angle)
            elif axis=='y': R = rot_y(step_angle)
            else: R = rot_z(step_angle)

            for c in layer:
                cx, cy, cz = c.center
                coords = [cx, cy, cz]
                coords[idx] -= center_val
                rx, ry, rz = mat_mul_vec(R, coords)
                coords = [rx, ry, rz]
                coords[idx] += center_val
                c.center = (coords[0], coords[1], coords[2])
                c.ori = mul_mat(R, c.ori)

            self.draw()
            step += 1
            if step < self.anim_steps:
                self.canvas.after(20, animate)
            else:
                for c in layer:
                    x,y,z = c.center
                    c.center = (round(x), round(y), round(z))
                    new_ori = [[0]*3 for _ in range(3)]
                    for i in range(3):
                        for j in range(3):
                            v = c.ori[i][j]
                            if abs(v) < 0.5:
                                new_ori[i][j] = 0
                            else:
                                new_ori[i][j] = 1 if v > 0 else -1
                    c.ori = new_ori

                self.animating = False
                self.draw()

        animate()


    def _rotate_colors(self, axis, layer, clockwise):
        """Rotate the colors of cubies in a layer"""
        return

    def move(self, mv):
        base = mv[0]
        prime = mv.endswith("'")
        double = mv.endswith("2")
        count = 2 if double else (3 if prime else 1)

        for _ in range(count):
            if base=='U': self.rotate_layer('y', 1, -math.pi/2, True)
            elif base=='D': self.rotate_layer('y',-1, math.pi/2, True)
            elif base=='F': self.rotate_layer('z', 1, -math.pi/2, True)
            elif base=='B': self.rotate_layer('z',-1, math.pi/2, True)
            elif base=='L': self.rotate_layer('x',-1, math.pi/2, True)
            elif base=='R': self.rotate_layer('x', 1, -math.pi/2, True)

    def scramble(self, n=20):
        moves = ['U','U\'','U2','D','D\'','D2','F','F\'','F2','B','B\'','B2','L','L\'','L2','R','R\'','R2']
        for _ in range(n):
            self.move(random.choice(moves))

    def reset(self):
        self.__init__(self.canvas)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("3D Rubik's Cube")
        self.geometry("1100x700")

        self.canvas = tk.Canvas(self, width=900, height=700, bg="#404040")
        self.canvas.pack(side=tk.LEFT)

        self.cube = Rubiks3D(self.canvas)

        panel = tk.Frame(self)
        panel.pack(side=tk.RIGHT, fill=tk.Y)

        moves = ['U','U\'','U2','D','D\'','D2','F','F\'','F2','B','B\'','B2','L','L\'','L2','R','R\'','R2']
        self.last_move_var = tk.StringVar(value='')
        tk.Label(panel, textvariable=self.last_move_var).pack(pady=6)

        def make_cmd(mv):
            def cmd():
                print(f"Move requested: {mv}")
                self.last_move_var.set(mv)
                self.cube.move(mv)
            return cmd

        for m in moves:
            tk.Button(panel, text=m, width=8, command=make_cmd(m)).pack(pady=2)

        tk.Button(panel, text="Scramble", width=10, command=self.cube.scramble).pack(pady=10)
        tk.Button(panel, text="Reset", width=10, command=self.cube.reset).pack(pady=5)
        tk.Label(panel, text="Drag to rotate cube").pack(pady=10)

        self.lastpos=None
        self.canvas.bind("<ButtonPress-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_drag)

    def mouse_down(self, e):
        self.lastpos=(e.x,e.y)

    def mouse_drag(self, e):
        if not self.lastpos: return
        dx=e.x-self.lastpos[0]
        dy=e.y-self.lastpos[1]
        self.cube.ry += dx*0.01
        self.cube.rx += dy*0.01
        self.cube.update_view_rot()
        self.cube.draw()
        self.lastpos=(e.x,e.y)

if __name__=="__main__":
    App().mainloop()
