// =========================
// Parameters
// =========================
diameter       = 150;
thickness      = 2.5;
hole_diameter  = 8;
hole_count     = 300;

show_part = "both";   // ["top","bottom","both"]
split_gap = 0;

$fn = 64;

// =========================
// Afgeleide maten
// =========================
R = diameter / 2;
r_inner = R - thickness;
//hc = ceil(hole_count * 2.323); // TODO something with split_gap
hc = hole_count;

// =========================
// Holle bol
// =========================
module sphere_shell() {
    difference() {
        sphere(r = R);
        sphere(r = r_inner);
    }
}

// =========================
// Radiaal gat
// =========================
module radial_hole(theta, phi) {
    rotate([0, 0, phi])
    rotate([0, theta, 0])
    translate([0, 0, r_inner])
        cylinder(
            d = hole_diameter,
            h = thickness*2,
            center = true
        );
}

// =========================
// Fibonacci gaten (volledige bol)
// =========================
module holes_fibonacci() {
    golden = (1 + sqrt(5)) / 2;

    for (i = [0 : hc - 1]) {
        z = 1 - 2 * (i + 0.5) / hc;
        theta = acos(z);
        phi = 360 * i / golden;
        radial_hole(theta, phi);
    }
}

// =========================
// Split helpers
// =========================
module split_top() {
    intersection() {
        children();
        translate([0,0,R/2 + split_gap/2])
            cube([2*R,2*R,R], center=true);
    }
}

module split_bottom() {
    intersection() {
        children();
        translate([0,0,-R/2 - split_gap/2])
            cube([2*R,2*R,R], center=true);
    }
}

// =========================
// Eindmodel
// =========================
module full_sphere_with_holes() {
    difference() {
        sphere_shell();
        holes_fibonacci();
    }
}

if (show_part == "bottom")
    split_top() full_sphere_with_holes();
else if (show_part == "top")
    split_bottom() full_sphere_with_holes();
else
    full_sphere_with_holes();
